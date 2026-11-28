from rest_framework import serializers
from api.models import Tool

class CreateToolRequestDTO(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")

class UpdateToolRequestDTO(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=[c[0] for c in Tool.STATUS_CHOICES],
        required=False,
    )

class CreateCameraAngleRequestDTO(serializers.Serializer):
    tool_id = serializers.UUIDField()
    name = serializers.CharField(max_length=100)
    target_distance_cm = serializers.FloatField(min_value=0.0)
    target_lux = serializers.IntegerField(min_value=0)
    tolerance_margin_cm = serializers.FloatField(
        min_value=0.0, required=False, default=2.5
    )

class UpdateCameraAngleRequestDTO(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    target_distance_cm = serializers.FloatField(min_value=0.0, required=False)
    target_lux = serializers.IntegerField(min_value=0, required=False)
    tolerance_margin_cm = serializers.FloatField(min_value=0.0, required=False)

class CameraAngleResponseDTO(serializers.Serializer):
    id = serializers.IntegerField()
    tool_id = serializers.UUIDField()
    name = serializers.CharField()
    target_distance_cm = serializers.FloatField()
    target_lux = serializers.IntegerField()
    tolerance_margin_cm = serializers.FloatField()

class ToolDetailResponseDTO(serializers.Serializer):
    id = serializers.UUIDField()
    qr_code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    camera_angles = CameraAngleResponseDTO(many=True)