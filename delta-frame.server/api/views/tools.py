from uuid import UUID

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.dtos.common import ProblemDetailDTO
from api.dtos.tools import (
    CameraAngleResponseDTO,
    CreateCameraAngleRequestDTO,
    CreateToolRequestDTO,
    ToolDetailResponseDTO,
    UpdateCameraAngleRequestDTO,
    UpdateToolRequestDTO,
)
from api.models import CameraAngle, Tool
from api.permissions import IsAdmin, IsInspector, IsReadOnly
from api.services import camera_angles as angle_service
from api.services import tools as tool_service

class ToolListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    @extend_schema(
        tags=["Tools"],
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                required=False,
                enum=[c[0] for c in Tool.STATUS_CHOICES],
            ),
        ],
        responses={200: ToolDetailResponseDTO(many=True), 401: ProblemDetailDTO},
    )
    def get(self, request):
        tool_status = request.query_params.get("status")
        queryset = tool_service.list_tools(status=tool_status)
        return Response(
            ToolDetailResponseDTO(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Tools"],
        request=CreateToolRequestDTO,
        responses={
            201: ToolDetailResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
        },
    )
    def post(self, request):
        dto = CreateToolRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        tool = tool_service.create_tool(**dto.validated_data)
        return Response(
            ToolDetailResponseDTO(tool).data,
            status=status.HTTP_201_CREATED,
        )


class ToolByQrView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tools"],
        responses={
            200: ToolDetailResponseDTO,
            401: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def get(self, request, qr_code: str):
        try:
            tool = tool_service.get_tool_by_qr(qr_code)
        except Tool.DoesNotExist as exc:
            raise Http404("Tool not found for QR code.") from exc
        return Response(ToolDetailResponseDTO(tool).data, status=status.HTTP_200_OK)


class ToolDetailView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    def _get_tool(self, tool_id: UUID) -> Tool:
        try:
            return tool_service.get_tool_by_id(tool_id)
        except Tool.DoesNotExist as exc:
            raise Http404("Tool not found.") from exc

    @extend_schema(
        tags=["Tools"],
        responses={
            200: ToolDetailResponseDTO,
            401: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def get(self, request, tool_id: UUID):
        tool = self._get_tool(tool_id)
        return Response(ToolDetailResponseDTO(tool).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Tools"],
        request=UpdateToolRequestDTO,
        responses={
            200: ToolDetailResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def patch(self, request, tool_id: UUID):
        tool = self._get_tool(tool_id)
        dto = UpdateToolRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        updated = tool_service.update_tool(tool, **dto.validated_data)
        return Response(ToolDetailResponseDTO(updated).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Tools"],
        responses={
            204: None,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def delete(self, request, tool_id: UUID):
        tool = self._get_tool(tool_id)
        tool_service.delete_tool(tool)
        return Response(status=status.HTTP_204_NO_CONTENT)

class CameraAngleListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    @extend_schema(
        tags=["Camera Angles"],
        parameters=[
            OpenApiParameter(name="tool_id", type=UUID, required=False),
        ],
        responses={200: CameraAngleResponseDTO(many=True), 401: ProblemDetailDTO},
    )
    def get(self, request):
        tool_id = request.query_params.get("tool_id")
        if tool_id:
            queryset = angle_service.list_angles_for_tool(UUID(tool_id))
        else:
            queryset = CameraAngle.objects.all().order_by("tool_id", "name")
        return Response(
            CameraAngleResponseDTO(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Camera Angles"],
        request=CreateCameraAngleRequestDTO,
        responses={
            201: CameraAngleResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def post(self, request):
        dto = CreateCameraAngleRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data
        try:
            tool = tool_service.get_tool_by_id(data.get("tool_id"))
        except Tool.DoesNotExist as exc:
            raise Http404("Tool not found.") from exc

        angle = angle_service.create_camera_angle(
            tool=tool,
            name=data.get("name"),
            target_distance_cm=data.get("target_distance_cm"),
            target_lux=data.get("target_lux"),
            tolerance_margin_cm=data.get("tolerance_margin_cm"),
        )
        return Response(
            CameraAngleResponseDTO(angle).data,
            status=status.HTTP_201_CREATED,
        )

class CameraAngleDetailView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    def _get_angle(self, angle_id: int) -> CameraAngle:
        try:
            return angle_service.get_angle_by_id(angle_id)
        except CameraAngle.DoesNotExist as exc:
            raise Http404("Camera angle not found.") from exc

    @extend_schema(
        tags=["Camera Angles"],
        responses={
            200: CameraAngleResponseDTO,
            401: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def get(self, request, angle_id: int):
        angle = self._get_angle(angle_id)
        return Response(CameraAngleResponseDTO(angle).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Camera Angles"],
        request=UpdateCameraAngleRequestDTO,
        responses={
            200: CameraAngleResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def patch(self, request, angle_id: int):
        angle = self._get_angle(angle_id)
        dto = UpdateCameraAngleRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        updated = angle_service.update_camera_angle(angle, **dto.validated_data)
        return Response(CameraAngleResponseDTO(updated).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Camera Angles"],
        responses={
            204: None,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def delete(self, request, angle_id: int):
        angle = self._get_angle(angle_id)
        angle_service.delete_camera_angle(angle)
        return Response(status=status.HTTP_204_NO_CONTENT)
