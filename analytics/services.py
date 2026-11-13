from datetime import time as dt_time
from decimal import Decimal
import hashlib
from io import BytesIO
import warnings

from django.db import OperationalError, ProgrammingError, transaction
from django.db.models import Avg
from django.utils import timezone

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


SEED_ABET_CRITERIA = [
    ('Criterion 1', 'Students', True),
    ('Criterion 2', 'Program Educational Objectives', True),
    ('Criterion 3', 'Student Outcomes', True),
    ('Criterion 4', 'Continuous Improvement', True),
    ('Criterion 5', 'Curriculum', False),
    ('Criterion 6', 'Faculty', True),
    ('Criterion 7', 'Facilities', False),
]
# Seed baseline: 5 of 7 criteria locked -> KPI baseline (ABET 87%) is unchanged at seed time.
ABET_BASELINE_LOCKED = 5


SEED_COURSES = [
    ('CPE 311', 'Logic Circuits', {'SO1': 'I', 'SO2': 'I', 'SO3': 'I'}),
    ('CPE 412', 'Embedded Systems', {'SO1': 'E', 'SO2': 'I', 'SO3': 'E'}),
    ('CPE 512', 'Computer Networks', {'SO1': 'E', 'SO2': 'E', 'SO4': 'I'}),
    ('CPE 515', 'Software Design', {'SO1': 'R', 'SO2': 'E', 'SO3': 'E', 'SO4': 'E'}),
    ('CPE 616', 'Capstone Design', {'SO1': 'R', 'SO2': 'R', 'SO3': 'R', 'SO4': 'R'}),
]

SEED_COMPETENCIES = [
    ('CPE 311', '2023-10101', 'RUB-2026-311', 86, 72, 82, 68, 92),
    ('CPE 412', '2023-10204', 'RUB-2026-412', 87, 74, 84, 70, 93),
    ('CPE 512', '2023-10318', 'RUB-2026-512', 88, 76, 85, 72, 94),
    ('CPE 515', '2023-10429', 'RUB-2026-515', 89, 78, 86, 74, 95),
    ('CPE 616', '2023-10588', 'RUB-2026-616', 90, 80, 88, 76, 96),
]

SEED_TELEMETRY = [
    (52, Decimal('0.99')),
    (46, Decimal('0.72')),
    (48, Decimal('1.44')),
    (39, Decimal('1.26')),
    (44, Decimal('1.08')),
    (36, Decimal('1.71')),
    (41, Decimal('1.35')),
    (43, Decimal('1.17')),
    (38, Decimal('1.53')),
    (33, Decimal('1.80')),
]

SEED_AUDITS = [
    (dt_time(9, 41, 7), 'a3f9c2…7e41b8', 'READ · Grades'),
    (dt_time(9, 41, 22), '9d04e1…c829a0', 'SYNC · Canvas'),
    (dt_time(9, 42, 5), '6b81f0…3312d4', 'WRITE · SO Map'),
    (dt_time(9, 43, 19), 'f42c77…1098e5', 'EXPORT · PDF'),
    (dt_time(9, 44, 2), 'c15a89…4401b2', 'AUTH · OAuth'),
]

DEFAULT_SSO_PASSWORD = 'TIP@EmpowerED2026'
SEED_SSO_USERS = (
    ('dean.cit@tip.edu.ph', 'EmpowerED', 'Dean', 'DEAN'),
    ('student.id@tip.edu.ph', 'EmpowerED', 'Student', 'DEAN'),
)


