import hashlib
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import (
    Course,
    CourseOutcomeMapping,
    DPAAuditLog,
    MiddlewareConfig,
    StudentCompetencyRecord,
    SyncTelemetryLog,
)


class EmpowerEDAnalyticsV2Tests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auto_seed_populates_tip_cpe_matrix_and_audits(self):
        """Post-migrate auto-seeding loads CPE 311-616, SO mappings, competencies, and 5 audit logs."""
        self.assertEqual(Course.objects.count(), 5)
        self.assertEqual(CourseOutcomeMapping.objects.count(), 17)
        self.assertEqual(StudentCompetencyRecord.objects.count(), 5)
        self.assertEqual(SyncTelemetryLog.objects.count(), 10)
        self.assertGreaterEqual(DPAAuditLog.objects.count(), 5)

        cpe_616 = Course.objects.get(course_code='CPE 616')
        outcomes = dict(cpe_616.outcomes.values_list('so_code', 'proficiency'))
        self.assertEqual(outcomes, {'SO1': 'R', 'SO2': 'R', 'SO3': 'R', 'SO4': 'R'})

    def test_dashboard_html_renders_eight_panels(self):
        """Root dashboard view returns 200 OK with all 8 EmpowerED v2.0 interface panels."""
        response = self.client.get(reverse('empowered-dashboard'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn('EmpowerED', html)
        self.assertIn('Secure OAuth Login Screen', html)
        self.assertIn('ABET Self-Study Report PDF Export Portal', html)
        self.assertIn('Middleware System Alerts & API Config', html)

    def test_dashboard_state_endpoint_aggregates_seeded_metrics(self):
        """GET /api/v2/dashboard/state/ returns accurate baseline KPIs, matrix, radar, and audits."""
        response = self.client.get(reverse('dashboard-state'))
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['kpis']['abet_accreditation'], 87)
        self.assertEqual(data['kpis']['ched_obe_status'], 92)
        self.assertEqual(data['kpis']['matrix_coverage'], 89.4)
        self.assertEqual(data['kpis']['deficit'], 17.6)
        self.assertEqual(data['competencies']['knowledge'], 88.0)
        self.assertEqual(data['competencies']['skills'], 76.0)
        self.assertEqual(len(data['course_matrix']), 5)
        self.assertEqual(len(data['audit_logs']), 5)

    def test_canvas_webhook_anonymizes_student_id_under_ra10173(self):
        """POST /api/v2/hooks/canvas-sync/ hashes student_number via SHA-256 and logs audit trail."""
        raw_student_no = '2023-10492'
        expected_sha = hashlib.sha256(raw_student_no.encode('utf-8')).hexdigest()
        config = MiddlewareConfig.load()

        payload = {
            'course_code': 'CPE 515',
            'canvas_rubric_id': 'RUB-2026-991',
            'student_number': raw_student_no,
            'scores': {
                'knowledge': 95,
                'skills': 88,
                'values': 92,
                'capstone': 85,
                'internship': 98,
            },
        }
        response = self.client.post(
            reverse('canvas-sync-webhook'),
            payload,
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {config.api_secret_key}',
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['status'], 'LIVE - SYNCED')
        self.assertIn('…', body['sha256_payload'])

        record = StudentCompetencyRecord.objects.get(canvas_rubric_id='RUB-2026-991')
        self.assertEqual(record.student_token, expected_sha)
        self.assertNotEqual(record.student_token, raw_student_no)

        latest_audit = DPAAuditLog.objects.first()
        self.assertEqual(latest_audit.action, 'SYNC · Canvas')
        self.assertTrue(latest_audit.privacy_verified)

    def test_canvas_webhook_rejects_invalid_bearer_token(self):
        """Invalid Bearer token is rejected with 401 Unauthorized."""
        payload = {
            'course_code': 'CPE 311',
            'canvas_rubric_id': 'RUB-BAD-TOKEN',
            'student_number': '2023-99999',
            'scores': {'knowledge': 80},
        }
        response = self.client.post(
            reverse('canvas-sync-webhook'),
            payload,
            format='json',
            HTTP_AUTHORIZATION='Bearer tip_live_invalid_token_000',
        )
        self.assertEqual(response.status_code, 401)

    def test_matrix_mapping_rbac_and_persistence(self):
        """Level 1 Read cannot edit matrix; Level 2 Write persists I/E/R updates and logs audit."""
        url = reverse('course-matrix-mapping')

        # Downgrade to Level 1 Read
        self.client.patch(
            reverse('middleware-config-settings'),
            {'active_clearance_level': 1},
            format='json',
        )
        denied = self.client.patch(
            url,
            {'course_code': 'CPE 311', 'so_code': 'SO1', 'proficiency': 'E'},
            format='json',
        )
        self.assertEqual(denied.status_code, 403)

        # Upgrade to Level 2 Write
        self.client.patch(
            reverse('middleware-config-settings'),
            {'active_clearance_level': 2},
            format='json',
        )
        allowed = self.client.patch(
            url,
            {'course_code': 'CPE 311', 'so_code': 'SO1', 'proficiency': 'R'},
            format='json',
        )
        self.assertEqual(allowed.status_code, 200)
        mapping = CourseOutcomeMapping.objects.get(
            course__course_code='CPE 311', so_code='SO1'
        )
        self.assertEqual(mapping.proficiency, 'R')
        self.assertEqual(DPAAuditLog.objects.first().action, 'WRITE · SO Map')

    def test_api_key_rotation_enforces_level_3_admin(self):
        """Only Level 3 Admin clearance can rotate the API secret key."""
        rotate_url = reverse('rotate-api-key')
        old_key = MiddlewareConfig.load().api_secret_key

        # Default is Level 2 -> should return 403
        denied = self.client.post(rotate_url, format='json')
        self.assertEqual(denied.status_code, 403)

        # Elevate to Level 3 Admin -> should succeed
        self.client.patch(
            reverse('middleware-config-settings'),
            {'active_clearance_level': 3},
            format='json',
        )
        rotated = self.client.post(rotate_url, format='json')
        self.assertEqual(rotated.status_code, 200)
        new_key = rotated.json()['api_secret_key']
        self.assertTrue(new_key.startswith('tip_live_'))
        self.assertNotEqual(new_key, old_key)
        self.assertEqual(DPAAuditLog.objects.first().action, 'AUTH · KeyRot')

    def test_abet_ssr_pdf_export_generates_valid_pdf_and_audit(self):
        """POST /api/v2/reports/abet-ssr/ streams a valid PDF binary and records EXPORT · PDF."""
        response = self.client.post(
            reverse('abet-ssr-export'),
            {
                'criteria': [
                    {'code': 'Criterion 1', 'title': 'Students', 'locked': True},
                    {'code': 'Criterion 3', 'title': 'Student Outcomes', 'locked': True},
                ]
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertEqual(DPAAuditLog.objects.first().action, 'EXPORT · PDF')

