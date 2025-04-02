from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from jwt import decode as jwt_decode
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

User = get_user_model()


@database_sync_to_async
def get_user(validated_token):
    try:
        user = get_user_model().objects.get(id=validated_token["user_id"])
        return user
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Close old database connections to prevent usage of timed out connections
        close_old_connections()

        # Get the token from headers instead of query parameters
        headers = dict(scope.get("headers", []))
        token = None

        # Check for Authorization header
        auth_header = headers.get(b"authorization")
        if auth_header:
            auth_header_str = auth_header.decode("utf-8")
            if auth_header_str.startswith("Bearer "):
                token = auth_header_str[7:]  # Remove 'Bearer ' prefix

        # If no token in headers and query string exists, try to extract from query string
        if not token and scope.get("query_string"):
            # Safely parse query string without assuming "token" exists
            try:
                from urllib.parse import parse_qs

                query_params = parse_qs(scope["query_string"].decode("utf-8"))
                token_list = query_params.get("token", [])
                if token_list:
                    token = token_list[0]
            except Exception:
                # If parsing fails for any reason, just continue without a token
                pass

        if not token:
            # No token found, proceed as anonymous user
            scope["user"] = AnonymousUser()
        else:
            # Try to authenticate the user
            try:
                # This will automatically validate the token and raise an error if token is invalid
                UntypedToken(token)
                # If token is valid, decode it
                decoded_data = jwt_decode(
                    token, settings.SECRET_KEY, algorithms=["HS256"]
                )
                # Get the user using ID
                scope["user"] = await get_user(validated_token=decoded_data)
            except (InvalidToken, TokenError) as e:
                # Token is invalid, proceed as anonymous user
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(AuthMiddlewareStack(inner))
