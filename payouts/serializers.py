from rest_framework import serializers


class PayoutRequestSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField()
    bank_account_id = serializers.CharField(max_length=255)