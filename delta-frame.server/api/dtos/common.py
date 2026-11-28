from rest_framework import serializers

class PaginationQueryDTO(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(
        required=False, min_value=1, max_value=100, default=20
    )

class ProblemDetailDTO(serializers.Serializer):
    title = serializers.CharField()
    status = serializers.IntegerField()
    detail = serializers.CharField()
    code = serializers.CharField()
    errors = serializers.DictField(required=False)