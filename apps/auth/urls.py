from django.urls import path
from apps.auth.views.auth import RegisterView, LoginView, LogoutView, ChangePasswordView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),
]
