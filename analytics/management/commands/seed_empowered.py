from django.core.management.base import BaseCommand
from analytics.services import ensure_seed_data


class Command(BaseCommand):
    help = (
        'Pre-loads T.I.P. EmpowerED v2.0 CPE 311-616 course outcome matrix, '
        'anonymized student competencies, telemetry logs, and SHA-256 DPA audit logs.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear existing analytics records and restore baseline T.I.P. prototype seed data.',
        )

    def handle(self, *args, **options):
        summary = ensure_seed_data(reset=options['reset'])
        self.stdout.write(
            self.style.SUCCESS(
                f"EmpowerED v2.0 database seeded: {summary.get('courses', 0)} courses, "
                f"{summary.get('mappings', 0)} SO mappings, "
                f"{summary.get('competency_records', 0)} competency records, "
                f"{summary.get('telemetry_logs', 0)} telemetry logs, "
                f"{summary.get('audit_logs', 0)} DPA audit entries."
            )
        )

