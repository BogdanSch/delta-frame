from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError, QuerySet
from api.models import Tool

ALLOWED_UPDATE_FIELDS = {"name", "description", "status"}

def list_tools(*, status: str | None = None) -> QuerySet[Tool]:
    """List tools with prefetched camera angles, optionally filtered by status."""
    queryset = Tool.objects.prefetch_related("camera_angles").order_by("name")
    if status is not None:
        queryset = queryset.filter(status=status)
    return queryset

def get_tool_by_id(tool_id: UUID) -> Tool:
    """Fetch a single tool with prefetched camera angles."""
    return Tool.objects.prefetch_related("camera_angles").get(pk=tool_id)

def get_tool_by_qr(qr_code: str) -> Tool:
    """Normalize a QR code and fetch the matching tool with prefetched camera angles."""
    normalized_qr = qr_code.strip().upper()
    return Tool.objects.prefetch_related("camera_angles").get(qr_code=normalized_qr)

def create_tool(*, name: str, description: str = "") -> Tool:
    """Create a tool with a stripped name; QR code is generated on save."""
    return Tool.objects.create(name=name.strip(), description=description)

def update_tool(tool: Tool, **fields) -> Tool:
    """Update mutable tool fields while ignoring any attempt to mutate qr_code."""
    fields.pop("qr_code", None)
    for field_name, value in fields.items():
        if field_name not in ALLOWED_UPDATE_FIELDS:
            continue
        if field_name == "name" and isinstance(value, str):
            value = value.strip()
        setattr(tool, field_name, value)

    tool.save()
    return tool

def delete_tool(tool: Tool) -> None:
    """Delete a tool unless it is in use or referenced by historical inspection sessions."""
    if tool.status == "IN_USE":
        raise ValidationError(
            "Tool is currently in use and cannot be deleted.",
            code="tool_in_use",
        )
    try:
        tool.delete()
    except ProtectedError as exc:
        raise ValidationError(
            "Tool has historical inspection sessions and cannot be deleted.",
            code="tool_has_history",
        ) from exc
