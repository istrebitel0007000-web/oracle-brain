from django.urls import path
from apps.chat.views.create_conversation import CreateConversationView
from apps.chat.views.list_conversations import ListConversationsView
from apps.chat.views.delete_conversation import DeleteConversationView
from apps.chat.views.send_message import SendMessageView
from apps.chat.views.rate_message import RateMessageView
from apps.chat.views.branch_conversation import BranchConversationView
from apps.chat.views.export_conversation import ExportConversationView

urlpatterns = [
    path("conversations/list/", ListConversationsView.as_view()),
    path("conversations/create/", CreateConversationView.as_view()),
    path("conversations/<int:pk>/delete/", DeleteConversationView.as_view()),
    path("conversations/<int:conversation_id>/messages/send/", SendMessageView.as_view()),
    path("messages/<int:pk>/rate/", RateMessageView.as_view()),
    path("conversations/<int:pk>/branch/", BranchConversationView.as_view()),
    path("conversations/<int:pk>/export/", ExportConversationView.as_view()),
]
