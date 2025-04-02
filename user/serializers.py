from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.validators import UniqueValidator
from user.models import User
from django.db import transaction
from .models import UserProfile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError(
                {"detail": "Email and password are required."}
            )
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError({"detail": "Invalid credentials."})

        # Generate tokens
        token = self.get_token(user)

        return {
            "access": str(token.access_token),
            "refresh": str(token),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
        }


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(min_length=2, max_length=40, required=True)
    username = serializers.CharField(min_length=2, max_length=40, required=True)
    password = serializers.CharField(
        min_length=8, required=True, write_only=True, max_length=20
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "password",
        )
        extra_kwargs = {
            "email": {"required": True},
            "password": {"write_only": True, "required": True},
            "username": {"required": True},
        }
        custom_error_messages_for_validators = {
            "email": {
                UniqueValidator: "There is an existing account associated with this email address",
            },
            "username": {
                UniqueValidator: "This username is already taken",
            },
        }

    from django.db import transaction

    def create(self, validated_data):
        with transaction.atomic():
            username = validated_data.get("username")  # Extract username if present

            user = super(UserSerializer, self).create(validated_data)
            user.email = str(user.email).lower()
            user.set_password(validated_data["password"])
            user.username = username

            user.save()
            return user

    def to_representation(self, instance):
        data = super(UserSerializer, self).to_representation(instance)
        data.update(instance.tokens())
        data["success"] = True
        return data


class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = ["first_name", "last_name", "bio", "last_seen"]
