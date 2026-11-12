from django.urls import path
from . import views

urlpatterns = [
    # Multi-Page Frontend Routes (Panels 01 - 08 + Overview Grid)
    path('', views.panel2_dashboard_view, name='home'),
    path('overview/', views.overview_board_view, name='overview-board'),
    path('login/', views.panel1_login_view, name='panel1-login'),
    path('logout/', views.empowered_session_logout_view, name='empowered-logout'),
    path('dashboard/', views.panel2_dashboard_view, name='panel2-dashboard'),
    path('pipeline/', views.panel3_pipeline_view, name='panel3-pipeline'),
    path('matrix/', views.panel4_matrix_view, name='panel4-matrix'),
    path('competency/', views.panel5_competency_view, name='panel5-competency'),
    path('audit-logs/', views.panel6_audit_view, name='panel6-audit'),
    path('abet-export/', views.panel7_abet_view, name='panel7-abet'),
    path('api-config/', views.panel8_config_view, name='panel8-config'),
    path('abet-report/print/', views.abet_report_print_view, name='abet-report-print'),

    # REST API Middleware Endpoints
    path('api/v2/hooks/canvas-sync/', views.CanvasSyncWebhookAPIView.as_view(), name='canvas-sync-webhook'),
    path('api/v2/dashboard/state/', views.DashboardStateAPIView.as_view(), name='dashboard-state'),
    path('api/v2/auth/sso/', views.InstitutionalSSOAPIView.as_view(), name='institutional-sso'),
    path('api/v2/auth/session-login/', views.EmpowerEdSessionLoginAPIView.as_view(), name='session-login'),
    path('api/v2/matrix/mapping/', views.CourseOutcomeMappingAPIView.as_view(), name='course-matrix-mapping'),
    path('api/v2/reports/abet-ssr/', views.ABETReportExportAPIView.as_view(), name='abet-ssr-export'),
    path('api/v2/reports/abet-print-seal/', views.ABETPrintSealAPIView.as_view(), name='abet-print-seal'),
    path('api/v2/abet/criteria/', views.ABETCriterionToggleAPIView.as_view(), name='abet-criteria'),
    path('api/v2/config/rotate-key/', views.RotateAPIKeyAPIView.as_view(), name='rotate-api-key'),
    path('api/v2/config/settings/', views.MiddlewareConfigAPIView.as_view(), name='middleware-config-settings'),
]

