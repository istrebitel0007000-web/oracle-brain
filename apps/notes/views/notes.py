from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import Http404
from apps.core.serializer import Serializer
from apps.notes.models.note import Note
from apps.notes.services.create_note import create_note, delete_note, pin_note, update_note


class NoteSerializer(Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    is_pinned = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CreateNoteRequestSerializer(Serializer):
    text = serializers.CharField(required=True)


class UpdateNoteRequestSerializer(Serializer):
    text = serializers.CharField(required=True)


class ListNotesView(APIView):
    def get(self, request):
        notes = Note.objects.filter(user=request.user).order_by("-is_pinned", "-created_at")
        serializer = NoteSerializer(notes, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class CreateNoteView(APIView):
    def post(self, request):
        serializer = CreateNoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = create_note(user_id=request.user.id, text=serializer.validated_data["text"])
        response_serializer = NoteSerializer(note)
        return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)


class UpdateNoteView(APIView):
    def put(self, request, pk):
        serializer = UpdateNoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = update_note(note_id=pk, user_id=request.user.id, text=serializer.validated_data["text"])
        response_serializer = NoteSerializer(note)
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)


class DeleteNoteView(APIView):
    def delete(self, request, pk):
        if not Note.objects.filter(id=pk, user=request.user).exists():
            raise Http404
        delete_note(note_id=pk, user_id=request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PinNoteView(APIView):
    def patch(self, request, pk):
        note = pin_note(note_id=pk, user_id=request.user.id)
        response_serializer = NoteSerializer(note)
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)
