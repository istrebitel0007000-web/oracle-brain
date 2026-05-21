import secrets
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from apps.core.serializer import Serializer
from apps.core.services.groq_client import ask_groq
from apps.webhooks.models.webhook_call import WebhookCall, WebhookToken

log = logging.getLogger("oracle.webhooks")


def generate_webhook_token(user_id: int) -> str:
    """Generate a secure webhook token and persist it to the database."""
    token = secrets.token_urlsafe(32)
    WebhookToken.objects.create(user_id=user_id, token=token)
    return token


def _validate_token(token: str) -> bool:
    return WebhookToken.objects.filter(token=token, is_active=True).exists()


class GenerateWebhookTokenView(APIView):
    def post(self, request):
        token = generate_webhook_token(user_id=request.user.id)
        return Response(
            status=status.HTTP_201_CREATED,
            data={"token": token},
        )


class WebhookReceiveRequestSerializer(Serializer):
    prompt = serializers.CharField(required=True)
    token = serializers.CharField(required=True)


class WebhookReceiveView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = WebhookReceiveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        prompt = serializer.validated_data["prompt"]
        source_ip = _get_client_ip(request)

        if not _validate_token(token):
            WebhookCall.objects.create(
                token=token,
                prompt=prompt,
                response="",
                source_ip=source_ip,
                success=False,
            )
            return Response(
                status=status.HTTP_401_UNAUTHORIZED,
                data={"detail": "Invalid webhook token."},
            )

        result = ask_groq(messages=[{"role": "user", "content": prompt}])
        response_text = result["content"]

        WebhookCall.objects.create(
            token=token,
            prompt=prompt,
            response=response_text,
            source_ip=source_ip,
            success=True,
        )

        return Response(
            status=status.HTTP_200_OK,
            data={"response": response_text},
        )


def _get_client_ip(request) -> str:
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
