from rest_framework.test import APIClient
from payouts.models import Merchant, Payout, LedgerEntry
from django.test import TransactionTestCase
from threading import Thread
from django.db import connection


class IdempotencyTestCase(TransactionTestCase):

    def setUp(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create(name="Test Merchant")

        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=10000,
            entry_type="credit"
        )

    def test_idempotent_payout(self):
        url = "/api/v1/payouts/"
        headers = {
            "HTTP_IDEMPOTENCY_KEY": "123e4567-e89b-12d3-a456-426614174000"
        }

        data = {
            "amount_paise": 5000,
            "bank_account_id": "bank_123"
        }

        response1 = self.client.post(url, data, format="json", **headers)
        response2 = self.client.post(url, data, format="json", **headers)

        self.assertEqual(Payout.objects.count(), 1)

        self.assertEqual(response1.data, response2.data)

        payout = Payout.objects.first()
        self.assertEqual(payout.amount_paise, 5000)


class ConcurrencyTestCase(TransactionTestCase):

    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")

        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=10000,
            entry_type="credit"
        )

        self.url = "/api/v1/payouts/"

        self.data = {
            "amount_paise": 6000,
            "bank_account_id": "bank_123"
        }

    def make_request(self, headers, responses, index):
        client = APIClient()
        response = client.post(self.url, self.data, format="json", **headers)
        responses[index] = response

        connection.close()

    def test_concurrent_payouts(self):
        headers1 = {
            "HTTP_IDEMPOTENCY_KEY": "11111111-1111-1111-1111-111111111111"
        }
        headers2 = {
            "HTTP_IDEMPOTENCY_KEY": "22222222-2222-2222-2222-222222222222"
        }

        responses = [None, None]

        t1 = Thread(target=self.make_request, args=(headers1, responses, 0))
        t2 = Thread(target=self.make_request, args=(headers2, responses, 1))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        self.assertLessEqual(Payout.objects.count(), 1)

        success_responses = [
            r for r in responses if r and r.status_code == 200
        ]

        failure_responses = [
            r for r in responses if r and r.status_code != 200
        ]

        self.assertLessEqual(len(success_responses), 1)

        self.assertGreaterEqual(len(failure_responses), 1)