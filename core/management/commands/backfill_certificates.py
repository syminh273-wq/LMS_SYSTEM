from django.core.management.base import BaseCommand, CommandError

from features.course.classroom.repositories.classroom_member_repository import (
    ClassroomMemberRepository,
)
from features.quiz_collection.services import CertificateIssuanceService


class Command(BaseCommand):
    help = (
        "Backfill IssuedCertificate rows for students who have completed a "
        "QuizCollection with 100% but never received the cert (e.g. due to "
        "the historical silent-exception bug in the submit endpoint).\n\n"
        "Usage:\n"
        "  python manage.py backfill_certificates --student=<uid>\n"
        "  python manage.py backfill_certificates --classroom=<uid>\n"
        "  python manage.py backfill_certificates --all\n"
    )

    def add_arguments(self, parser):
        parser.add_argument("--student", type=str, default=None, help="Student uid to backfill for.")
        parser.add_argument(
            "--classroom", type=str, default=None, help="Classroom uid to scope backfill to."
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Backfill every approved student/classroom pair. Use with care.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute what would be issued without writing to the DB.",
        )

    def handle(self, *args, **options):
        if not options["student"] and not options["classroom"] and not options["all"]:
            raise CommandError("Provide one of --student=<uid>, --classroom=<uid>, or --all.")

        service = CertificateIssuanceService()
        member_repo = ClassroomMemberRepository()
        pairs = self._collect_pairs(member_repo, options)

        if not pairs:
            self.stdout.write(self.style.WARNING("No (student, classroom) pairs to process."))
            return

        self.stdout.write(
            self.style.NOTICE(
                f"Processing {len(pairs)} (student, classroom) pair(s){' [DRY RUN]' if options['dry_run'] else ''}…"
            )
        )

        total_issued = 0
        total_skipped = 0
        total_failed = 0

        for student_id, classroom_id in pairs:
            try:
                before = self._count_certs(service, student_id, classroom_id)
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  ! could not read certs for student={student_id} classroom={classroom_id}: {exc}")
                )
                total_failed += 1
                continue

            if options["dry_run"]:
                self.stdout.write(
                    f"  · student={student_id} classroom={classroom_id} (existing certs: {before})"
                )
                continue

            try:
                issued = service.check_and_issue(
                    student_id=student_id,
                    classroom_id=classroom_id,
                    just_submitted_quiz_id=None,
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ! backfill failed for student={student_id} classroom={classroom_id}: {exc}"
                    )
                )
                total_failed += 1
                continue

            delta = len(issued)
            if delta:
                total_issued += delta
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ student={student_id} classroom={classroom_id}: "
                        f"issued {delta} new certificate(s)."
                    )
                )
            else:
                total_skipped += 1
                self.stdout.write(
                    f"  · student={student_id} classroom={classroom_id}: nothing to issue "
                    f"(existing: {before})."
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Backfill complete."))
        self.stdout.write(f"  Issued:   {total_issued}")
        self.stdout.write(f"  Skipped:  {total_skipped}")
        self.stdout.write(f"  Failed:   {total_failed}")

    def _collect_pairs(self, member_repo, options):
        if options["student"]:
            student_id = options["student"]
            memberships = list(member_repo.get_by_member(student_id))
            if not memberships:
                self.stdout.write(
                    self.style.WARNING(
                        f"Student {student_id} has no classroom memberships."
                    )
                )
                return []
            if options["classroom"]:
                memberships = [m for m in memberships if str(m.classroom_uid) == str(options["classroom"])]
            return [(student_id, str(m.classroom_uid)) for m in memberships]

        if options["classroom"]:
            classroom_id = options["classroom"]
            members = list(member_repo.get_members(classroom_id))
            if not members:
                self.stdout.write(
                    self.style.WARNING(
                        f"Classroom {classroom_id} has no approved members."
                    )
                )
                return []
            return [(str(m.member_id), classroom_id) for m in members]

        pairs = []
        try:
            from features.course.classroom.models.classroom_member import ClassroomMember
            rows = ClassroomMember.objects.filter(is_deleted=False, status='approved').limit(10000)
            for m in rows:
                pairs.append((str(m.member_id), str(m.classroom_uid)))
        except Exception as exc:
            raise CommandError(f"Could not enumerate members: {exc}")
        return pairs

    def _count_certs(self, service, student_id, classroom_id) -> int:
        from features.quiz_collection.repositories import IssuedCertificateRepository
        repo = IssuedCertificateRepository()
        certs = repo.get_by_student(student_id)
        return sum(1 for c in certs if str(c.classroom_id) == str(classroom_id))
