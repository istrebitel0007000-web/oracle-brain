from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.core.serializer import Serializer
from rest_framework import serializers
from apps.chat.services.create_conversation import create_conversation


class CreateConversationRequestSerializer(Serializer):
    title = serializers.CharField(required=False, default="New Conversation", max_length=255)
    model = serializers.CharField(required=False, default="deepseek-r1-distill-llama-70b", max_length=100)
    persona = serializers.CharField(required=False, default="tech_oracle", max_length=100)
    temperature = serializers.FloatField(required=False, default=0.7)
    response_length = serializers.CharField(required=False, default="medium", max_length=20)
    is_incognito = serializers.BooleanField(required=False, default=False)


class CreateConversationResponseSerializer(Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    model = serializers.CharField()
    persona = serializers.CharField()
    temperature = serializers.FloatField()
    response_length = serializers.CharField()
    is_incognito = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class CreateConversationView(APIView):
    def post(self, request):
        serializer = CreateConversationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = create_conversation(
            user_id=request.user.id,
            **serializer.validated_data,
        )
        response_serializer = CreateConversationResponseSerializer(conversation)
        return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)
