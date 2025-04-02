import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework_simplejwt.tokens import AccessToken, TokenError

from .models import ChatMessage, ChatRoom, ChatMedia

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Extract token from headers instead of query parameters
            headers = dict(self.scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")

            if not auth_header or not auth_header.startswith("Bearer "):
                logger.warning(
                    "WebSocket connection denied: No valid Authorization header"
                )
                await self.close(code=403)
                return

            token = auth_header.split("Bearer ")[1]

            # Validate token and get user
            try:
                access_token = AccessToken(token)
                access_token.verify()
                user_id = access_token["user_id"]
                self.user = await self.get_user(user_id)
            except TokenError as e:
                logger.error(f"Token validation failed: {e}")
                await self.close(code=403)
                return

            if not self.user or self.user.is_anonymous:
                logger.warning("WebSocket connection denied: Invalid user")
                await self.close(code=403)
                return

            # Get room_id from URL route
            self.room_id = self.scope["url_route"].get("kwargs", {}).get("room_id")
            if not self.room_id:
                logger.error("WebSocket connection denied: Missing room_id")
                await self.close(code=400)
                return

            # Check if the chat room exists and user is a participant
            self.chat_room = await self.get_chat_room()
            if not self.chat_room:
                logger.error(f"Chat room {self.room_id} not found or access denied")
                await self.close(code=404)
                return

            self.room_group_name = f"chat_{self.room_id}"

            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Mark previous messages as read and send history
            await self.mark_messages_as_read()
            await self.send_chat_history()

        except Exception as e:
            logger.critical(f"Unexpected error in connect: {e}", exc_info=True)
            await self.close(code=500)

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type", "text")

            # Handle regular text message
            if message_type == "text":
                message_content = text_data_json.get("message", "").strip()

                # Ignore empty messages
                if not message_content:
                    return

                receiver = await self.get_receiver()
                if not receiver:
                    return

                # Save text message
                chat_message = await self.save_message({
                    "content": message_content,
                    "sender": self.user,
                    "receiver": receiver,
                    "room": self.chat_room,
                })

                # Prepare WebSocket response
                message_data = {
                    "type": "chat_message",
                    "message_type": "text",
                    "message": chat_message.content,
                    "sender_id": self.user.id,
                    "sender_username": self.user.username,
                    "receiver_id": receiver.id,
                    "receiver_username": receiver.username,
                    "timestamp": chat_message.timestamp.isoformat(),
                    "message_id": chat_message.id,
                    "is_read": False,
                }

                # Send WebSocket message
                await self.channel_layer.group_send(self.room_group_name, message_data)

            # Handle media message (updating an existing message created during file upload)
            elif message_type == "media":
                message_id = text_data_json.get("message_id")
                message_content = text_data_json.get("message", "").strip()

                if not message_id:
                    return

                # Update the message content if provided
                if message_content:
                    success, message = await self.update_message_content(message_id, message_content)
                    if not success:
                        return
                else:
                    message = await self.get_message(message_id)
                    if not message:
                        return

                # Get media information
                media = await self.get_media_for_message(message_id)
                if not media:
                    return

                # Prepare media message data
                message_data = {
                    "type": "chat_message",
                    "message_type": "media",
                    "message": message.content,
                    "sender_id": message.sender.id,
                    "sender_username": message.sender.username,
                    "receiver_id": message.receiver.id,
                    "receiver_username": message.receiver.username,
                    "timestamp": message.timestamp.isoformat(),
                    "message_id": message.id,
                    "is_read": False,
                    "media": {
                        "file_url": media.file.url,
                        "file_type": media.file_type,
                        "file_name": media.file_name,
                        "file_size": media.file_size,
                    }
                }

                # Send WebSocket message
                await self.channel_layer.group_send(self.room_group_name, message_data)

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self.send(text_data=json.dumps({"error": "Invalid JSON format"}))
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self.send(text_data=json.dumps({"error": "Internal server error"}))

    async def chat_message(self, event):
        # Mark message as read if current user is the receiver
        if self.user.id == event.get("receiver_id") and not event.get("is_read"):
            success = await self.mark_message_as_read(event.get("message_id"))
            if success:
                event["is_read"] = True

        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found")
            return None

    @database_sync_to_async
    def get_chat_room(self):
        try:
            return ChatRoom.objects.filter(
                Q(user1=self.user) | Q(user2=self.user), id=self.room_id
            ).first()
        except Exception as e:
            logger.error(f"Error retrieving chat room: {e}")
            return None

    @database_sync_to_async
    def get_receiver(self):
        if self.chat_room.user1 == self.user:
            return self.chat_room.user2
        return self.chat_room.user1

    @database_sync_to_async
    def save_message(self, message_data):
        """Save a chat message."""
        chat_message = ChatMessage.objects.create(
            room=message_data["room"],
            sender=message_data["sender"],
            receiver=message_data["receiver"],
            content=message_data["content"],
        )
        return chat_message

    @database_sync_to_async
    def get_message(self, message_id):
        """Get a specific message."""
        try:
            return ChatMessage.objects.select_related('sender', 'receiver').get(id=message_id)
        except ChatMessage.DoesNotExist:
            logger.error(f"Message with id {message_id} not found")
            return None

    @database_sync_to_async
    def update_message_content(self, message_id, content):
        """Update message content."""
        try:
            message = ChatMessage.objects.select_related('sender', 'receiver').get(
                id=message_id,
                sender=self.user
            )
            message.content = content
            message.save(update_fields=['content'])
            return True, message
        except ChatMessage.DoesNotExist:
            logger.error(f"Message with id {message_id} not found or not owned by user")
            return False, None

    @database_sync_to_async
    def get_media_for_message(self, message_id):
        """Get media for a specific message."""
        try:
            return ChatMedia.objects.filter(message_id=message_id).first()
        except Exception as e:
            logger.error(f"Error retrieving chat media: {e}")
            return None

    @database_sync_to_async
    def get_chat_history(self):
        """Get chat history with related media."""
        messages = list(
            ChatMessage.objects.filter(room=self.chat_room)
            .select_related("sender", "receiver")
            .prefetch_related("media")
            .order_by("timestamp")
        )
        return messages

    async def send_chat_history(self):
        history = await self.get_chat_history()
        messages = []
        for msg in history:
            message_data = {
                "message_id": msg.id,
                "message": msg.content,
                "sender_id": msg.sender.id,
                "sender_username": msg.sender.username,
                "receiver_id": msg.receiver.id,
                "receiver_username": msg.receiver.username,
                "timestamp": msg.timestamp.isoformat(),
                "is_read": msg.is_read,
            }

            # Add media information if available
            media = list(msg.media.all())
            if media:
                message_data["message_type"] = "media"
                message_data["media"] = {
                    "file_url": media[0].file.url,
                    "file_type": media[0].file_type,
                    "file_name": media[0].file_name,
                    "file_size": media[0].file_size,
                }
            else:
                message_data["message_type"] = "text"

            messages.append(message_data)

        await self.send(
            text_data=json.dumps({"type": "chat_history", "messages": messages})
        )

    @database_sync_to_async
    def mark_messages_as_read(self):
        ChatMessage.objects.filter(
            room=self.chat_room, receiver=self.user, is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        try:
            message = ChatMessage.objects.get(id=message_id, receiver=self.user)
            message.is_read = True
            message.save()
            return True
        except ChatMessage.DoesNotExist:
            logger.warning(f"Message {message_id} not found for user {self.user}")
            return False
