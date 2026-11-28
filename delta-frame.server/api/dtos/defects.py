from rest_framework import serializers

class UpdateDefectRequestDTO(serializers.Serializer):
    difference_index = serializers.FloatField(
        min_value=0.0, max_value=1.0, required=False
    )
    description = serializers.CharField(required=False, allow_blank=True)
    bounding_boxes = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )

class ApproveDefectRequestDTO(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True)
    bounding_boxes = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )

class DefectAnalysisResponseDTO(serializers.Serializer):
    id = serializers.UUIDField()
    session_id = serializers.UUIDField()
    angle_id = serializers.IntegerField()
    before_photo_id = serializers.UUIDField()
    before_image_url = serializers.SerializerMethodField()
    after_photo_id = serializers.UUIDField()
    after_image_url = serializers.SerializerMethodField()
    difference_index = serializers.FloatField()
    description = serializers.CharField()
    bounding_boxes = serializers.ListField(child=serializers.DictField())
    is_approved_by_human = serializers.BooleanField()

    def get_before_image_url(self, obj) -> str:
        if obj.before_photo and obj.before_photo.image_file:
            return obj.before_photo.image_file.url
        return ""

    def get_after_image_url(self, obj) -> str:
        if obj.after_photo and obj.after_photo.image_file:
            return obj.after_photo.image_file.url
        return ""