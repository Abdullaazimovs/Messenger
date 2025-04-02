from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import (
    CustomTokenObtainPairView,
    UserRegistrationView,
    UserProfileView,
    LogoutView,
)

router = DefaultRouter()

router.register(r"profile", UserProfileView, basename="user_profile")


urlpatterns = [
    # Authentication routes
    path("register/", UserRegistrationView.as_view(), name="user_registration"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # User profile route
    path("", include(router.urls)),
]
