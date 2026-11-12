from rest_framework import serializers
from .models import (
    Course,
    CourseOutcomeMapping,
    DPAAuditLog,
    MiddlewareConfig,
    StudentCompetencyRecord,
    SyncTelemetryLog,
)


class CourseOutcomeMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOutcomeMapping
        fields = ['so_code', 'proficiency']


class CourseMatrixSerializer(serializers.ModelSerializer):
    outcomes = CourseOutcomeMappingSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['course_code', 'course_title', 'outcomes']


class DPAAuditLogSerializer(serializers.ModelSerializer):
    timestamp = serializers.TimeField(format='%H:%M:%S', read_only=True)

    class Meta:
        model = DPAAuditLog
        fields = ['timestamp', 'sha256_payload', 'action', 'privacy_verified']


class SyncTelemetryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncTelemetryLog
        fields = ['latency_ms', 'throughput_pkts', 'recorded_at']


class MiddlewareConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MiddlewareConfig
        fields = [
            'api_secret_key',
            'alert_high_latency',
            'alert_sync_failure',
            'alert_weekly_digest',
            'active_clearance_level',
        ]
        read_only_fields = ['api_secret_key']


class CanvasWebhookIngestSerializer(serializers.Serializer):
    course_code = serializers.CharField(max_length=20)
    canvas_rubric_id = serializers.CharField(max_length=50)
    student_number = serializers.CharField(max_length=50)
    scores = serializers.DictField(
        child=serializers.DecimalField(max_digits=5, decimal_places=2)
    )


class MatrixCellUpdateSerializer(serializers.Serializer):
    course_code = serializers.CharField(max_length=20)
    so_code = serializers.ChoiceField(choices=['SO1', 'SO2', 'SO3', 'SO4'])
    # '-' clears the mapping (cell shows as an em dash in the matrix)
    proficiency = serializers.ChoiceField(choices=['I', 'E', 'R', '-'])


class ABETCriterionToggleSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)
    locked = serializers.BooleanField()


class ABETCriterionInputSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=30)
    title = serializers.CharField(max_length=120)
    locked = serializers.BooleanField()


class ABETReportExportSerializer(serializers.Serializer):
    criteria = ABETCriterionInputSerializer(many=True, required=False)


class InstitutionalSSOSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, default='student.id@tip.edu.ph')

