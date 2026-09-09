from django.contrib.auth.models import User
from django.db import models


class VaultUserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    kdf_salt = models.BinaryField(max_length=64)
    verifier_salt = models.BinaryField(max_length=64)
    verifier = models.BinaryField(max_length=64)
    kdf_params = models.JSONField(default=dict)
