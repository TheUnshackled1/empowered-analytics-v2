import hashlib
from django.contrib.staticfiles import finders
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

    def test_all_multipage_routes_and_overview_board_render_cleanly(self):
        """Login hides module-nav; all 9 protected routes render base.html navigation once authenticated."""
        login_res = self.client.get(reverse('panel1-login'))
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.context['active_tab'], 'p1')
        login_html = login_res.content.decode('utf-8')
        self.assertIn('Secure OAuth Login Screen', login_html)
        self.assertNotIn('class="module-nav"', login_html)
        self.assertNotIn('Analytics Dashboard', login_html)

        # Authenticate the test session for protected routes
        self.client.post(reverse('session-login'), {'email': 'dean.cit@tip.edu.ph'}, format='json')

        expected_routes = [
            ('home', 'p2', 'Administrative Analytics Dashboard'),
            ('overview-board', 'overview', 'Middleware System Alerts'),
            ('panel2-dashboard', 'p2', 'Administrative Analytics Dashboard'),
            ('panel3-pipeline', 'p3', 'Live API Middleware Sync Pipeline'),
            ('panel4-matrix', 'p4', 'Curriculum Outcomes-Based Course Mapping Matrix'),
            ('panel5-competency', 'p5', 'Student Competency Radar Chart'),
            ('panel6-audit', 'p6', 'DPA Encrypted Audit Log Table'),
            ('panel7-abet', 'p7', 'ABET Self-Study Report PDF Export Portal'),
            ('panel8-config', 'p8', 'Middleware System Alerts'),
        ]
        for url_name, expected_tab, expected_heading in expected_routes:
            with self.subTest(route=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['active_tab'], expected_tab)
                html = response.content.decode('utf-8')
                self.assertIn('app-body', html)
                self.assertIn('module-nav', html)
                self.assertIn('nav-icon', html)
                self.assertIn('page-transition-loader', html)
                self.assertIn('page-progress-bar', html)
                self.assertNotIn('class="nav-num"', html)
                self.assertNotIn('nav-section-lbl', html)
                self.assertNotIn('8-Panel Master Board', html)
                self.assertIn(expected_heading, html)

    def test_static_css_and_javascript_files_exist_and_are_linked_in_templates(self):
        """Every HTML template has a dedicated CSS file in static/css/ and JS file in static/javascript/."""
        # Authenticate the test session first
        self.client.post(reverse('session-login'), {'email': 'dean.cit@tip.edu.ph'}, format='json')

        template_bases = [
            'base',
            'overview_board',
            'panel1_login',
            'panel2_dashboard',
            'panel3_pipeline',
            'panel4_matrix',
            'panel5_competency',
            'panel6_audit',
            'panel7_abet',
            'panel8_config',
        ]
        for name in template_bases:
            with self.subTest(static_asset=name):
                css_path = finders.find(f'css/{name}.css')
                js_path = finders.find(f'javascript/{name}.js')
                self.assertIsNotNone(css_path, f'Missing static/css/{name}.css')
                self.assertIsNotNone(js_path, f'Missing static/javascript/{name}.js')

        route_asset_pairs = [
            ('overview-board', 'overview_board'),
            ('panel2-dashboard', 'panel2_dashboard'),
            ('panel3-pipeline', 'panel3_pipeline'),
            ('panel4-matrix', 'panel4_matrix'),
            ('panel5-competency', 'panel5_competency'),
            ('panel6-audit', 'panel6_audit'),
            ('panel7-abet', 'panel7_abet'),
            ('panel8-config', 'panel8_config'),
            ('panel1-login', 'panel1_login'),
        ]
        for url_name, asset_name in route_asset_pairs:
            with self.subTest(route_assets=url_name):
                response = self.client.get(reverse(url_name))
                html = response.content.decode('utf-8')
                self.assertIn('/static/css/base.css', html)
                self.assertIn('/static/javascript/base.js', html)
                self.assertIn(f'/static/css/{asset_name}.css', html)
                self.assertIn(f'/static/javascript/{asset_name}.js', html)
                self.assertNotIn('<style>', html)

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
        self.assertGreaterEqual(len(data['audit_logs']), 5)

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

        denied = self.client.post(rotate_url, format='json')
        self.assertEqual(denied.status_code, 403)

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

    # ------------------------------------------------------------------
    # Authentication guard tests
    # ------------------------------------------------------------------

    def test_protected_routes_redirect_unauthenticated_to_login(self):
        """All panel routes redirect to /login/?next=<path> when session is not set, and /login/ hides module-nav."""
        from django.test import Client
        unauth_client = Client()
        login_page = unauth_client.get(reverse('panel1-login'))
        self.assertEqual(login_page.status_code, 200)
        login_html = login_page.content.decode('utf-8')
        self.assertNotIn('class="module-nav"', login_html)
        self.assertNotIn('8-Panel Master Board', login_html)

        protected = [
            'home',
            'overview-board',
            'panel2-dashboard',
            'panel3-pipeline',
            'panel4-matrix',
            'panel5-competency',
            'panel6-audit',
            'panel7-abet',
            'panel8-config',
        ]
        for name in protected:
            url = reverse(name)
            with self.subTest(route=name):
                fresh_client = Client()
                response = fresh_client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login/', response['Location'])

    def test_session_login_and_protected_access(self):
        """After POST /api/v2/auth/session-login/ the session allows access to protected panels."""
        login_res = self.client.post(
            reverse('session-login'),
            {'email': 'dean.cit@tip.edu.ph'},
            format='json',
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.json()['verified'])

        # Session cookie is now set — dashboard must return 200
        dashboard = self.client.get(reverse('panel2-dashboard'))
        self.assertEqual(dashboard.status_code, 200)

    def test_logout_clears_session(self):
        """GET /logout/ flushes the session and redirects to /login/; protected panels block again."""
        # Log in first
        self.client.post(
            reverse('session-login'),
            {'email': 'dean.cit@tip.edu.ph'},
            format='json',
        )
        # Confirm access
        self.assertEqual(self.client.get(reverse('panel2-dashboard')).status_code, 200)

        # Log out
        out = self.client.get(reverse('empowered-logout'))
        self.assertRedirects(out, reverse('panel1-login'), fetch_redirect_response=False)

        # Protected panel must redirect again
        blocked = self.client.get(reverse('panel2-dashboard'))
        self.assertEqual(blocked.status_code, 302)
        self.assertIn('/login/', blocked['Location'])
