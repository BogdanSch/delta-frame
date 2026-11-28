from rest_framework import serializers

from api.dtos.defects import DefectAnalysisResponseDTO
from api.dtos.photos import PhotoResponseDTO
from api.models import InspectionSession

class CreateSessionRequestDTO(serializers.Serializer):
    tool_id = serializers.UUIDField()
    worker_id = serializers.IntegerField(required=False, allow_null=True)
    session_type = serializers.ChoiceField(
        choices=[c[0] for c in InspectionSession.SESSION_TYPE_CHOICES]
    )

class SyncSessionRequestDTO(serializers.Serializer):
    id = serializers.UUIDField()
    tool_id = serializers.UUIDField()
    worker_id = serializers.IntegerField(required=False, allow_null=True)
    session_type = serializers.ChoiceField(
        choices=[c[0] for c in InspectionSession.SESSION_TYPE_CHOICES]
    )
    created_at = serializers.DateTimeField()

class UpdateSessionRequestDTO(serializers.Serializer):
    worker_id = serializers.IntegerField(required=False, allow_null=True)
    conclusion = serializers.ChoiceField(
        choices=[c[0] for c in InspectionSession.CONCLUSION_CHOICES],
        required=False,
    )

class CompleteSessionRequestDTO(serializers.Serializer):
    conclusion = serializers.ChoiceField(
        choices=[c[0] for c in InspectionSession.CONCLUSION_CHOICES]
    )

class SessionSummaryResponseDTO(serializers.Serializer):
    id = serializers.UUIDField()
    tool_id = serializers.UUIDField()
    tool_name = serializers.CharField(source="tool.name")
    inspector_id = serializers.IntegerField()
    worker_id = serializers.IntegerField(allow_null=True)
    session_type = serializers.CharField()
    status = serializers.CharField()
    conclusion = serializers.CharField()
    created_at = serializers.DateTimeField()

class SessionDetailResponseDTO(SessionSummaryResponseDTO):
    photos = PhotoResponseDTO(many=True)
    defect_analyses = DefectAnalysisResponseDTO(many=True)
