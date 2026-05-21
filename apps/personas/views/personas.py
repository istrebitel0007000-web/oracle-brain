from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import Http404
from django.db import IntegrityError
from apps.core.serializer import Serializer
from apps.personas.models.persona import Persona


class PersonaSerializer(Serializer):
    id = serializers.IntegerField()
    key = serializers.CharField()
    name = serializers.CharField()
    instruction = serializers.CharField()
    temperature = serializers.FloatField()
    length = serializers.CharField()
    persona_type = serializers.CharField()
    created_at = serializers.DateTimeField()


class CreatePersonaRequestSerializer(Serializer):
    key = serializers.SlugField(required=True, max_length=100)
    name = serializers.CharField(required=True, max_length=255)
    instruction = serializers.CharField(required=True)
    temperature = serializers.FloatField(required=False, default=0.7)
    length = serializers.ChoiceField(
        required=False,
        default="medium",
        choices=["short", "medium", "detailed"],
    )


class UpdatePersonaRequestSerializer(Serializer):
    name = serializers.CharField(required=False, default=None, max_length=255)
    instruction = serializers.CharField(required=False, default=None)
    temperature = serializers.FloatField(required=False, default=None)
    length = serializers.ChoiceField(
        required=False,
        default=None,
        choices=["short", "medium", "detailed"],
        allow_null=True,
    )


class ListPersonasView(APIView):
    def get(self, request):
        personas = Persona.objects.all().order_by("name")
        serializer = PersonaSerializer(personas, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class CreatePersonaView(APIView):
    def post(self, request):
        serializer = CreatePersonaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            persona = Persona.objects.create(
                **serializer.validated_data,
                persona_type=Persona.PersonaType.CUSTOM,
            )
        except IntegrityError:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"key": ["A persona with that key already exists."]},
            )
        response_serializer = PersonaSerializer(persona)
        return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)


class UpdatePersonaView(APIView):
    def put(self, request, pk):
        serializer = UpdatePersonaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            persona = Persona.objects.get(id=pk, persona_type=Persona.PersonaType.CUSTOM)
        except Persona.DoesNotExist:
            raise Http404
        d = serializer.validated_data
        if d["name"] is not None:
            persona.name = d["name"]
        if d["instruction"] is not None:
            persona.instruction = d["instruction"]
        if d["temperature"] is not None:
            persona.temperature = d["temperature"]
        if d["length"] is not None:
            persona.length = d["length"]
        persona.save()
        response_serializer = PersonaSerializer(persona)
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)


class DeletePersonaView(APIView):
    def delete(self, request, pk):
        if not Persona.objects.filter(id=pk, persona_type=Persona.PersonaType.CUSTOM).exists():
            raise Http404
        Persona.objects.filter(id=pk, persona_type=Persona.PersonaType.CUSTOM).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
