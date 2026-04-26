# Playto Payout Engine

A minimal payout engine built as part of the Playto Founding Engineer Challenge.

This system simulates how international payments are collected and paid out to Indian merchants, focusing on correctness, concurrency, and money integrity.

---

## 🚀 Features

* **Ledger-based accounting system**

  * All balances derived from credits and debits
  * No direct balance mutation

* **Payout API**

  * Request payouts using idempotency keys
  * Prevents duplicate payouts on retries

* **Concurrency-safe transactions**

  * Prevents double spending using database-level locking

* **Background payout processor**

  * Simulates bank settlement
  * Success (70%), Failure (20%), Processing (10%)
  * Retry logic with backoff

* **State machine enforcement**

  * pending → processing → completed/failed
  * Invalid transitions are blocked

* **Automated tests**

  * Idempotency test
  * Concurrency test

---

## 🛠 Tech Stack

* Backend: Django + Django REST Framework
* Database: PostgreSQL
* Background jobs: Python worker (simulated)

---

## ⚙️ Setup Instructions

### 1. Clone repository

```bash
git clone https://github.com/patelaviral/playto-payout-engine.git
cd playto-payout-engine
```

---

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # Mac/Linux
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure environment variables

Create a `.env` file in the root directory:

```env
DB_NAME=playto_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

---

### 5. Run migrations

```bash
python manage.py migrate
```

---

### 6. Seed initial data

```bash
python manage.py seed_data
```

This creates:

* 2 merchants
* initial credit history

---

### 7. Run server

```bash
python manage.py runserver
```

---

## 📡 API Usage

### Create Payout

**POST** `/api/v1/payouts/`

Headers:

```
Idempotency-Key: <uuid>
```

Body:

```json
{
  "amount_paise": 5000,
  "bank_account_id": "bank_123"
}
```

---

## 🧪 Running Tests

```bash
python manage.py test
```

Includes:

* Idempotency validation
* Concurrency safety (no double spend)

---

## 🔁 Payout Processing

Run manually:

```bash
python manage.py shell
```

```python
from payouts.tasks import process_pending_payouts
process_pending_payouts()
```

---

## 🧠 Design Decisions

### Ledger Model

Balance is computed using:

```
SUM(
  CASE 
    WHEN entry_type = 'credit' THEN amount
    WHEN entry_type = 'debit' THEN -amount
    WHEN entry_type = 'hold' THEN -amount
  END
)
```

This ensures:

* auditability
* correctness under concurrency
* no floating-point errors

---

### Concurrency Handling

Uses:

```
select_for_update() + transaction.atomic()
```

Ensures:

* only one payout can deduct balance at a time

---

### Idempotency

* Stored per merchant
* Duplicate requests return same response
* Prevents duplicate payouts

---

### Retry Logic

* Retries stuck payouts (>30s)
* Exponential backoff
* Max 3 attempts → fail

---

## 📄 Explainer

Detailed explanation available in:

```
payouts/EXPLAINER.md
```

---

## 🎯 What I’m Most Proud Of

* Correct handling of concurrency and race conditions
* Ledger-based balance system (no mutation bugs)
* Realistic payout lifecycle simulation
* Writing tests that reflect real-world failures

---

## 📌 Notes

* Designed for correctness over feature completeness
* Focused on real-world payment system challenges

---

## 🚀 Deployment

(You can add your deployed URL here)

---

## 👤 Author

Aviral Patel
