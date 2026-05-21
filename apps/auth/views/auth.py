from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.serializer import Serializer
from apps.auth.services.register_user import (
    register_user, login_user, logout_user, change_password
)


class RegisterRequestSerializer(Serializer):
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(required=True, min_length=6, max_length=128)
    email = serializers.EmailField(required=False, default="")


class LoginRequestSerializer(Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class ChangePasswordRequestSerializer(Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)


class AuthResponseSerializer(Serializer):
    token = serializers.CharField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, token = register_user(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
                email=serializer.validated_data["email"],
            )
        except DjangoValidationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=e.message_dict)
        response_serializer = AuthResponseSerializer({
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
        })
        return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = login_user(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if not result:
            return Response(
                status=status.HTTP_401_UNAUTHORIZED,
                data={"detail": "Invalid credentials."},
            )
        user, token = result
        response_serializer = AuthResponseSerializer({
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
        })
        return Response(status=status.HTTP_200_OK, data=response_serializer.data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout_user(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        success = change_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
        )
        if not success:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"detail": "Old password is incorrect."},
            )
        return Response(status=status.HTTP_200_OK, data={"detail": "Password changed."})
