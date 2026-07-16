from uuid import UUID

from features.quiz_collection.models import IssuedCertificate


class IssuedCertificateRepository:

    def get_by_student(self, student_id):
        s_id = UUID(str(student_id)) if not isinstance(student_id, UUID) else student_id
        return list(IssuedCertificate.objects.filter(student_id=s_id, is_deleted=False))

    def find(self, uid):
        u_id = UUID(str(uid)) if not isinstance(uid, UUID) else uid
        cert = IssuedCertificate.objects.filter(uid=u_id, is_deleted=False).first()
        if not cert:
            raise IssuedCertificate.DoesNotExist('IssuedCertificate not found.')
        return cert

    def find_for_collection_classroom_student(self, collection_id, classroom_id, student_id):
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        r_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id
        s_id = UUID(str(student_id)) if not isinstance(student_id, UUID) else student_id
        return IssuedCertificate.objects.filter(
            collection_id=c_id, classroom_id=r_id, student_id=s_id, is_deleted=False
        ).allow_filtering().first()

    def exists(self, collection_id, classroom_id, student_id) -> bool:
        return self.find_for_collection_classroom_student(
            collection_id, classroom_id, student_id
        ) is not None

    def create(self, student_id, certificate_id, collection_id, classroom_id,
               issued_by, verification_code, pdf_url=None) -> IssuedCertificate:
        s_id = UUID(str(student_id)) if not isinstance(student_id, UUID) else student_id
        c_id = UUID(str(certificate_id)) if not isinstance(certificate_id, UUID) else certificate_id
        col_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        r_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id
        ib = UUID(str(issued_by)) if not isinstance(issued_by, UUID) else issued_by

        return IssuedCertificate.objects.create(
            student_id=s_id,
            certificate_id=c_id,
            collection_id=col_id,
            classroom_id=r_id,
            issued_by=ib,
            verification_code=verification_code,
            pdf_url=pdf_url,
        )
