from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError, QuerySet

from api.models import CameraAngle, Tool

ALLOWED_UPDATE_FIELDS: str[str] = {
    "name",
    "target_distance_cm",
    "target_lux",
    "tolerance_margin_cm",
}

def list_angles_for_tool(tool_id: UUID) -> QuerySet[CameraAngle]:
    """List camera angles for a specific tool ordered by name."""
    return CameraAngle.objects.filter(tool_id=tool_id).order_by("name")

def get_angle_by_id(angle_id: int) -> CameraAngle:
    """Fetch a single camera angle with its related tool."""
    return CameraAngle.objects.select_related("tool").get(pk=angle_id)

def create_camera_angle(
    *,
    tool: Tool,
    name: str,
    target_distance_cm: float,
    target_lux: int,
    tolerance_margin_cm: float = 2.5,
) -> CameraAngle:
    """Create a camera angle after verifying case-insensitive uniqueness per tool."""
    normalized_name = name.strip()
    if CameraAngle.objects.filter(tool=tool, name__iexact=normalized_name).exists():
        raise ValidationError(
            f"Camera angle '{normalized_name}' already exists for this tool.",
            code="duplicate_angle",
        )
    return CameraAngle.objects.create(
        tool=tool,
        name=normalized_name,
        target_distance_cm=target_distance_cm,
        target_lux=target_lux,
        tolerance_margin_cm=tolerance_margin_cm,
    )

def update_camera_angle(angle: CameraAngle, **fields) -> CameraAngle:
    """Update camera angle calibration fields and enforce per-tool name uniqueness."""
    if "name" in fields:
        normalized_name = fields["name"].strip()
        if (
            CameraAngle.objects.filter(
                tool_id=angle.tool_id,
                name__iexact=normalized_name,
            )
            .exclude(pk=angle.pk)
            .exists()
        ):
            raise ValidationError(
                f"Camera angle '{normalized_name}' already exists for this tool.",
                code="duplicate_angle",
            )
        fields["name"] = normalized_name

    for field_name, value in fields.items():
        if field_name in ALLOWED_UPDATE_FIELDS:
            setattr(angle, field_name, value)

    angle.save()
    return angle

def delete_camera_angle(angle: CameraAngle) -> None:
    """Delete a camera angle unless referenced by recorded photos."""
    try:
        angle.delete()
    except ProtectedError as exc:
        raise ValidationError(
            "Camera angle is referenced by recorded photos.",
            code="angle_in_use",
        ) from exc
