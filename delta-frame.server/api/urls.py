from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views import defects, photos, sessions, tools, users

urlpatterns = [
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path(
        "api/v1/auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="openapi-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="openapi-schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="openapi-schema"),
        name="redoc-ui",
    ),
    # Users & Equipment Registry
    path("api/v1/users/me/", users.UserMeView.as_view(), name="user-me"),
    path("api/v1/users/", users.UserListCreateView.as_view(), name="user-list"),
    path(
        "api/v1/users/<int:user_id>/",
        users.UserDetailView.as_view(),
        name="user-detail",
    ),
    path("api/v1/tools/", tools.ToolListCreateView.as_view(), name="tool-list"),
    path(
        "api/v1/tools/by-qr/<str:qr_code>/",
        tools.ToolByQrView.as_view(),
        name="tool-by-qr",
    ),
    path(
        "api/v1/tools/<uuid:tool_id>/",
        tools.ToolDetailView.as_view(),
        name="tool-detail",
    ),
    path(
        "api/v1/camera-angles/",
        tools.CameraAngleListCreateView.as_view(),
        name="angle-list",
    ),
    path(
        "api/v1/camera-angles/<int:angle_id>/",
        tools.CameraAngleDetailView.as_view(),
        name="angle-detail",
    ),
    path(
        "api/v1/sessions/",
        sessions.SessionListCreateView.as_view(),
        name="session-list",
    ),
    path(
        "api/v1/sessions/sync/",
        sessions.SessionSyncView.as_view(),
        name="session-sync",
    ),
    path(
        "api/v1/sessions/<uuid:session_id>/",
        sessions.SessionDetailView.as_view(),
        name="session-detail",
    ),
    path(
        "api/v1/sessions/<uuid:session_id>/complete/",
        sessions.SessionCompleteView.as_view(),
        name="session-complete",
    ),
    path(
        "api/v1/photos/",
        photos.PhotoListUploadView.as_view(),
        name="photo-list",
    ),
    path(
        "api/v1/photos/<uuid:photo_id>/",
        photos.PhotoDetailView.as_view(),
        name="photo-detail",
    ),
    path("api/v1/defects/", defects.DefectListView.as_view(), name="defect-list"),
    path(
        "api/v1/defects/<uuid:defect_id>/",
        defects.DefectDetailView.as_view(),
        name="defect-detail",
    ),
    path(
        "api/v1/defects/<uuid:defect_id>/approve/",
        defects.DefectApproveView.as_view(),
        name="defect-approve",
    ),
]
