from rest_framework import serializers

class UploadPhotoRequestDTO(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    session_id = serializers.UUIDField()
    angle_id = serializers.IntegerField()
    image_file = serializers.ImageField()
    source_device = serializers.ChoiceField(choices=["IOT", "MOBILE"])
    measured_distance_cm = serializers.FloatField(min_value=0.0)
    measured_lux = serializers.IntegerField(min_value=0)
    timestamp = serializers.DateTimeField(required=False)

class PhotoResponseDTO(serializers.Serializer):
    id = serializers.UUIDField()
    session_id = serializers.UUIDField()
    angle_id = serializers.IntegerField()
    angle_name = serializers.CharField(source="angle.name")
    image_url = serializers.SerializerMethodField()
    source_device = serializers.CharField()
    measured_distance_cm = serializers.FloatField()
    measured_lux = serializers.IntegerField()
    is_geometry_valid = serializers.BooleanField()
    timestamp = serializers.DateTimeField()

    def get_image_url(self, obj) -> str:
        if obj.image_file:
            return obj.image_file.url
        return ""