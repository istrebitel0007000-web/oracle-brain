from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from apps.core.serializer import Serializer
from apps.chat.models.conversation import Conversation


class ConversationItemSerializer(Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    model = serializers.CharField()
    persona = serializers.CharField()
    branch_name = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ListConversationsView(APIView):
    def get(self, request):
        conversations = Conversation.objects.filter(
            user=request.user
        ).order_by("-updated_at")
        serializer = ConversationItemSerializer(conversations, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)
