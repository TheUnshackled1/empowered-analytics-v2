from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Course,
    CourseOutcomeMapping,
    DPAAuditLog,
    InstitutionalUser,
    MiddlewareConfig,
    StudentCompetencyRecord,
    SyncTelemetryLog,
)


@admin.register(InstitutionalUser)
class InstitutionalUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('EmpowerED RBAC & SSO', {'fields': ('role', 'clearance_level', 'oauth_2fa_verified')}),
    )
    list_display = ('username', 'email', 'role', 'clearance_level', 'oauth_2fa_verified', 'is_staff')


class CourseOutcomeMappingInline(admin.TabularInline):
    model = CourseOutcomeMapping
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'course_title')
    search_fields = ('course_code', 'course_title')
    inlines = [CourseOutcomeMappingInline]


@admin.register(StudentCompetencyRecord)
class StudentCompetencyRecordAdmin(admin.ModelAdmin):
    list_display = (
        'course',
        'canvas_rubric_id',
        'knowledge',
        'skills',
        'values',
        'capstone_readiness',
        'internship_hours',
        'synced_at',
    )
    list_filter = ('course',)
    readonly_fields = ('student_token', 'synced_at')


@admin.register(SyncTelemetryLog)
class SyncTelemetryLogAdmin(admin.ModelAdmin):
    list_display = ('latency_ms', 'throughput_pkts', 'recorded_at')
    readonly_fields = ('recorded_at',)


@admin.register(DPAAuditLog)
class DPAAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'sha256_payload', 'action', 'privacy_verified', 'created_at')
    readonly_fields = ('timestamp', 'sha256_payload', 'action', 'privacy_verified', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MiddlewareConfig)
class MiddlewareConfigAdmin(admin.ModelAdmin):
    list_display = (
        'active_clearance_level',
        'alert_high_latency',
        'alert_sync_failure',
        'alert_weekly_digest',
        'updated_at',
    )