def ensure_seed_data(reset: bool = False) -> dict:
    """
    Idempotently populate T.I.P. EmpowerED v2.0 courses, SO mappings,
    anonymized student competencies, telemetry logs, config, and DPA audit logs.
    """
    try:
        with transaction.atomic():
            if reset:
                CourseOutcomeMapping.objects.all().delete()
                StudentCompetencyRecord.objects.all().delete()
                Course.objects.all().delete()
                SyncTelemetryLog.objects.all().delete()
                DPAAuditLog.objects.all().delete()
                MiddlewareConfig.objects.all().delete()
                ABETCriterion.objects.all().delete()

            MiddlewareConfig.load()

            if ABETCriterion.objects.count() == 0:
                for idx, (code, title, locked) in enumerate(SEED_ABET_CRITERIA, start=1):
                    ABETCriterion.objects.create(
                        code=code, title=title, is_locked=locked, sort_order=idx
                    )

            seeded_emails = [u[0] for u in SEED_SSO_USERS]
            InstitutionalUser.objects.filter(password='').exclude(email__in=seeded_emails).delete()

            for sso_email, first_name, last_name, role in SEED_SSO_USERS:
                user, created_user = InstitutionalUser.objects.get_or_create(
                    username=sso_email,
                    defaults={
                        'email': sso_email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'role': role,
                        'clearance_level': 2,
                        'oauth_2fa_verified': True,
                    },
                )
                if created_user or not user.password or not user.has_usable_password():
                    user.set_password(DEFAULT_SSO_PASSWORD)
                    user.save(update_fields=['password'])

            courses_by_code = {}
            if Course.objects.count() == 0:
                for code, title, outcomes in SEED_COURSES:
                    course = Course.objects.create(course_code=code, course_title=title)
                    courses_by_code[code] = course
                    for so_code, prof in outcomes.items():
                        CourseOutcomeMapping.objects.create(
                            course=course,
                            so_code=so_code,
                            proficiency=prof,
                        )
            else:
                for course in Course.objects.all():
                    courses_by_code[course.course_code] = course

            if StudentCompetencyRecord.objects.count() == 0:
                for code, student_no, rubric_id, know, skill, val, cap, intern in SEED_COMPETENCIES:
                    course = courses_by_code.get(code) or Course.objects.first()
                    if course:
                        anon_token = hashlib.sha256(student_no.encode('utf-8')).hexdigest()
                        StudentCompetencyRecord.objects.create(
                            course=course,
                            student_token=anon_token,
                            canvas_rubric_id=rubric_id,
                            knowledge=Decimal(str(know)),
                            skills=Decimal(str(skill)),
                            values=Decimal(str(val)),
                            capstone_readiness=Decimal(str(cap)),
                            internship_hours=Decimal(str(intern)),
                        )

            if SyncTelemetryLog.objects.count() == 0:
                for latency, throughput in SEED_TELEMETRY:
                    SyncTelemetryLog.objects.create(
                        latency_ms=latency,
                        throughput_pkts=throughput,
                    )

            if DPAAuditLog.objects.count() == 0:
                for ts, digest, action in SEED_AUDITS:
                    DPAAuditLog.objects.create(
                        timestamp=ts,
                        sha256_payload=digest,
                        action=action,
                        privacy_verified=True,
                    )

            return {
                'courses': Course.objects.count(),
                'mappings': CourseOutcomeMapping.objects.count(),
                'competency_records': StudentCompetencyRecord.objects.count(),
                'telemetry_logs': SyncTelemetryLog.objects.count(),
                'audit_logs': DPAAuditLog.objects.count(),
            }
    except (OperationalError, ProgrammingError):
        # Tables may not be created yet before initial migrate completes
        return {}


def build_abet_state() -> dict:
    """Persistent Panel 07 ABET checklist state used by every panel and the printable SSR."""
    rows = list(ABETCriterion.objects.all())
    total = len(rows)
    locked = sum(1 for r in rows if r.is_locked)
    return {
        'criteria': [
            {'code': r.code, 'title': r.title, 'locked': r.is_locked} for r in rows
        ],
        'locked_count': locked,
        'total_count': total,
        'ssr_pct': int(round((locked / total) * 100)) if total else 0,
    }


