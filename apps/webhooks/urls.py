from django.urls import path
from apps.webhooks.views.webhooks import GenerateWebhookTokenView, WebhookReceiveView

urlpatterns = [
    path("token/create/", GenerateWebhookTokenView.as_view()),
    path("receive/", WebhookReceiveView.as_view()),
]
