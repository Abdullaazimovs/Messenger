import os
import uuid

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.text import slugify
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .serializers import ChatRoomSerializer, ChatMessageSerializer
from .models import ChatRoom, ChatMessage, ChatMedia

from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


User = get_user_model()


class ChatRoomViewSet(viewsets.ViewSet):
    """ViewSet for managing chat rooms"""

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """List all chat rooms the authenticated user is part of."""
        chat_rooms = ChatRoom.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        )
        serializer = ChatRoomSerializer(chat_rooms, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Retrieve a specific chat room by ID."""
        chat_room = get_object_or_404(
            ChatRoom.objects.filter(
                Q(user1=request.user) | Q(user2=request.user), id=pk
            )
        )
        serializer = ChatRoomSerializer(chat_room)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def create_chat(self, request):
        """Create a new chat room between two users if it doesn't exist."""
        other_user_id = request.data.get("other_user_id")
        if not other_user_id:
            return Response({"error": "other_user_id is required"}, status=400)

        other_user = get_object_or_404(User, id=other_user_id)

        if request.user == other_user:
            return Response({"error": "Cannot create a chat with yourself"}, status=400)

        chat_room, created = ChatRoom.objects.get_or_create(
            user1=min(request.user, other_user, key=lambda u: u.id),
            user2=max(request.user, other_user, key=lambda u: u.id),
        )

        serializer = ChatRoomSerializer(chat_room)
        return Response({"chat_room": serializer.data, "newly_created": created})


class ChatMessageViewSet(viewsets.ViewSet):
    """ViewSet for handling chat messages"""

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, room_id=None):
        """List messages from a specific chat room."""
        chat_room = get_object_or_404(
            ChatRoom.objects.filter(
                Q(user1=request.user) | Q(user2=request.user), id=room_id
            )
        )
        messages = ChatMessage.objects.filter(room=chat_room).order_by("timestamp")
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    def create(self, request, room_id=None):
        """Send a new message in a chat room."""
        chat_room = get_object_or_404(
            ChatRoom.objects.filter(
                Q(user1=request.user) | Q(user2=request.user), id=room_id
            )
        )

        receiver = (
            chat_room.user2 if chat_room.user1 == request.user else chat_room.user1
        )

        message = ChatMessage.objects.create(
            room=chat_room,
            sender=request.user,
            receiver=receiver,
            content=request.data.get("content", ""),
        )

        serializer = ChatMessageSerializer(message)
        return Response(serializer.data)


class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            file_obj = request.FILES.get('file')
            room_id = request.data.get('room_id')
            receiver_id = request.data.get('receiver_id')

            if not file_obj:
                return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

            if not room_id:
                return Response({'error': 'Room ID required'}, status=status.HTTP_400_BAD_REQUEST)

            if not receiver_id:
                return Response({'error': 'Receiver ID required'}, status=status.HTTP_400_BAD_REQUEST)

            # Get file type based on mimetype
            main_type = file_obj.content_type.split('/')[0]
            if main_type not in ['image', 'video', 'audio']:
                main_type = 'document'

            # Get room
            try:
                room = ChatRoom.objects.get(id=room_id)
            except ChatRoom.DoesNotExist:
                return Response({'error': 'Chat room not found'}, status=status.HTTP_404_NOT_FOUND)

            # Verify user is part of the room
            if request.user.id != room.user1_id and request.user.id != room.user2_id:
                return Response({'error': 'Not authorized to access this room'}, status=status.HTTP_403_FORBIDDEN)

            # Get receiver user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                receiver = User.objects.get(id=receiver_id)
            except User.DoesNotExist:
                return Response({'error': 'Receiver not found'}, status=status.HTTP_404_NOT_FOUND)

            # Create message (empty content for now, will be updated via WebSocket)
            message = ChatMessage.objects.create(
                sender=request.user,
                receiver=receiver,
                room=room,
                content=""  # Empty content, can be updated later via WebSocket
            )

            # Create media entry
            media = ChatMedia.objects.create(
                message=message,
                file=file_obj,
                file_type=main_type,
                file_name=file_obj.name,
                file_size=file_obj.size
            )

            # Return file information
            return Response({
                'file_url': media.file.url,
                'file_type': media.file_type,
                'file_name': media.file_name,
                'file_size': media.file_size,
                'message_id': message.id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)