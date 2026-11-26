from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from api.models import CameraAngle, DefectAnalysis, InspectionSession, PhotoRecord

def validate_difference_index(difference_index: float) -> None:
    if not (0.0 <= difference_index <= 1.0):
        raise ValidationError(
            "difference_index must be between 0.0 and 1.0.",
            code="invalid_difference_index",
        )

def list_defects(
    *,
    session_id: UUID | None = None,
    tool_id: UUID | None = None,
    is_approved: bool | None = None,
) -> QuerySet[DefectAnalysis]:
    """List defect analyses filtered by session, tool, or human approval status."""
    queryset = DefectAnalysis.objects.select_related(
        "session__tool", "angle", "before_photo", "after_photo"
    )
    if session_id is not None:
        queryset = queryset.filter(session_id=session_id)
    if tool_id is not None:
        queryset = queryset.filter(session__tool_id=tool_id)
    if is_approved is not None:
        queryset = queryset.filter(is_approved_by_human=is_approved)
    return queryset


def get_defect_by_id(defect_id: UUID) -> DefectAnalysis:
    """Fetch a single defect analysis with related photos, angle, and session."""
    return DefectAnalysis.objects.select_related(
        "session__tool", "angle", "before_photo", "after_photo"
    ).get(pk=defect_id)

def upsert_defect_analysis(
    *,
    session: InspectionSession,
    angle: CameraAngle,
    before_photo: PhotoRecord,
    after_photo: PhotoRecord,
    difference_index: float = 0.0,
    description: str = "",
    bounding_boxes: list | None = None,
) -> DefectAnalysis:
    """Create or update the defect analysis pair for a given (session, angle)."""
    if before_photo.angle_id != angle.id or after_photo.angle_id != angle.id:
        raise ValidationError(
            "Both before_photo and after_photo must belong to the specified angle.",
            code="angle_mismatch",
        )
    validate_difference_index(difference_index)

    analysis, _ = DefectAnalysis.objects.update_or_create(
        session=session,
        angle=angle,
        defaults={
            "before_photo": before_photo,
            "after_photo": after_photo,
            "difference_index": difference_index,
            "description": description,
            "bounding_boxes": [] if bounding_boxes is None else bounding_boxes,
        },
    )
    return analysis

def update_analysis_results(
    analysis: DefectAnalysis,
    *,
    difference_index: float,
    description: str = "",
    bounding_boxes: list | None = None,
) -> DefectAnalysis:
    """Populate CV/LLM comparison metrics on an existing defect analysis."""
    validate_difference_index(difference_index)
    analysis.difference_index = difference_index
    analysis.description = description
    analysis.bounding_boxes = [] if bounding_boxes is None else bounding_boxes
    analysis.save(
        update_fields=["difference_index", "description", "bounding_boxes"]
    )
    return analysis

def approve_defect_analysis(
    analysis: DefectAnalysis,
    *,
    description: str | None = None,
    bounding_boxes: list | None = None,
) -> DefectAnalysis:
    """Apply optional inspector edits and mark the defect analysis as approved."""
    if description is not None:
        analysis.description = description
    if bounding_boxes is not None:
        analysis.bounding_boxes = bounding_boxes
    analysis.is_approved_by_human = True
    analysis.save(
        update_fields=["description", "bounding_boxes", "is_approved_by_human"]
    )
    return analysis

def delete_defect_analysis(analysis: DefectAnalysis) -> None:
    """Delete an unapproved defect analysis; block deletion once approved."""
    if analysis.is_approved_by_human:
        raise ValidationError(
            "Approved defect analyses cannot be deleted.",
            code="analysis_approved",
        )
    analysis.delete()