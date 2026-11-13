from decimal import Decimal
from functools import wraps
import hashlib
import json
import secrets
import time

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ABETCriterion,
    Course,
    CourseOutcomeMapping,
    DPAAuditLog,
    InstitutionalUser,
    MiddlewareConfig,
    StudentCompetencyRecord,
    SyncTelemetryLog,
)
from .serializers import (
    ABETCriterionToggleSerializer,
    ABETReportExportSerializer,
    CanvasWebhookIngestSerializer,
    CourseMatrixSerializer,
    DPAAuditLogSerializer,
    InstitutionalSSOSerializer,
    MatrixCellUpdateSerializer,
    MiddlewareConfigSerializer,
)
from .services import (
    DEFAULT_SSO_PASSWORD,
    build_abet_ssr_pdf,
    build_abet_state,
    compute_dashboard_metrics,
    ensure_seed_data,
)


# ---------------------------------------------------------------------------
# Session-based authentication guard
# ---------------------------------------------------------------------------

def _empowered_login_required(view_func):
    """Redirect unauthenticated visitors to /login/?next=<requested-path>."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get('empowered_authenticated'):
            login_url = reverse('panel1-login')
            next_url = request.get_full_path()
            return redirect(f'{login_url}?next={next_url}')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _write_audit(event: dict, action: str) -> tuple:
    """Persist an RA 10173 SHA-256 audit ledger row and return (entry, short_hash)."""
    raw_event = json.dumps({**event, 'ts': timezone.now().isoformat()}, default=str, sort_keys=True)
    short_hash = DPAAuditLog.generate_hash(raw_event)
    entry = DPAAuditLog.objects.create(
        sha256_payload=short_hash,
        action=action,
        privacy_verified=True,
    )
    return entry, short_hash


def _audit_payload(entry, short_hash: str) -> dict:
    return {
        'timestamp': entry.timestamp.strftime('%H:%M:%S'),
        'sha256_payload': short_hash,
        'action': entry.action,
    }


def _issue_oauth_token() -> str:
    """Fresh per-login OAuth 2.0 access token (separate from the Panel 08 API secret key)."""
    return f"tip_oauth_{secrets.token_hex(12)}"


def _mask_token(token) -> str:
    if not token:
        return ''
    return f"{token[:14]}••••••••{token[-4:]}"


def seed_initial_data():
    """Seeds initial T.I.P. CPE courses, competencies, telemetry, and DPA audit logs if empty."""
    dean = InstitutionalUser.objects.filter(email__iexact='dean.cit@tip.edu.ph').first()
    if (
        not Course.objects.exists()
        or not DPAAuditLog.objects.exists()
        or not ABETCriterion.objects.exists()
        or dean is None
        or not dean.password
        or not dean.has_usable_password()
    ):
        ensure_seed_data()


def _extract_bearer_token(request) -> str | None:
    auth_header = request.headers.get('Authorization', '').strip()
    if auth_header.lower().startswith('bearer '):
        return auth_header[7:].strip()
    api_key_header = request.headers.get('X-API-Key', '').strip()
    if api_key_header:
        return api_key_header
    return None


def _build_matrix_rows():
    courses = Course.objects.prefetch_related('outcomes').all()
    matrix_rows = []
    for course in courses:
        outcome_map = {o.so_code: o.proficiency for o in course.outcomes.all()}
        matrix_rows.append(
            {
                'course_code': course.course_code,
                'course_title': course.course_title,
                'cells': [
                    {'so_code': so, 'proficiency': outcome_map.get(so)}
                    for so in ('SO1', 'SO2', 'SO3', 'SO4')
                ],
            }
        )
    return courses, matrix_rows


# --- Dedicated Template Views (Overview + Panels 01 to 08) ---

@_empowered_login_required
def overview_board_view(request):
    seed_initial_data()
    _, matrix_rows = _build_matrix_rows()
    logs = DPAAuditLog.objects.order_by('-id')[:5]
    return render(
        request,
        'overview_board.html',
        {
            'active_tab': 'overview',
            'matrix_rows': matrix_rows,
            'logs': logs,
            'abet': build_abet_state(),
        },
    )


def panel1_login_view(request):
    seed_initial_data()
    # Visiting /login/ always places the user in an unauthenticated state
    # until they complete institutional sign-in.
    request.session.pop('empowered_authenticated', None)
    request.session.pop('empowered_user_email', None)
    config = MiddlewareConfig.load()
    user = (
        InstitutionalUser.objects.filter(email='dean.cit@tip.edu.ph').first()
        or InstitutionalUser.objects.order_by('id').first()
    )
    return render(
        request,
        'panel1_login.html',
        {
            'active_tab': 'p1',
            'sso_email': user.email if user and user.email else 'dean.cit@tip.edu.ph',
            'config': config,
        },
    )


@_empowered_login_required
def panel2_dashboard_view(request):
    seed_initial_data()
    metrics = compute_dashboard_metrics()
    return render(
        request,
        'panel2_dashboard.html',
        {
            'active_tab': 'p2',
            'kpis': metrics['kpis'],
            'telemetry': metrics['telemetry'],
        },
    )


@_empowered_login_required
def panel3_pipeline_view(request):
    seed_initial_data()
    metrics = compute_dashboard_metrics()
    latest_telemetry = SyncTelemetryLog.objects.order_by('-id').first()
    return render(
        request,
        'panel3_pipeline.html',
        {
            'active_tab': 'p3',
            'latency': latest_telemetry.latency_ms if latest_telemetry else 42,
            'throughput': float(latest_telemetry.throughput_pkts) if latest_telemetry else 1.8,
            'telemetry': metrics['telemetry'],
        },
    )


@_empowered_login_required
def panel4_matrix_view(request):
    seed_initial_data()
    courses, matrix_rows = _build_matrix_rows()
    return render(
        request,
        'panel4_matrix.html',
        {
            'active_tab': 'p4',
            'courses': courses,
            'matrix_rows': matrix_rows,
        },
    )


@_empowered_login_required
def panel5_competency_view(request):
    seed_initial_data()
    metrics = compute_dashboard_metrics()
    return render(
        request,
        'panel5_competency.html',
        {
            'active_tab': 'p5',
            'comp': metrics['competencies'],
            'radar': metrics['radar'],
        },
    )


@_empowered_login_required
def panel6_audit_view(request):
    seed_initial_data()
    logs = DPAAuditLog.objects.order_by('-id')[:12]
    return render(request, 'panel6_audit.html', {'active_tab': 'p6', 'logs': logs})


@_empowered_login_required
def panel7_abet_view(request):
    seed_initial_data()
    return render(
        request,
        'panel7_abet.html',
        {'active_tab': 'p7', 'abet': build_abet_state()},
    )


@_empowered_login_required
def abet_report_print_view(request):
    """
    Official printable ABET & CHED OBE Self-Study Report (browser Save-as-PDF).
    Pure-read GET: it never writes to the audit ledger. The seal hash is only displayed
    when it matches a real EXPORT audit row created via POST /api/v2/reports/abet-print-seal/.
    """
    seed_initial_data()
    metrics = compute_dashboard_metrics()
    _, matrix_rows = _build_matrix_rows()
    seal = request.GET.get('seal', '').strip()
    sealed = bool(seal) and DPAAuditLog.objects.filter(
        sha256_payload=seal, action__startswith='EXPORT'
    ).exists()
    return render(
        request,
        'abet_report_print.html',
        {
            'kpis': metrics['kpis'],
            'comp': metrics['competencies'],
            'abet': metrics['abet'],
            'matrix_rows': matrix_rows,
            'seal_hash': seal if sealed else '',
            'is_sealed': sealed,
            'generated_at': timezone.localtime(),
        },
    )


@_empowered_login_required
def panel8_config_view(request):
    seed_initial_data()
    config = MiddlewareConfig.load()
    webhook_url = request.build_absolute_uri('/api/v2/hooks/canvas-sync/')
    return render(
        request,
        'panel8_config.html',
        {
            'active_tab': 'p8',
            'config': config,
            'webhook_url': webhook_url,
        },
    )


def empowered_session_logout_view(request):
    """Clear the EmpowerED session and redirect to the login page."""
    request.session.flush()
    return redirect('panel1-login')


# --- REST API Middleware Views ---

class CanvasSyncWebhookAPIView(APIView):
    """
    Panel 03 & 08: Receives LTI 1.3 Rubric JSON from Canvas LMS,
    executes ETL mapping into EmpowerED SIS database, and logs SHA-256 audit hash.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        start_time = time.perf_counter()
        config = MiddlewareConfig.load()

        provided_token = _extract_bearer_token(request)
        if provided_token is not None and not secrets.compare_digest(
            provided_token, config.api_secret_key
        ):
            return Response(
                {'detail': 'Invalid OAuth 2.0 / API Bearer token.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = CanvasWebhookIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        raw_json = json.dumps(request.data, default=str, sort_keys=True)

        with transaction.atomic():
            course, _ = Course.objects.get_or_create(
                course_code=payload['course_code'],
                defaults={'course_title': 'Mapped Engineering Course'},
            )

            # Anonymize student ID for RA 10173 Data Privacy compliance
            anon_token = hashlib.sha256(
                payload['student_number'].encode('utf-8')
            ).hexdigest()
            scores = payload['scores']

            StudentCompetencyRecord.objects.create(
                course=course,
                student_token=anon_token,
                canvas_rubric_id=payload['canvas_rubric_id'],
                knowledge=scores.get('knowledge', Decimal('88.00')),
                skills=scores.get('skills', Decimal('76.00')),
                values=scores.get('values', Decimal('85.00')),
                capstone_readiness=scores.get('capstone', Decimal('72.00')),
                internship_hours=scores.get('internship', Decimal('94.00')),
            )

            elapsed_ms = max(14, int((time.perf_counter() - start_time) * 1000))
            throughput_val = Decimal(
                str(round(1.55 + ((len(raw_json) * 7) % 55) / 100.0, 2))
            )
            telemetry = SyncTelemetryLog.objects.create(
                latency_ms=elapsed_ms,
                throughput_pkts=throughput_val,
            )

            short_hash = DPAAuditLog.generate_hash(raw_json)
            audit_entry = DPAAuditLog.objects.create(
                sha256_payload=short_hash,
                action='SYNC · Canvas',
                privacy_verified=True,
            )

        return Response(
            {
                'status': 'LIVE - SYNCED',
                'latency_ms': elapsed_ms,
                'throughput_pkts': float(telemetry.throughput_pkts),
                'timestamp': audit_entry.timestamp.strftime('%H:%M:%S'),
                'sha256_payload': short_hash,
            },
            status=status.HTTP_201_CREATED,
        )


class DashboardStateAPIView(APIView):
    """
    Panels 02, 03, 04, 05, 06, & 08: Aggregates real-time OBE metrics, matrix mappings,
    competency averages, telemetry series, config state, and latest DPA encrypted audit logs.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        seed_initial_data()
        metrics = compute_dashboard_metrics()
        courses = CourseMatrixSerializer(
            Course.objects.prefetch_related('outcomes'), many=True
        ).data
        audits = DPAAuditLogSerializer(
            DPAAuditLog.objects.order_by('-id')[:8], many=True
        ).data
        config = MiddlewareConfig.load()
        user = InstitutionalUser.objects.order_by('-id').first()

        return Response(
            {
                'kpis': metrics['kpis'],
                'competencies': metrics['competencies'],
                'radar': metrics['radar'],
                'telemetry': metrics['telemetry'],
                'abet': metrics['abet'],
                'course_matrix': courses,
                'audit_logs': audits,
                'config': MiddlewareConfigSerializer(config).data,
                'oauth_token_masked': _mask_token(request.session.get('empowered_oauth_token')),
                'sso_user': {
                    'email': user.email if user else 'dean.cit@tip.edu.ph',
                    'role': user.role if user else 'DEAN',
                    'oauth_2fa_verified': user.oauth_2fa_verified if user else True,
                    'clearance_level': config.active_clearance_level,
                },
            }
        )


class InstitutionalSSOAPIView(APIView):
    """Panel 01: Simulated T.I.P. Microsoft OAuth 2.0 + 2FA institutional verification."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = InstitutionalSSOSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email', 'dean.cit@tip.edu.ph')
        config = MiddlewareConfig.load()

        with transaction.atomic():
            user, created_user = InstitutionalUser.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'role': 'DEAN',
                    'clearance_level': config.active_clearance_level,
                    'oauth_2fa_verified': True,
                },
            )
            user.oauth_2fa_verified = True
            if created_user or not user.password or not user.has_usable_password():
                user.set_password(DEFAULT_SSO_PASSWORD)
                user.save(update_fields=['oauth_2fa_verified', 'password'])
            else:
                user.save(update_fields=['oauth_2fa_verified'])

            oauth_token = _issue_oauth_token()
            token_digest = hashlib.sha256(oauth_token.encode('utf-8')).hexdigest()
            audit_entry, short_hash = _write_audit(
                {'email': email, 'provider': 'tip-microsoft-sso', 'token_sha256': token_digest},
                'AUTH · OAuth',
            )

        request.session['empowered_authenticated'] = True
        request.session['empowered_user_email'] = user.email
        request.session['empowered_oauth_token'] = oauth_token

        return Response(
            {
                'verified': True,
                'email': user.email,
                'role': user.role,
                'clearance_level': config.active_clearance_level,
                'oauth_token_masked': _mask_token(oauth_token),
                **_audit_payload(audit_entry, short_hash),
            }
        )


