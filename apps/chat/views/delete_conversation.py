from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from apps.chat.models.conversation import Conversation
from apps.chat.services.delete_conversation import delete_conversation


class DeleteConversationView(APIView):
    def delete(self, request, pk):
        if not Conversation.objects.filter(id=pk, user=request.user).exists():
            raise Http404
        delete_conversation(conversation_id=pk, user_id=request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
