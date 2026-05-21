from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import Http404
from apps.core.serializer import Serializer
from apps.chat.models.conversation import Message
from apps.chat.services.rate_message import rate_message


class RateMessageRequestSerializer(Serializer):
    rating = serializers.IntegerField(required=True, min_value=1, max_value=5)


class RateMessageResponseSerializer(Serializer):
    id = serializers.IntegerField()
    rating = serializers.IntegerField()


class RateMessageView(APIView):
    def patch(self, request, pk):
        serializer = RateMessageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message = rate_message(
                message_id=pk,
                user_id=request.user.id,
                rating=serializer.validated_data["rating"],
            )
        except Message.DoesNotExist:
            raise Http404
        response_serializer = RateMessageResponseSerializer(message)
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)
