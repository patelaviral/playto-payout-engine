from django.db import models
from django.core.validators import MinValueValidator


class Merchant(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Payout(models.Model):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    ]

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="payouts"
    )

    amount_paise = models.BigIntegerField(
        validators=[MinValueValidator(1)]
    )

    bank_account_id = models.CharField(max_length=255)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    retry_count = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_transition(self, new_status):
        allowed = {
            self.PENDING: [self.PROCESSING],
            self.PROCESSING: [self.COMPLETED, self.FAILED],
            self.COMPLETED: [],
            self.FAILED: [],
        }
        return new_status in allowed[self.status]

    def __str__(self):
        return f"{self.merchant.name} - {self.amount_paise} - {self.status}"


class LedgerEntry(models.Model):
    CREDIT = "credit"
    HOLD = "hold"      
    DEBIT = "debit"

    ENTRY_TYPE_CHOICES = [
        (CREDIT, "Credit"),
        (HOLD, "Hold"),
        (DEBIT, "Debit"),
    ]

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="ledger_entries"
    )

    amount_paise = models.BigIntegerField(
        validators=[MinValueValidator(1)]
    )

    entry_type = models.CharField(
        max_length=10,
        choices=ENTRY_TYPE_CHOICES
    )

    payout = models.ForeignKey(
        Payout,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ledger_entries"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.entry_type} - {self.amount_paise}"


class IdempotencyKey(models.Model):
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="idempotency_keys"
    )

    key = models.UUIDField(db_index=True)

    response_data = models.JSONField(null=True, blank=True)

    is_processing = models.BooleanField(default=True)  # 🔥 NEW

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("merchant", "key")

    def __str__(self):
        return f"{self.merchant.name} - {self.key}"