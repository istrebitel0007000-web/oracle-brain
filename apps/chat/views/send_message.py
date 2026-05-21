from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import Http404
from apps.core.serializer import Serializer
from apps.chat.services.send_message import send_message
from apps.chat.models.conversation import Conversation


class SendMessageRequestSerializer(Serializer):
    content = serializers.CharField(required=True)


class SendMessageResponseSerializer(Serializer):
    id = serializers.IntegerField()
    role = serializers.CharField()
    content = serializers.CharField()
    model_used = serializers.CharField()
    tokens_in = serializers.IntegerField()
    tokens_out = serializers.IntegerField()
    cost = serializers.FloatField()
    latency_ms = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class SendMessageView(APIView):
    def post(self, request, conversation_id):
        serializer = SendMessageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message = send_message(
                conversation_id=conversation_id,
                user_id=request.user.id,
                content=serializer.validated_data["content"],
            )
        except Conversation.DoesNotExist:
            raise Http404
        response_serializer = SendMessageResponseSerializer(message)
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)
