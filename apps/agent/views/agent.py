from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from apps.core.serializer import Serializer
from apps.agent.services.run_tool import run_tool, list_tools


class RunToolRequestSerializer(Serializer):
    tool_name = serializers.CharField(required=True, max_length=100)
    tool_input = serializers.DictField(required=False, default=dict)
    conversation_id = serializers.IntegerField(required=False, default=None)


class RunToolResponseSerializer(Serializer):
    tool_name = serializers.CharField()
    output = serializers.CharField()


class ToolInfoSerializer(Serializer):
    name = serializers.CharField()
    description = serializers.CharField()


class ListToolsView(APIView):
    def get(self, request):
        tools = list_tools()
        serializer = ToolInfoSerializer(tools, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class RunToolView(APIView):
    def post(self, request):
        serializer = RunToolRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        output = run_tool(
            tool_name=d["tool_name"],
            tool_input=d["tool_input"],
            user_id=request.user.id,
            conversation_id=d["conversation_id"],
        )
        response_serializer = RunToolResponseSerializer({
            "tool_name": d["tool_name"],
            "output": output,
        })
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)
