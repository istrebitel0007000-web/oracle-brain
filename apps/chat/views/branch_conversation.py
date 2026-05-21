from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import Http404
from apps.core.serializer import Serializer
from apps.chat.models.conversation import Conversation
from apps.chat.services.branch_conversation import branch_conversation


class BranchConversationRequestSerializer(Serializer):
    branch_name = serializers.CharField(required=True, max_length=100)
    from_message_id = serializers.IntegerField(required=True)


class BranchConversationResponseSerializer(Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    branch_name = serializers.CharField()
    parent_conversation = serializers.IntegerField(source="parent_conversation_id")
    created_at = serializers.DateTimeField()


class BranchConversationView(APIView):
    def post(self, request, pk):
        serializer = BranchConversationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            branch = branch_conversation(
                conversation_id=pk,
                user_id=request.user.id,
                branch_name=serializer.validated_data["branch_name"],
                from_message_id=serializer.validated_data["from_message_id"],
            )
        except Conversation.DoesNotExist:
            raise Http404
        response_serializer = BranchConversationResponseSerializer(branch)
        return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)
