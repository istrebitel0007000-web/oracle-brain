from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.authtoken.models import Token


def register_user(username: str, password: str, email: str = "") -> tuple[User, Token]:
    """Create a new user and return (user, token)."""
    if User.objects.filter(username=username).exists():
        raise ValidationError({"username": ["A user with that username already exists."]})
    try:
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
        )
    except IntegrityError:
        raise ValidationError({"username": ["A user with that username already exists."]})
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def login_user(username: str, password: str) -> tuple[User, Token] | None:
    """
    Authenticate a user and return (user, token).
    Returns None if credentials are invalid.
    """
    user = authenticate(username=username, password=password)
    if not user:
        return None
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def logout_user(user: User) -> None:
    """Delete the user auth token, effectively logging them out."""
    Token.objects.filter(user=user).delete()


def change_password(user: User, old_password: str, new_password: str) -> bool:
    """
    Change a user password.
    Returns True on success, False if old_password is wrong.
    """
    if not user.check_password(old_password):
        return False
    user.set_password(new_password)
    user.save(update_fields=["password"])
    Token.objects.filter(user=user).delete()
    Token.objects.create(user=user)
    return True
