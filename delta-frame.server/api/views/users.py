from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.dtos.common import ProblemDetailDTO
from api.dtos.users import CreateUserRequestDTO, UpdateUserRequestDTO, UserResponseDTO
from api.models import User
from api.permissions import IsAdmin
from api.services import users as user_service

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        responses={200: UserResponseDTO, 401: ProblemDetailDTO},
    )
    def get(self, request):
        return Response(UserResponseDTO(request.user).data, status=status.HTTP_200_OK)

class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Users"],
        parameters=[
            OpenApiParameter(
                name="role",
                type=str,
                required=False,
                enum=[c[0] for c in User.ROLE_CHOICES],
            ),
            OpenApiParameter(name="is_active", type=bool, required=False),
        ],
        responses={200: UserResponseDTO(many=True), 401: ProblemDetailDTO, 403: ProblemDetailDTO},
    )
    def get(self, request):
        role = request.query_params.get("role")
        is_active_param = request.query_params.get("is_active")
        is_active: bool | None = True
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1", "yes")
        queryset = user_service.list_users(role=role, is_active=is_active)
        return Response(UserResponseDTO(queryset, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Users"],
        request=CreateUserRequestDTO,
        responses={
            201: UserResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
        },
    )
    def post(self, request):
        dto = CreateUserRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        user = user_service.create_user(**dto.validated_data)
        return Response(UserResponseDTO(user).data, status=status.HTTP_201_CREATED)

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_user(self, user_id: int) -> User:
        try:
            return user_service.get_user_by_id(user_id)
        except User.DoesNotExist as exc:
            raise Http404("User not found.") from exc

    @extend_schema(
        tags=["Users"],
        responses={
            200: UserResponseDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def get(self, request, user_id: int):
        user = self._get_user(user_id)
        return Response(UserResponseDTO(user).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Users"],
        request=UpdateUserRequestDTO,
        responses={
            200: UserResponseDTO,
            400: ProblemDetailDTO,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def patch(self, request, user_id: int):
        user = self._get_user(user_id)
        dto = UpdateUserRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        updated = user_service.update_user(user, **dto.validated_data)
        return Response(UserResponseDTO(updated).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Users"],
        responses={
            204: None,
            401: ProblemDetailDTO,
            403: ProblemDetailDTO,
            404: ProblemDetailDTO,
        },
    )
    def delete(self, request, user_id: int):
        user = self._get_user(user_id)
        user_service.deactivate_user(user)
        return Response(status=status.HTTP_204_NO_CONTENT)
