import hashlib
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def current_local_time():
    """Return current local wall-clock time (Asia/Manila) as datetime.time."""
    return timezone.localtime().time().replace(microsecond=0)


class InstitutionalUser(AbstractUser):
    CLEARANCE_CHOICES = [
        (1, 'Level 1 - Read'),
        (2, 'Level 2 - Write'),
        (3, 'Level 3 - Admin'),
    ]
    role = models.CharField(max_length=30, default='DEAN')
    clearance_level = models.IntegerField(choices=CLEARANCE_CHOICES, default=2)
    oauth_2fa_verified = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({self.role} · L{self.clearance_level})"


class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)  # e.g., CPE 311
    course_title = models.CharField(max_length=150)

    class Meta:
        ordering = ['course_code']

    def __str__(self):
        return f"{self.course_code} - {self.course_title}"


class CourseOutcomeMapping(models.Model):
    PROFICIENCY_CHOICES = [
        ('I', 'Introductory'),
        ('E', 'Enabling'),
        ('R', 'Reinforcing'),
    ]
    course = models.ForeignKey(Course, related_name='outcomes', on_delete=models.CASCADE)
    so_code = models.CharField(max_length=10)  # SO1, SO2, SO3, SO4
    proficiency = models.CharField(max_length=1, choices=PROFICIENCY_CHOICES)

    class Meta:
        unique_together = ('course', 'so_code')
        ordering = ['so_code']

    def __str__(self):
        return f"{self.course.course_code} · {self.so_code} ({self.proficiency})"


class StudentCompetencyRecord(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='competency_records')
    student_token = models.CharField(max_length=64)  # Anonymized SHA-256 student ID (RA 10173)
    canvas_rubric_id = models.CharField(max_length=50)
    knowledge = models.DecimalField(max_digits=5, decimal_places=2)
    skills = models.DecimalField(max_digits=5, decimal_places=2)
    values = models.DecimalField(max_digits=5, decimal_places=2)
    capstone_readiness = models.DecimalField(max_digits=5, decimal_places=2)
    internship_hours = models.DecimalField(max_digits=5, decimal_places=2)
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-synced_at', '-id']

    def __str__(self):
        return f"{self.course.course_code} · {self.canvas_rubric_id} ({self.student_token[:8]}…)"


class SyncTelemetryLog(models.Model):
    latency_ms = models.PositiveIntegerField(default=42)
    throughput_pkts = models.DecimalField(max_digits=6, decimal_places=2, default=1.80)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at', '-id']

    def __str__(self):
        return f"{self.latency_ms} ms | {self.throughput_pkts}k pkt/s"


class DPAAuditLog(models.Model):
    timestamp = models.TimeField(default=current_local_time, editable=False)
    sha256_payload = models.CharField(max_length=64, editable=False)
    action = models.CharField(max_length=30)  # e.g., SYNC · Canvas, READ · Grades
    privacy_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.action} ({self.sha256_payload})"

    @staticmethod
    def generate_hash(raw_payload: str) -> str:
        full_hash = hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()
        return f"{full_hash[:6]}…{full_hash[-6:]}"


class ABETCriterion(models.Model):
    """Persistent Panel 07 ABET Self-Study checklist (Criterion 1-7)."""
    code = models.CharField(max_length=20, unique=True)   # e.g., Criterion 1
    title = models.CharField(max_length=120)              # e.g., Students
    is_locked = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        state = 'LOCKED' if self.is_locked else 'OPEN'
        return f"{self.code} · {self.title} [{state}]"


class MiddlewareConfig(models.Model):
    """Singleton operational config backing Panel 08 alerts, secret key, and active RBAC clearance."""
    api_secret_key = models.CharField(max_length=64, default='tip_live_98a7bc65d4e3f210')
    alert_high_latency = models.BooleanField(default=True)
    alert_sync_failure = models.BooleanField(default=True)
    alert_weekly_digest = models.BooleanField(default=False)
    active_clearance_level = models.IntegerField(
        choices=InstitutionalUser.CLEARANCE_CHOICES,
        default=2,
    )
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls) -> 'MiddlewareConfig':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"EmpowerED Middleware Config (Clearance L{self.active_clearance_level})"