def compute_dashboard_metrics() -> dict:
    """Calculate live OBE KPIs, 5-bar competencies, 6-axis radar scores, and telemetry series."""
    agg = StudentCompetencyRecord.objects.aggregate(
        knowledge=Avg('knowledge'),
        skills=Avg('skills'),
        values=Avg('values'),
        capstone=Avg('capstone_readiness'),
        internship=Avg('internship_hours'),
    )

    knowledge = float(agg['knowledge'] if agg['knowledge'] is not None else 88.0)
    skills = float(agg['skills'] if agg['skills'] is not None else 76.0)
    values = float(agg['values'] if agg['values'] is not None else 85.0)
    capstone = float(agg['capstone'] if agg['capstone'] is not None else 72.0)
    internship = float(agg['internship'] if agg['internship'] is not None else 94.0)

    competencies = {
        'knowledge': round(knowledge, 1),
        'skills': round(skills, 1),
        'values': round(values, 1),
        'capstone': round(capstone, 1),
        'internship': round(internship, 1),
    }

    # 6-axis ABET Student Competency Radar derived from aggregated OBE records
    radar = {
        'knowledge': round(knowledge, 1),
        'problem_solving': round((knowledge * 0.55) + (skills * 0.45), 1),
        'design': round((skills * 0.55) + (capstone * 0.45), 1),
        'communication': round((values * 0.50) + (internship * 0.50), 1),
        'ethics': round(values, 1),
        'teamwork': round((values * 0.45) + (internship * 0.55), 1),
    }

    course_count = max(1, Course.objects.count())
    max_cells = course_count * 4
    mappings = list(CourseOutcomeMapping.objects.all())
    mapped_cells = len(mappings)
    weight_map = {'I': 1, 'E': 2, 'R': 3}
    proficiency_sum = sum(weight_map.get(m.proficiency, 1) for m in mappings)

    overall_comp = (knowledge + skills + values + capstone + internship) / 5.0
    abet_state = build_abet_state()
    # Each criterion locked above/below the seeded baseline moves ABET accreditation by +/- 2 pts.
    abet_checklist_delta = (
        (abet_state['locked_count'] - ABET_BASELINE_LOCKED) * 2.0
        if abet_state['total_count']
        else 0.0
    )
    matrix_coverage = round(
        min(99.9, max(0.0, 72.4 + (mapped_cells / max_cells) * 20.0 + (proficiency_sum - 34) * 0.2)),
        1,
    )
    abet_pct = int(round(min(
        99.0,
        max(50.0, overall_comp + 4.0 + (proficiency_sum - 34) * 0.3 + abet_checklist_delta),
    )))
    ched_pct = int(round(min(99.0, max(50.0, overall_comp + 9.0 + (mapped_cells - 17) * 0.5))))
    deficit = round(
        max(0.0, 100.0 - overall_comp + 0.6 - (proficiency_sum - 34) * 0.15),
        1,
    )

    recent_telemetry = list(SyncTelemetryLog.objects.order_by('-id')[:10])
    recent_telemetry.reverse()
    if recent_telemetry:
        latency_series = [t.latency_ms for t in recent_telemetry]
        throughput_series = [float(t.throughput_pkts) for t in recent_telemetry]
        latency_avg = int(round(sum(latency_series) / len(latency_series)))
        throughput_latest = round(throughput_series[-1], 2)
    else:
        latency_series = [42] * 10
        throughput_series = [1.80] * 10
        latency_avg = 42
        throughput_latest = 1.80

    return {
        'kpis': {
            'abet_accreditation': abet_pct,
            'ched_obe_status': ched_pct,
            'matrix_coverage': matrix_coverage,
            'deficit': deficit,
        },
        'competencies': competencies,
        'radar': radar,
        'abet': abet_state,
        'telemetry': {
            'latency_avg_ms': latency_avg,
            'throughput_pkts': throughput_latest,
            'latency_series': latency_series,
            'throughput_series': throughput_series,
            'total_synced_records': StudentCompetencyRecord.objects.count(),
        },
    }


def _ascii_safe(text: str) -> str:
    """Convert Unicode punctuation into Latin-1 safe text for core Helvetica PDF rendering."""
    return (
        str(text)
        .replace('…', '...')
        .replace('·', '|')
        .replace('—', '-')
        .replace('–', '-')
        .replace('✓', 'OK')
        .encode('latin-1', errors='replace')
        .decode('latin-1')
    )


