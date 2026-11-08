from django.urls import path
from .views import (
    ABETReportExportAPIView,
    CanvasSyncWebhookAPIView,
    CourseOutcomeMappingAPIView,
    DashboardStateAPIView,
    InstitutionalSSOAPIView,
    MiddlewareConfigAPIView,
    RotateAPIKeyAPIView,
    dashboard_view,
)

urlpatterns = [
    path('', dashboard_view, name='empowered-dashboard'),
    path('api/v2/hooks/canvas-sync/', CanvasSyncWebhookAPIView.as_view(), name='canvas-sync-webhook'),
    path('api/v2/dashboard/state/', DashboardStateAPIView.as_view(), name='dashboard-state'),
    path('api/v2/auth/sso/', InstitutionalSSOAPIView.as_view(), name='institutional-sso'),
    path('api/v2/matrix/mapping/', CourseOutcomeMappingAPIView.as_view(), name='course-matrix-mapping'),
    path('api/v2/reports/abet-ssr/', ABETReportExportAPIView.as_view(), name='abet-ssr-export'),
    path('api/v2/config/rotate-key/', RotateAPIKeyAPIView.as_view(), name='rotate-api-key'),
    path('api/v2/config/settings/', MiddlewareConfigAPIView.as_view(), name='middleware-config-settings'),
]