class EmpowerEdSessionLoginAPIView(APIView):
    """
    Panel 01: Validates institutional email + password credentials against
    InstitutionalUser, then sets the ``empowered_authenticated`` Django session
    flag and records an AUTH · OAuth audit entry.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        seed_initial_data()
        email = (request.data.get('email') or '').strip()
        password = request.data.get('password') or ''

        user = (
            InstitutionalUser.objects.filter(email__iexact=email, is_active=True).first()
            if email
            else None
        )
        if user is None or not password or not user.check_password(password):
            request.session.pop('empowered_authenticated', None)
            request.session.pop('empowered_user_email', None)
            request.session.pop('empowered_oauth_token', None)
            return Response(
                {
                    'verified': False,
                    'detail': 'Invalid institutional username or password. Access denied.',
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        config = MiddlewareConfig.load()

        # Fresh OAuth 2.0 bearer token for this login; only its SHA-256 digest enters the ledger.
        oauth_token = _issue_oauth_token()
        token_digest = hashlib.sha256(oauth_token.encode('utf-8')).hexdigest()
        audit_entry, short_hash = _write_audit(
            {'email': user.email, 'provider': 'tip-microsoft-sso', 'token_sha256': token_digest},
            'AUTH · OAuth',
        )

        with transaction.atomic():
            user.oauth_2fa_verified = True
            user.save(update_fields=['oauth_2fa_verified'])

        # Mark the Django session as authenticated
        request.session['empowered_authenticated'] = True
        request.session['empowered_user_email'] = user.email
        request.session['empowered_oauth_token'] = oauth_token

        return Response(
            {
                'verified': True,
                'email': user.email,
                'clearance_level': config.active_clearance_level,
                'oauth_token_masked': _mask_token(oauth_token),
                **_audit_payload(audit_entry, short_hash),
            }
        )


class CourseOutcomeMappingAPIView(APIView):
    """Panel 04: Persists I/E/R course outcome matrix updates with RBAC Level >= 2 enforcement."""
    authentication_classes = []
    permission_classes = []

    def patch(self, request):
        config = MiddlewareConfig.load()
        if config.active_clearance_level < 2:
            return Response(
                {
                    'detail': 'RBAC Restriction: Level 2 · Write or Level 3 · Admin clearance required to edit OBE course mappings.'
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MatrixCellUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            course, _ = Course.objects.get_or_create(
                course_code=data['course_code'],
                defaults={'course_title': 'Mapped Engineering Course'},
            )
            if data['proficiency'] == '-':
                # '-' clears the mapping: the cell returns to an unmapped em dash
                CourseOutcomeMapping.objects.filter(
                    course=course, so_code=data['so_code']
                ).delete()
            else:
                CourseOutcomeMapping.objects.update_or_create(
                    course=course,
                    so_code=data['so_code'],
                    defaults={'proficiency': data['proficiency']},
                )
            audit_entry, short_hash = _write_audit(
                {
                    'course_code': course.course_code,
                    'so_code': data['so_code'],
                    'proficiency': data['proficiency'],
                },
                'WRITE · SO Map',
            )

        metrics = compute_dashboard_metrics()
        return Response(
            {
                'course_code': course.course_code,
                'so_code': data['so_code'],
                'proficiency': data['proficiency'],
                'kpis': metrics['kpis'],
                **_audit_payload(audit_entry, short_hash),
            }
        )


class ABETCriterionToggleAPIView(APIView):
    """Panel 07: Persists an ABET Criterion lock/unlock (RBAC Level >= 2) and logs SHA-256."""
    authentication_classes = []
    permission_classes = []

    def patch(self, request):
        config = MiddlewareConfig.load()
        if config.active_clearance_level < 2:
            return Response(
                {
                    'detail': 'RBAC Restriction: Level 2 · Write or Level 3 · Admin clearance required to edit the ABET checklist.'
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        seed_initial_data()
        serializer = ABETCriterionToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        criterion = ABETCriterion.objects.filter(code=data['code']).first()
        if criterion is None:
            return Response(
                {'detail': f"Unknown ABET criterion '{data['code']}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            criterion.is_locked = data['locked']
            criterion.save(update_fields=['is_locked'])
            audit_entry, short_hash = _write_audit(
                {'criterion': criterion.code, 'locked': criterion.is_locked},
                'WRITE · ABET SSR',
            )

        metrics = compute_dashboard_metrics()
        return Response(
            {
                'code': criterion.code,
                'locked': criterion.is_locked,
                'abet': metrics['abet'],
                'kpis': metrics['kpis'],
                **_audit_payload(audit_entry, short_hash),
            }
        )


class ABETPrintSealAPIView(APIView):
    """Panel 07: Seals the printable SSR with an EXPORT audit row before the print view opens."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        seed_initial_data()
        abet_state = build_abet_state()
        audit_entry, short_hash = _write_audit(
            {'criteria': abet_state['criteria'], 'format': 'print-html'},
            'EXPORT · Print',
        )
        return Response(_audit_payload(audit_entry, short_hash), status=status.HTTP_201_CREATED)


