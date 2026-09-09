import base64
import hmac
from typing import Any

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.audit import log_action

from .lockout import lockout_store
from .models import VaultUserProfile
from .serializers import LoginSerializer, PreauthSerializer, RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.create(username=data["username"])
        user.set_unusable_password()
        user.save()
        VaultUserProfile.objects.create(
            user=user,
            kdf_salt=base64.b64decode(data["kdf_salt"]),
            verifier_salt=base64.b64decode(data["verifier_salt"]),
            verifier=base64.b64decode(data["verifier"]),
            kdf_params=data["kdf_params"],
        )
        log_action(user, "register", request=request)
        return Response({"username": user.username}, status=status.HTTP_201_CREATED)


class PreauthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        serializer = PreauthSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            profile = VaultUserProfile.objects.get(
                user__username=serializer.validated_data["username"]
            )
        except VaultUserProfile.DoesNotExist:
            return Response(
                {"error": {"code": "user_not_found", "message": "unknown user"}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "kdf_salt": base64.b64encode(profile.kdf_salt).decode("ascii"),
                "verifier_salt": base64.b64encode(profile.verifier_salt).decode("ascii"),
                "kdf_params": profile.kdf_params,
            }
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request: Request) -> Response:
        body: dict[str, Any] = request.data  # type: ignore[assignment]
        username = body.get("username", "")
        ip = request.META.get("REMOTE_ADDR", "")
        if lockout_store.is_locked(username, ip):
            return Response(
                {"error": {"code": "account_locked", "message": "too many failed attempts"}},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            profile = VaultUserProfile.objects.select_related("user").get(
                user__username=str(data["username"])
            )
        except VaultUserProfile.DoesNotExist:
            lockout_store.record_failure(username, ip)
            return Response(
                {
                    "error": {
                        "code": "invalid_credentials",
                        "message": "invalid username or verifier",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        verifier = base64.b64decode(data["verifier"])
        if not hmac.compare_digest(bytes(profile.verifier), verifier):
            lockout_store.record_failure(username, ip)
            return Response(
                {
                    "error": {
                        "code": "invalid_credentials",
                        "message": "invalid username or verifier",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        lockout_store.reset(username, ip)
        token, _ = Token.objects.get_or_create(user=profile.user)
        log_action(profile.user, "login", request=request)
        return Response({"token": token.key})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        assert request.user.is_authenticated
        Token.objects.filter(user=request.user).delete()
        log_action(request.user, "logout", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user
        assert user.is_authenticated
        return Response({"username": user.username, "created_at": user.date_joined})
