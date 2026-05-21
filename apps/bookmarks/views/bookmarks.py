from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import Http404
from apps.core.serializer import Serializer
from apps.bookmarks.models.bookmark import Bookmark
from apps.bookmarks.services.create_bookmark import create_bookmark, delete_bookmark, update_bookmark


class BookmarkSerializer(Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    content = serializers.CharField()
    message = serializers.IntegerField(source="message_id", allow_null=True)
    created_at = serializers.DateTimeField()


class CreateBookmarkRequestSerializer(Serializer):
    label = serializers.CharField(required=True, max_length=255)
    content = serializers.CharField(required=True)
    message_id = serializers.IntegerField(required=False, default=None)


class UpdateBookmarkRequestSerializer(Serializer):
    label = serializers.CharField(required=True, max_length=255)


class ListBookmarksView(APIView):
    def get(self, request):
        bookmarks = Bookmark.objects.filter(user=request.user).order_by("-created_at")
        serializer = BookmarkSerializer(bookmarks, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class CreateBookmarkView(APIView):
    def post(self, request):
        serializer = CreateBookmarkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bookmark = create_bookmark(
            user_id=request.user.id,
            label=serializer.validated_data["label"],
            content=serializer.validated_data["content"],
            message_id=serializer.validated_data["message_id"],
        )
        response_serializer = BookmarkSerializer(bookmark)
        return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)


class UpdateBookmarkView(APIView):
    def put(self, request, pk):
        serializer = UpdateBookmarkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bookmark = update_bookmark(
            bookmark_id=pk,
            user_id=request.user.id,
            label=serializer.validated_data["label"],
        )
        response_serializer = BookmarkSerializer(bookmark)
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)


class DeleteBookmarkView(APIView):
    def delete(self, request, pk):
        if not Bookmark.objects.filter(id=pk, user=request.user).exists():
            raise Http404
        delete_bookmark(bookmark_id=pk, user_id=request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
