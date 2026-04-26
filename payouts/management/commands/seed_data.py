from django.core.management.base import BaseCommand
from payouts.models import Merchant, LedgerEntry


class Command(BaseCommand):
    help = "Seed initial merchants and ledger data"

    def handle(self, *args, **kwargs):
        if Merchant.objects.exists():
            self.stdout.write("Data already exists, skipping...")
            return

        self.stdout.write("Seeding data...")

        merchant1 = Merchant.objects.create(name="Alpha Agency")
        merchant2 = Merchant.objects.create(name="Beta Freelancers")

        LedgerEntry.objects.create(
            merchant=merchant1,
            amount_paise=20000,
            entry_type="credit"
        )

        LedgerEntry.objects.create(
            merchant=merchant1,
            amount_paise=10000,
            entry_type="credit"
        )

        LedgerEntry.objects.create(
            merchant=merchant2,
            amount_paise=15000,
            entry_type="credit"
        )

        self.stdout.write(self.style.SUCCESS("Seed data created successfully"))