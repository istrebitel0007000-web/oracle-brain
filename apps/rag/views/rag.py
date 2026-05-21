from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from apps.core.serializer import Serializer
from apps.rag.models.rag_chunk import RagChunk
from apps.rag.services.add_chunk import add_chunk, add_chunks_from_text
from apps.rag.services.search_chunks import search_chunks


class RagChunkSerializer(Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    source = serializers.CharField()
    created_at = serializers.DateTimeField()


class AddChunkRequestSerializer(Serializer):
    text = serializers.CharField(required=True)
    source = serializers.CharField(required=False, default="")
    auto_split = serializers.BooleanField(required=False, default=False)
    chunk_size = serializers.IntegerField(required=False, default=500)


class SearchChunksRequestSerializer(Serializer):
    query = serializers.CharField(required=True)
    top_k = serializers.IntegerField(required=False, default=5)


class ListRagChunksView(APIView):
    def get(self, request):
        chunks = RagChunk.objects.filter(user=request.user).order_by("-created_at")
        serializer = RagChunkSerializer(chunks, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class AddRagChunkView(APIView):
    def post(self, request):
        serializer = AddChunkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        if d["auto_split"]:
            chunks = add_chunks_from_text(
                user_id=request.user.id,
                text=d["text"],
                source=d["source"],
                chunk_size=d["chunk_size"],
            )
            return Response(
                status=status.HTTP_201_CREATED,
                data={"created": len(chunks)},
            )

        chunk = add_chunk(
            user_id=request.user.id,
            text=d["text"],
            source=d["source"],
        )
        response_serializer = RagChunkSerializer(chunk)
        return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)


class SearchRagChunksView(APIView):
    def get(self, request):
        serializer = SearchChunksRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        chunks = search_chunks(
            user_id=request.user.id,
            query=serializer.validated_data["query"],
            top_k=serializer.validated_data["top_k"],
        )
        response_serializer = RagChunkSerializer(chunks, many=True)
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)


class DeleteRagChunkView(APIView):
    def delete(self, request, pk):
        RagChunk.objects.filter(id=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
