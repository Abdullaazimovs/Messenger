from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatMessageViewSet, ChatRoomViewSet, FileUploadView

router = DefaultRouter()

router.register(r"messages", ChatMessageViewSet, basename="messages")
router.register(r"room", ChatRoomViewSet, basename="room")

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
    # Additional custom endpoints
    path(
        "messages/conversation/",
        ChatMessageViewSet.as_view({"get": "conversation"}),
        name="conversation",
    ),
    path(
        "messages/recent/",
        ChatMessageViewSet.as_view({"get": "recent_conversations"}),
        name="recent-conversations",
    ),
    path(
        "messages/mark-read/",
        ChatMessageViewSet.as_view({"post": "mark_read"}),
        name="mark-read",
    ),
    path('messages/upload/', FileUploadView.as_view(), name='file-upload'),
]
