from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import HttpResponse, Http404
from apps.core.serializer import Serializer
from apps.chat.models.conversation import Conversation
from apps.chat.services.export_conversation import export_conversation


class ExportConversationRequestSerializer(Serializer):
    format = serializers.ChoiceField(
        required=False,
        default="json",
        choices=["json", "markdown", "csv", "txt"],
    )


class ExportConversationView(APIView):
    def get(self, request, pk):
        serializer = ExportConversationRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        fmt = serializer.validated_data["format"]
        try:
            content, content_type = export_conversation(
                conversation_id=pk,
                user_id=request.user.id,
                fmt=fmt,
            )
        except Conversation.DoesNotExist:
            raise Http404
        ext_map = {"json": "json", "markdown": "md", "csv": "csv", "txt": "txt"}
        filename = f"conversation_{pk}.{ext_map.get(fmt, 'txt')}"
        return HttpResponse(
            content,
            content_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
