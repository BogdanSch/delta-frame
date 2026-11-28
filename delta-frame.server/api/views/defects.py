from uuid import UUID

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.dtos.common import ProblemDetailDTO
from api.dtos.defects import ApproveDefectRequestDTO, DefectAnalysisResponseDTO, UpdateDefectRequestDTO
from api.models import DefectAnalysis
from api.permissions import IsAdmin, IsInspector, IsReadOnly
from api.services import defects as defect_service

def get_defect(defect_id: UUID) -> DefectAnalysis:
    try:
        return defect_service.get_defect_by_id(defect_id)
    except DefectAnalysis.DoesNotExist as exc:
        raise Http404("Defect analysis not found.") from exc

class DefectListView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    @extend_schema(
        tags=["Defects"],
        parameters=[
            OpenApiParameter(name="session_id", type=UUID, required=False),
            OpenApiParameter(name="tool_id", type=UUID, required=False),
            OpenApiParameter(name="is_approved", type=bool, required=False),
        ],
        responses={200: DefectAnalysisResponseDTO(many=True), 401: ProblemDetailDTO},
    )
    def get(self, request):
        params = request.query_params
        session_id = UUID(params["session_id"]) if params.get("session_id") else None
        tool_id = UUID(params["tool_id"]) if params.get("tool_id") else None
        is_approved = None
        if params.get("is_approved") is not None:
            is_approved = params["is_approved"].lower() in ("true", "1", "yes")

        queryset = defect_service.list_defects(
            session_id=session_id,
            tool_id=tool_id,
            is_approved=is_approved,
        )
        return Response(
            DefectAnalysisResponseDTO(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )

class DefectDetailView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    @extend_schema(
        tags=["Defects"],
        responses={
            200: DefectAnalysisResponseDTO,
            401: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def get(self, request, defect_id: UUID):
        defect = get_defect(defect_id)
        return Response(
            DefectAnalysisResponseDTO(defect).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Defects"],
        request=UpdateDefectRequestDTO,
        responses={
            200: DefectAnalysisResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def patch(self, request, defect_id: UUID):
        defect = get_defect(defect_id)
        dto = UpdateDefectRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data

        updated = defect_service.update_analysis_results(
            defect,
            difference_index=data.get("difference_index", defect.difference_index),
            description=data.get("description", defect.description),
            bounding_boxes=data.get("bounding_boxes", defect.bounding_boxes),
        )
        return Response(
            DefectAnalysisResponseDTO(updated).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Defects"],
        responses={
            204: None,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def delete(self, request, defect_id: UUID):
        defect = get_defect(defect_id)
        defect_service.delete_defect_analysis(defect)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DefectApproveView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin]

    @extend_schema(
        tags=["Defects"],
        request=ApproveDefectRequestDTO,
        responses={
            200: DefectAnalysisResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def patch(self, request, defect_id: UUID):
        defect = get_defect(defect_id)

        dto = ApproveDefectRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        approved = defect_service.approve_defect_analysis(defect, **dto.validated_data)
        return Response(
            DefectAnalysisResponseDTO(approved).data,
            status=status.HTTP_200_OK,
        )
