from rest_framework import serializers

from .models import ChatRoom, ChatMessage


class ChatRoomSerializer(serializers.ModelSerializer):
    user1_username = serializers.ReadOnlyField(source="user1.username")
    user2_username = serializers.ReadOnlyField(source="user2.username")

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "user1",
            "user1_username",
            "user2",
            "user2_username",
            "created_at",
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source="sender.username")
    receiver_username = serializers.ReadOnlyField(source="receiver.username")

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "room",
            "sender",
            "sender_username",
            "receiver",
            "receiver_username",
            "content",
            "timestamp",
            "is_read",
        ]
