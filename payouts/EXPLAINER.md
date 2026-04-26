# Playto Payout Engine – Explainer

## 1. The Ledger

I modeled the system using an append-only ledger instead of storing a mutable balance on the merchant.

Each transaction is recorded as a `LedgerEntry` with three types:

* `credit` → incoming funds
* `hold` → funds reserved for payout
* `debit` → funds successfully paid out

The available balance is computed using a database-level aggregation:

```
available = SUM(credits) - SUM(debits) - SUM(holds)
```

This is implemented using a single SQL aggregation with conditional expressions:

```
SUM(
  CASE 
    WHEN entry_type = 'credit' THEN amount_paise
    WHEN entry_type = 'debit' THEN -amount_paise
    WHEN entry_type = 'hold' THEN -amount_paise
  END
)
```

I chose this design because:

* It avoids race conditions caused by mutating a balance field
* It provides a complete audit trail of all money movements
* It guarantees correctness under concurrent writes

On payout failure, I do not mutate existing entries. Instead, I append a compensating `credit` entry, preserving immutability.

---

## 2. The Lock

To prevent concurrent payouts from overdrawing a balance, I use database-level row locking via `select_for_update()` inside a transaction.

Core code:

```
with transaction.atomic():
    merchant = Merchant.objects.select_for_update().get(id=merchant.id)
    balance = get_balances(merchant)

    if balance["available"] < amount:
        raise error
```

This relies on PostgreSQL’s **row-level locking**, which ensures:

* Only one transaction can read-modify-write the merchant’s balance at a time
* Other concurrent transactions are blocked until the lock is released

This prevents the classic race condition:

* Two requests both read balance = 100
* Both attempt to withdraw 60
* Without locking → both succeed (incorrect)

With locking → only one succeeds, the other sees updated state and fails.

---

## 3. Idempotency

Each request includes an `Idempotency-Key` (UUID) scoped per merchant.

I store this in an `IdempotencyKey` table with:

* unique constraint `(merchant, key)`
* `response_data` (cached response)
* `is_processing` flag

Flow:

1. Start a transaction and lock the idempotency row:

   ```
   select_for_update().get_or_create(...)
   ```
2. If key exists:

   * If `is_processing = False` → return stored response
   * If `is_processing = True` → return “request in progress”
3. If new key:

   * Process request
   * Store response
   * Mark `is_processing = False`

This handles the hardest case:

> If request A is still processing and request B arrives with the same key, B does not create a duplicate payout and does not return inconsistent data.

---

## 4. State Machine

Payouts follow a strict state machine:

* `pending → processing → completed`
* `pending → processing → failed`

Illegal transitions are explicitly blocked using:

```
def can_transition(self, new_status):
    allowed = {
        "pending": ["processing"],
        "processing": ["completed", "failed"],
        "completed": [],
        "failed": [],
    }
```

Before every state update, I validate:

```
if payout.can_transition(new_status):
    payout.status = new_status
```

This ensures:

* No backward transitions
* No invalid jumps (e.g., failed → completed)

State transitions that affect money (like failure refunds) are executed **atomically within the same transaction**.

---

## 5. The AI Audit

One critical issue I encountered was with concurrency handling.

An AI-generated approach suggested:

* Check balance
* Then create payout and ledger entry

However, it performed the balance check **outside a database lock**, which introduces a race condition.

Example of incorrect pattern:

```
balance = get_balance(merchant)
if balance >= amount:
    create_payout()
```

This is unsafe because two concurrent requests can read the same balance before either writes.

I fixed this by:

* Wrapping the entire flow in `transaction.atomic()`
* Using `select_for_update()` on the merchant row

Another issue was around idempotency:

* Initial implementation returned stored responses but did not handle in-flight requests
* This could result in duplicate processing under race conditions

I fixed this by introducing an `is_processing` flag and locking the idempotency row.

These changes ensured the system behaves correctly under concurrency and retry scenarios.
