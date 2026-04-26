import random
from django.utils import timezone
from django.db import transaction
from payouts.models import Payout, LedgerEntry


MAX_RETRIES = 3

def process_pending_payouts():
    payouts = Payout.objects.filter(
        status__in=["pending", "processing"]
    )

    for payout in payouts:
        with transaction.atomic():

            payout = Payout.objects.select_for_update().get(id=payout.id)

            if payout.status == "processing":
                if payout.last_attempt_at:
                    elapsed = (timezone.now() - payout.last_attempt_at).total_seconds()

                    
                    if elapsed < 30:
                        continue

                if payout.retry_count >= MAX_RETRIES:
                    
                    if payout.can_transition("failed"):
                        payout.status = "failed"
                        payout.save()

                        
                        LedgerEntry.objects.create(
                            merchant=payout.merchant,
                            amount_paise=payout.amount_paise,
                            entry_type="credit",
                            payout=payout
                        )
                    continue

            
            if payout.status == "pending":
                if not payout.can_transition("processing"):
                    continue

                payout.status = "processing"
                payout.last_attempt_at = timezone.now()
                payout.retry_count += 1
                payout.save()

            rand = random.random()

            
            if rand < 0.7:
                if payout.can_transition("completed"):
                    payout.status = "completed"
                    payout.save()

                    LedgerEntry.objects.create(
                        merchant=payout.merchant,
                        amount_paise=payout.amount_paise,
                        entry_type="debit",
                        payout=payout
                    )

            
            elif rand < 0.9:
                if payout.can_transition("failed"):
                    payout.status = "failed"
                    payout.save()

                    LedgerEntry.objects.create(
                        merchant=payout.merchant,
                        amount_paise=payout.amount_paise,
                        entry_type="credit",
                        payout=payout
                    )

            
            else:
                payout.last_attempt_at = timezone.now()
                payout.retry_count += 1
                payout.save()