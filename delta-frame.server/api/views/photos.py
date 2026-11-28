from uuid import UUID

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.dtos.common import ProblemDetailDTO
from api.dtos.photos import PhotoResponseDTO, UploadPhotoRequestDTO
from api.models import CameraAngle, InspectionSession, PhotoRecord
from api.permissions import IsAdmin, IsInspector, IsReadOnly
from api.services import photos as photo_service

class PhotoListUploadView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Photos"],
        parameters=[
            OpenApiParameter(name="session_id", type=UUID, required=False),
        ],
        responses={200: PhotoResponseDTO(many=True), 401: ProblemDetailDTO},
    )
    def get(self, request):
        session_id = request.query_params.get("session_id")
        if session_id:
            queryset = photo_service.list_photos_for_session(UUID(session_id))
        else:
            queryset = PhotoRecord.objects.select_related("angle").order_by("-timestamp")
        return Response(
            PhotoResponseDTO(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Photos"],
        request={"multipart/form-data": UploadPhotoRequestDTO},
        responses={
            201: PhotoResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def post(self, request):
        dto = UploadPhotoRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data

        try:
            session = InspectionSession.objects.get(id=data.get("session_id"))
            angle = CameraAngle.objects.get(id=data.get("angle_id"))
        except (InspectionSession.DoesNotExist, CameraAngle.DoesNotExist) as exc:
            raise Http404("Session or camera angle not found.") from exc

        photo = photo_service.record_photo(
            photo_id=data.get("id"),
            session=session,
            angle=angle,
            image_file=data.get("image_file"),
            source_device=data.get("source_device"),
            measured_distance_cm=data.get("measured_distance_cm"),
            measured_lux=data.get("measured_lux"),
            timestamp=data.get("timestamp"),
        )
        return Response(PhotoResponseDTO(photo).data, status=status.HTTP_201_CREATED)

class PhotoDetailView(APIView):
    permission_classes = [IsAuthenticated, IsInspector | IsAdmin | IsReadOnly]

    def __get_photo(self, photo_id: UUID) -> PhotoRecord:
        try:
            return photo_service.get_photo_by_id(photo_id)
        except PhotoRecord.DoesNotExist as exc:
            raise Http404("Photo not found.") from exc

    @extend_schema(
        tags=["Photos"],
        responses={
            200: PhotoResponseDTO,
            401: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def get(self, request, photo_id: UUID):
        photo = self.__get_photo(photo_id)
        return Response(PhotoResponseDTO(photo).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Photos"],
        responses={
            204: None,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def delete(self, request, photo_id: UUID):
        photo = self.__get_photo(photo_id)
        photo_service.delete_photo(photo)
        return Response(status=status.HTTP_204_NO_CONTENT)
