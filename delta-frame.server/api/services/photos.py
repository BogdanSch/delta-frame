from datetime import datetime
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.db import transaction
from django.db.models import ProtectedError, QuerySet
from django.utils import timezone
from api.models import CameraAngle, InspectionSession, PhotoRecord
from api.services import defects

def list_photos_for_session(session_id: UUID) -> QuerySet[PhotoRecord]:
    """List photos recorded for a session, ordered chronologically."""
    return (
        PhotoRecord.objects.filter(session_id=session_id)
        .select_related("angle")
        .order_by("timestamp")
    )

def get_photo_by_id(photo_id: UUID) -> PhotoRecord:
    """Fetch a single photo record with its session and camera angle."""
    return PhotoRecord.objects.select_related("session", "angle").get(pk=photo_id)

def get_latest_issuance_photo(
    *,
    tool_id: UUID,
    angle_id: int,
) -> PhotoRecord | None:
    """Return the best/latest issuance photo for a tool and angle as a baseline."""
    return (
        PhotoRecord.objects.filter(
            session__tool_id=tool_id,
            angle_id=angle_id,
            session__session_type="ISSUANCE",
        )
        .order_by("-is_geometry_valid", "-timestamp")
        .first()
    )

@transaction.atomic
def record_photo(
    *,
    photo_id: UUID | None = None,
    session: InspectionSession,
    angle: CameraAngle,
    image_file: File,
    source_device: str,
    measured_distance_cm: float,
    measured_lux: int,
    timestamp: datetime | None = None,
) -> PhotoRecord:
    """Validate geometry server-side, upsert a photo, and pair RETURN frames for analysis."""
    if angle.tool_id != session.tool_id:
        raise ValidationError(
            "Camera angle does not belong to the session's tool.",
            code="angle_tool_mismatch",
        )

    is_geometry_valid = (
        abs(measured_distance_cm - angle.target_distance_cm)
        <= angle.tolerance_margin_cm
    )
    resolved_timestamp = timestamp or timezone.now()

    defaults = {
        "image_file": image_file,
        "source_device": source_device,
        "measured_distance_cm": measured_distance_cm,
        "measured_lux": measured_lux,
        "is_geometry_valid": is_geometry_valid,
        "timestamp": resolved_timestamp,
    }
    create_defaults = dict(defaults)
    if photo_id is not None:
        create_defaults["id"] = photo_id

    photo, _ = PhotoRecord.objects.update_or_create(
        session=session,
        angle=angle,
        defaults=defaults,
        create_defaults=create_defaults,
    )

    if session.session_type == "RETURN":
        baseline = get_latest_issuance_photo(
            tool_id=session.tool_id,
            angle_id=angle.id,
        )
        if baseline is not None:
            defects.upsert_defect_analysis(
                session=session,
                angle=angle,
                before_photo=baseline,
                after_photo=photo,
            )

    return photo

def delete_photo(photo: PhotoRecord) -> None:
    """Delete a photo record and its stored file unless referenced by a defect analysis."""
    image_file = photo.image_file
    try:
        photo.delete()
    except ProtectedError as exc:
        raise ValidationError(
            "Photo is referenced by a defect analysis and cannot be deleted.",
            code="photo_in_use",
        ) from exc

    if image_file:
        image_file.delete(save=False)