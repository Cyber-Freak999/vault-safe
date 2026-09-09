import base64

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.audit import log_action

from .models import VaultUserProfile
from .serializers import PreauthSerializer, RegisterSerializer


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