class ABETReportExportAPIView(APIView):
    """Panel 07: Compiles checked ABET Criteria 1-7 into a downloadable SSR PDF."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        seed_initial_data()
        serializer = ABETReportExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        criteria = serializer.validated_data.get('criteria', [])

        raw_event = json.dumps(
            {'criteria': criteria, 'generated_at': timezone.now().isoformat()},
            default=str,
        )
        short_hash = DPAAuditLog.generate_hash(raw_event)
        audit_entry = DPAAuditLog.objects.create(
            sha256_payload=short_hash,
            action='EXPORT · PDF',
            privacy_verified=True,
        )

        pdf_bytes = build_abet_ssr_pdf(criteria=criteria, audit_hash=short_hash)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="TIP_EmpowerED_ABET_SSR_v2.pdf"'
        response['X-Audit-Timestamp'] = audit_entry.timestamp.strftime('%H:%M:%S')
        response['X-Audit-Hash'] = short_hash
        return response


class RotateAPIKeyAPIView(APIView):
    """Panel 08: Rotates the live API secret key (requires RBAC Level 3 · Admin)."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        config = MiddlewareConfig.load()
        if config.active_clearance_level < 3:
            return Response(
                {
                    'detail': 'RBAC Restriction: Level 3 · Admin clearance required to rotate API secret keys.'
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            new_key = f"tip_live_{secrets.token_hex(8)}"
            config.api_secret_key = new_key
            config.save(update_fields=['api_secret_key', 'updated_at'])

            raw_event = json.dumps(
                {'event': 'api_key_rotation', 'ts': timezone.now().isoformat()}
            )
            short_hash = DPAAuditLog.generate_hash(raw_event)
            audit_entry = DPAAuditLog.objects.create(
                sha256_payload=short_hash,
                action='AUTH · KeyRot',
                privacy_verified=True,
            )

        return Response(
            {
                'api_secret_key': new_key,
                'timestamp': audit_entry.timestamp.strftime('%H:%M:%S'),
                'sha256_payload': short_hash,
                'action': audit_entry.action,
            }
        )


class MiddlewareConfigAPIView(APIView):
    """Panel 08: Updates active RBAC clearance level (1-3) and performance alert toggles."""
    authentication_classes = []
    permission_classes = []

    def patch(self, request):
        config = MiddlewareConfig.load()
        target_clearance = request.data.get(
            'active_clearance_level', config.active_clearance_level
        )
        try:
            target_clearance = int(target_clearance)
        except (TypeError, ValueError):
            return Response(
                {'detail': 'Invalid clearance level.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        modifying_alerts = any(
            field in request.data
            for field in ('alert_high_latency', 'alert_sync_failure', 'alert_weekly_digest')
        )
        if modifying_alerts and target_clearance < 2:
            return Response(
                {
                    'detail': 'RBAC Restriction: Level 2 · Write or Level 3 · Admin clearance required to update alert settings.'
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        previous_clearance = config.active_clearance_level
        previous_alerts = {
            f: getattr(config, f)
            for f in ('alert_high_latency', 'alert_sync_failure', 'alert_weekly_digest')
        }

        serializer = MiddlewareConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        InstitutionalUser.objects.all().update(
            clearance_level=config.active_clearance_level
        )

        # Log only genuine state changes into the RA 10173 audit ledger
        audit = {}
        if config.active_clearance_level != previous_clearance:
            entry, short_hash = _write_audit(
                {
                    'event': 'rbac_clearance_change',
                    'from': previous_clearance,
                    'to': config.active_clearance_level,
                },
                'AUTH · RBAC',
            )
            audit = _audit_payload(entry, short_hash)
        else:
            changed_alerts = {
                f: getattr(config, f)
                for f, old in previous_alerts.items()
                if getattr(config, f) != old
            }
            if changed_alerts:
                entry, short_hash = _write_audit(
                    {'event': 'alert_toggle', 'changed': changed_alerts},
                    'WRITE · Alert',
                )
                audit = _audit_payload(entry, short_hash)

        return Response({**serializer.data, **audit})