def build_abet_ssr_pdf(criteria: list[dict], audit_hash: str) -> bytes:
    """Compile a downloadable T.I.P. EmpowerED ABET Self-Study Report (SSR) PDF."""
    metrics = compute_dashboard_metrics()
    kpis = metrics['kpis']
    comp = metrics['competencies']
    courses = Course.objects.prefetch_related('outcomes').all()

    # Persistent DB checklist is the source of truth; client payload is only a fallback.
    db_criteria = build_abet_state()['criteria']
    if db_criteria:
        criteria_rows = [
            {'code': c['code'], 'title': c['title'], 'locked': c['locked']} for c in db_criteria
        ]
    else:
        default_criteria = [
            {'code': code, 'title': title, 'locked': locked}
            for code, title, locked in SEED_ABET_CRITERIA
        ]
        criteria_rows = criteria if criteria else default_criteria
    locked_count = sum(1 for c in criteria_rows if c.get('locked'))
    readiness_pct = int(round((locked_count / max(1, len(criteria_rows))) * 100))

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        from fpdf import FPDF

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header Banner
    pdf.set_fill_color(11, 17, 30)
    pdf.rect(10, 10, 190, 26, style='F')
    pdf.set_xy(15, 14)
    pdf.set_text_color(245, 158, 11)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 7, 'TECHNOLOGICAL INSTITUTE OF THE PHILIPPINES (T.I.P.)', new_x='LMARGIN', new_y='NEXT')
    pdf.set_x(15)
    pdf.set_text_color(248, 250, 252)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 6, 'EmpowerED Analytics Module v2.0 | ABET Self-Study Report (SSR)', new_x='LMARGIN', new_y='NEXT')
    pdf.set_x(15)
    pdf.set_text_color(148, 163, 184)
    pdf.set_font('Helvetica', '', 8)
    now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S %Z')
    pdf.cell(
        0,
        5,
        _ascii_safe(f'Generated: {now_str}  |  RA 10173 DPA SHA-256 Seal: {audit_hash}'),
        new_x='LMARGIN',
        new_y='NEXT',
    )

    pdf.ln(8)
    pdf.set_text_color(15, 23, 42)

    # Section 1: Institutional KPIs
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, '1. Institutional OBE & Accreditation KPI Summary', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 7.8)
    pdf.set_fill_color(241, 245, 249)
    kpi_items = [
        ('ABET Accreditation', f"{kpis['abet_accreditation']}%"),
        ('CHED OBE Status', f"{kpis['ched_obe_status']}%"),
        ('Matrix Coverage', f"{kpis['matrix_coverage']}%"),
        ('Attainment Deficit', f"{kpis['deficit']}%"),
        ('SSR Readiness', f"{readiness_pct}% ({locked_count}/{len(criteria_rows)})"),
    ]
    for label, val in kpi_items:
        pdf.cell(38, 7, _ascii_safe(f'{label}: {val}'), border=1, fill=True, align='C')
    pdf.ln(11)

    # Section 2: ABET Criteria Checklist
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, '2. ABET General Criteria Verification Status', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(35, 7, 'Criterion', border=1, fill=True)
    pdf.cell(115, 7, 'Description', border=1, fill=True)
    pdf.cell(40, 7, 'SSR Lock Status', border=1, fill=True, align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(15, 23, 42)
    for row in criteria_rows:
        status_txt = 'LOCKED (VERIFIED)' if row.get('locked') else 'OPEN (IN REVIEW)'
        pdf.cell(35, 6.5, _ascii_safe(row.get('code', '')), border=1)
        pdf.cell(115, 6.5, _ascii_safe(row.get('title', '')), border=1)
        pdf.cell(40, 6.5, status_txt, border=1, align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(6)

    # Section 3: Curriculum OBE Course Mapping Matrix
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, '3. Curriculum Outcomes-Based Course Mapping Matrix (I / E / R)', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(30, 7, 'Course', border=1, fill=True)
    pdf.cell(80, 7, 'Course Title', border=1, fill=True)
    for so in ('SO1', 'SO2', 'SO3', 'SO4'):
        pdf.cell(20, 7, so, border=1, fill=True, align='C')
    pdf.ln(7)

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(15, 23, 42)
    for course in courses:
        outcome_map = {o.so_code: o.proficiency for o in course.outcomes.all()}
        pdf.cell(30, 6.5, _ascii_safe(course.course_code), border=1)
        pdf.cell(80, 6.5, _ascii_safe(course.course_title), border=1)
        for so in ('SO1', 'SO2', 'SO3', 'SO4'):
            pdf.cell(20, 6.5, outcome_map.get(so, '-'), border=1, align='C')
        pdf.ln(6.5)

    pdf.ln(6)

    # Section 4: Aggregated Student Competency Attainment
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, '4. Aggregated Student Competency Attainment (Target >= 80%)', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 9)
    comp_rows = [
        ('Knowledge', comp['knowledge']),
        ('Skills', comp['skills']),
        ('Values', comp['values']),
        ('Capstone Readiness', comp['capstone']),
        ('Internship Hours', comp['internship']),
    ]
    for name, score in comp_rows:
        remark = 'TARGET MET' if score >= 80.0 else 'CONTINUOUS IMPROVEMENT'
        pdf.cell(65, 6.5, name, border=1)
        pdf.cell(45, 6.5, f'{score:.1f}%', border=1, align='C')
        pdf.cell(80, 6.5, remark, border=1, align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(6)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(
        0,
        4.5,
        _ascii_safe(
            'Compliance Notice: All student-level Canvas LMS LTI 1.3 rubric submissions included in this '
            'aggregation were anonymized using SHA-256 tokenization prior to storage in compliance with '
            'Republic Act No. 10173 (Data Privacy Act of 2012).'
        ),
    )

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()

