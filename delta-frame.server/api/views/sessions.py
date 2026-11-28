from uuid import UUID

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.dtos.common import ProblemDetailDTO
from api.dtos.sessions import (
    CompleteSessionRequestDTO,
    CreateSessionRequestDTO,
    SessionDetailResponseDTO,
    SessionSummaryResponseDTO,
    SyncSessionRequestDTO,
    UpdateSessionRequestDTO,
)
from api.models import InspectionSession, Tool, User
from api.permissions import IsAdmin, IsInspector, IsReadOnly
from api.services import sessions as session_service

def resolve_tool_and_worker(tool_id: UUID, worker_id: int | None) -> tuple[Tool, User | None]:
    try:
        tool = Tool.objects.get(id=tool_id)
    except Tool.DoesNotExist as exc:
        raise Http404("Tool not found.") from exc

    worker = None
    if worker_id is not None:
        try:
            worker = User.objects.get(id=worker_id)
        except User.DoesNotExist as exc:
            raise Http404("Worker not found.") from exc
    return tool, worker

def get_session(session_id: UUID) -> InspectionSession:
    try:
        return session_service.get_session_by_id(session_id)
    except InspectionSession.DoesNotExist as exc:
        raise Http404("Inspection session not found.") from exc

class SessionListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    @extend_schema(
        tags=["Sessions"],
        parameters=[
            OpenApiParameter(name="tool_id", type=UUID, required=False),
            OpenApiParameter(
                name="session_type",
                type=str,
                required=False,
                enum=[c[0] for c in InspectionSession.SESSION_TYPE_CHOICES],
            ),
            OpenApiParameter(
                name="status",
                type=str,
                required=False,
                enum=[c[0] for c in InspectionSession.STATUS_CHOICES],
            ),
            OpenApiParameter(
                name="conclusion",
                type=str,
                required=False,
                enum=[c[0] for c in InspectionSession.CONCLUSION_CHOICES],
            ),
            OpenApiParameter(name="worker_id", type=int, required=False),
        ],
        responses={200: SessionSummaryResponseDTO(many=True), 401: ProblemDetailDTO},
    )
    def get(self, request):
        params = request.query_params
        tool_id = UUID(params["tool_id"]) if params.get("tool_id") else None
        worker_id = int(params["worker_id"]) if params.get("worker_id") else None
        queryset = session_service.list_sessions(
            tool_id=tool_id,
            session_type=params.get("session_type"),
            status=params.get("status"),
            conclusion=params.get("conclusion"),
            worker_id=worker_id,
        )
        return Response(
            SessionSummaryResponseDTO(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Sessions"],
        request=CreateSessionRequestDTO,
        responses={
            201: SessionSummaryResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def post(self, request):
        dto = CreateSessionRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data
        tool, worker = resolve_tool_and_worker(data.get("tool_id"), data.get("worker_id"))

        session, _ = session_service.create_or_sync_session(
            tool=tool,
            inspector=request.user,
            worker=worker,
            session_type=data.get("session_type"),
        )
        return Response(
            SessionSummaryResponseDTO(session).data,
            status=status.HTTP_201_CREATED,
        )

class SessionSyncView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin]

    @extend_schema(
        tags=["Sessions"],
        request=SyncSessionRequestDTO,
        responses={
            200: SessionDetailResponseDTO,
            201: SessionDetailResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def post(self, request):
        dto = SyncSessionRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data
        tool, worker = resolve_tool_and_worker(data.get("tool_id"), data.get("worker_id"))

        session, created = session_service.create_or_sync_session(
            session_id=data.get("id"),
            tool=tool,
            inspector=request.user,
            worker=worker,
            session_type=data.get("session_type"),
            created_at=data.get("created_at"),
        )
        full_session = session_service.get_session_by_id(session.id)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(SessionDetailResponseDTO(full_session).data, status=http_status)

class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    @extend_schema(
        tags=["Sessions"],
        responses={
            200: SessionDetailResponseDTO,
            401: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def get(self, request, session_id: UUID):
        session = get_session(session_id)
        return Response(
            SessionDetailResponseDTO(session).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Sessions"],
        request=UpdateSessionRequestDTO,
        responses={
            200: SessionDetailResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def patch(self, request, session_id: UUID):
        session = get_session(session_id)
        dto = UpdateSessionRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dict(dto.validated_data)

        if "worker_id" in data:
            worker_id = data.pop("worker_id")
            if worker_id is None:
                data["worker"] = None
            else:
                try:
                    data["worker"] = User.objects.get(id=worker_id)
                except User.DoesNotExist as exc:
                    raise Http404("Worker not found.") from exc

        updated = session_service.update_session(session, **data)
        full_session = session_service.get_session_by_id(updated.id)
        return Response(
            SessionDetailResponseDTO(full_session).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Sessions"],
        responses={
            204: None,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def delete(self, request, session_id: UUID):
        session = get_session(session_id)
        session_service.delete_session(session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionCompleteView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin]

    @extend_schema(
        tags=["Sessions"],
        request=CompleteSessionRequestDTO,
        responses={
            200: SessionDetailResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def post(self, request, session_id: UUID):
        session = get_session(session_id)

        dto = CompleteSessionRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        completed = session_service.complete_session(
            session, conclusion=dto.validated_data.get("conclusion")
        )
        full_session = session_service.get_session_by_id(completed.id)
        return Response(
            SessionDetailResponseDTO(full_session).data,
            status=status.HTTP_200_OK,
        )
