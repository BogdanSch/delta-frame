from rest_framework import serializers
from api.models import User

class CreateUserRequestDTO(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=4)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    role = serializers.ChoiceField(
        choices=[c[0] for c in User.ROLE_CHOICES],
        required=False,
        default="WORKER",
    )
    first_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    last_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )

class UpdateUserRequestDTO(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=[c[0] for c in User.ROLE_CHOICES],
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(write_only=True, min_length=4, required=False)

class UserResponseDTO(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()
