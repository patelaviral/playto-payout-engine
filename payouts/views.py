from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum, Case, When, F, IntegerField
from .models import IdempotencyKey, Merchant, Payout, LedgerEntry
from .serializers import PayoutRequestSerializer
import uuid


def get_balances(merchant):
    result = merchant.ledger_entries.aggregate(
        credits=Sum(
            Case(
                When(entry_type="credit", then=F("amount_paise")),
                default=0,
                output_field=IntegerField(),
            )
        ),
        debits=Sum(
            Case(
                When(entry_type="debit", then=F("amount_paise")),
                default=0,
                output_field=IntegerField(),
            )
        ),
        holds=Sum(
            Case(
                When(entry_type="hold", then=F("amount_paise")),
                default=0,
                output_field=IntegerField(),
            )
        ),
    )

    credits = result["credits"] or 0
    debits = result["debits"] or 0
    holds = result["holds"] or 0

    available = credits - debits - holds

    return {
        "available": available,
        "held": holds
    }


class PayoutRequestView(APIView):

    def post(self, request):
        serializer = PayoutRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        idempotency_key = request.headers.get("Idempotency-Key")

        if not idempotency_key:
            return Response({"error": "Idempotency-Key required"}, status=400)

        try:
            idempotency_key = uuid.UUID(idempotency_key)
        except ValueError:
            return Response({"error": "Invalid Idempotency-Key"}, status=400)

        merchant = Merchant.objects.first()
        if not merchant:
            return Response({"error": "Merchant not found"}, status=400)

        try:
            with transaction.atomic():

                idempotency_obj, created = IdempotencyKey.objects.select_for_update().get_or_create(
                    merchant=merchant,
                    key=idempotency_key
                )

                if not created:
                    if not idempotency_obj.is_processing:
                        return Response(idempotency_obj.response_data, status=200)
                    else:
                        return Response(
                            {"message": "Request is still processing"},
                            status=409
                        )

                amount = serializer.validated_data["amount_paise"]
                bank_account_id = serializer.validated_data["bank_account_id"]

                merchant = Merchant.objects.select_for_update().get(id=merchant.id)

                balances = get_balances(merchant)

                if balances["available"] < amount:
                    response_data = {"error": "Insufficient balance"}

                    idempotency_obj.response_data = response_data
                    idempotency_obj.is_processing = False
                    idempotency_obj.save()

                    return Response(response_data, status=400)

                payout = Payout.objects.create(
                    merchant=merchant,
                    amount_paise=amount,
                    bank_account_id=bank_account_id,
                    status="pending"
                )

                LedgerEntry.objects.create(
                    merchant=merchant,
                    amount_paise=amount,
                    entry_type="hold",
                    payout=payout
                )

                response_data = {
                    "message": "Payout created",
                    "payout_id": payout.id,
                    "amount": amount
                }

                idempotency_obj.response_data = response_data
                idempotency_obj.is_processing = False
                idempotency_obj.save()

                return Response(response_data, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)