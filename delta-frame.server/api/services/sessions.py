from datetime import datetime
from uuid import UUID, uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from api.models import InspectionSession, Tool, User

ALLOWED_UPDATE_FIELDS: set[str] = {"worker", "conclusion"}

def list_sessions(
    *,
    tool_id: UUID | None = None,
    session_type: str | None = None,
    status: str | None = None,
    conclusion: str | None = None,
    worker_id: int | None = None,
) -> QuerySet[InspectionSession]:
    """List inspection sessions with optional filters, ordered newest first."""
    queryset = InspectionSession.objects.select_related(
        "tool", "inspector", "worker"
    ).order_by("-created_at")

    if tool_id is not None:
        queryset = queryset.filter(tool_id=tool_id)
    if session_type is not None:
        queryset = queryset.filter(session_type=session_type)
    if status is not None:
        queryset = queryset.filter(status=status)
    if conclusion is not None:
        queryset = queryset.filter(conclusion=conclusion)
    if worker_id is not None:
        queryset = queryset.filter(worker_id=worker_id)

    return queryset

def get_session_by_id(session_id: UUID) -> InspectionSession:
    """Load an inspection session with related entities, photos, and defect analyses."""
    return (
        InspectionSession.objects.select_related("tool", "inspector", "worker")
        .prefetch_related(
            "photos__angle",
            "defect_analyses__before_photo",
            "defect_analyses__after_photo",
        )
        .get(pk=session_id)
    )

@transaction.atomic
def create_or_sync_session(
    *,
    session_id: UUID | None = None,
    tool: Tool,
    inspector: User,
    worker: User | None = None,
    session_type: str,
    created_at: datetime | None = None,
) -> tuple[InspectionSession, bool]:
    """Create an online session or idempotently sync an offline client session."""
    if inspector.role not in ("INSPECTOR", "ADMIN"):
        raise ValidationError(
            "Inspector must have role INSPECTOR or ADMIN.",
            code="invalid_inspector_role",
        )

    resolved_id = session_id or uuid4()
    resolved_created_at = created_at or timezone.now()

    existing = (
        InspectionSession.objects.filter(id=resolved_id)
        .only("id", "status")
        .first()
    )

    is_already_synced = existing is not None and existing.status in (
        "SYNCED",
        "COMPLETED",
    )
    if session_type == "ISSUANCE" and not is_already_synced:
        if tool.status != "AVAILABLE":
            raise ValidationError(
                "Tool must be AVAILABLE to start an ISSUANCE session.",
                code="tool_unavailable",
            )

    resolved_status = (
        "COMPLETED"
        if existing is not None and existing.status == "COMPLETED"
        else "SYNCED"
    )

    session, created = InspectionSession.objects.update_or_create(
        id=resolved_id,
        defaults={
            "tool": tool,
            "inspector": inspector,
            "worker": worker,
            "session_type": session_type,
            "status": resolved_status,
            "created_at": resolved_created_at,
        },
    )
    return session, created

def update_session(session: InspectionSession, **fields) -> InspectionSession:
    """Update worker or conclusion on a non-completed session."""
    if session.status == "COMPLETED":
        raise ValidationError(
            "Completed sessions cannot be modified.",
            code="session_locked",
        )

    for field_name, value in fields.items():
        if field_name in ALLOWED_UPDATE_FIELDS:
            setattr(session, field_name, value)

    session.save()
    return session

@transaction.atomic
def complete_session(
    session: InspectionSession,
    *,
    conclusion: str,
) -> InspectionSession:
    """Complete a session and atomically transition the associated tool's status."""
    tool = Tool.objects.select_for_update().get(id=session.tool_id)

    session.status = "COMPLETED"
    session.conclusion = conclusion
    session.save(update_fields=["status", "conclusion"])

    if session.session_type == "ISSUANCE":
        tool.status = "IN_USE"
    elif session.session_type == "RETURN":
        if conclusion == "DAMAGED":
            tool.status = "MAINTENANCE"
        elif conclusion in ("CLEAN", "MINOR_WEAR"):
            tool.status = "AVAILABLE"

    tool.save(update_fields=["status"])
    return session

def delete_session(session: InspectionSession) -> None:
    """Delete a session only if it is still in PENDING status."""
    if session.status != "PENDING":
        raise ValidationError(
            "Synced or completed sessions cannot be deleted.",
            code="session_locked",
        )
    session.delete()
