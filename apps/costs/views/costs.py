from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.db.models import Sum, Count
from apps.core.serializer import Serializer
from apps.costs.models.cost_record import CostRecord


class CostRecordSerializer(Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    model = serializers.CharField()
    persona = serializers.CharField()
    tokens_in = serializers.IntegerField()
    tokens_out = serializers.IntegerField()
    cost_usd = serializers.FloatField()
    created_at = serializers.DateTimeField()


class CostSummarySerializer(Serializer):
    total_cost_usd = serializers.FloatField()
    total_tokens_in = serializers.IntegerField()
    total_tokens_out = serializers.IntegerField()
    total_calls = serializers.IntegerField()


class ListCostsView(APIView):
    def get(self, request):
        query_params = request.query_params
        qs = CostRecord.objects.filter(user=request.user).order_by("-date", "-created_at")

        if query_params.get("date"):
            qs = qs.filter(date=query_params["date"])
        if query_params.get("model"):
            qs = qs.filter(model=query_params["model"])

        serializer = CostRecordSerializer(qs, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class CostSummaryView(APIView):
    def get(self, request):
        qs = CostRecord.objects.filter(user=request.user)

        if request.query_params.get("date"):
            qs = qs.filter(date=request.query_params["date"])

        summary = qs.aggregate(
            total_cost_usd=Sum("cost_usd"),
            total_tokens_in=Sum("tokens_in"),
            total_tokens_out=Sum("tokens_out"),
            total_calls=Count("id"),
        )

        summary["total_cost_usd"] = summary["total_cost_usd"] or 0.0
        summary["total_tokens_in"] = summary["total_tokens_in"] or 0
        summary["total_tokens_out"] = summary["total_tokens_out"] or 0
        summary["total_calls"] = summary["total_calls"] or 0

        serializer = CostSummarySerializer(summary)
        return Response(status=status.HTTP_200_OK, data=serializer.data)
