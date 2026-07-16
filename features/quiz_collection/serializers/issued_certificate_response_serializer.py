from rest_framework import serializers


class IssuedCertificateResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    student_id = serializers.UUIDField(read_only=True)
    certificate_id = serializers.UUIDField(read_only=True)
    collection_id = serializers.UUIDField(read_only=True)
    classroom_id = serializers.UUIDField(read_only=True)
    issued_by = serializers.UUIDField(read_only=True)
    issued_at = serializers.DateTimeField(read_only=True)
    pdf_url = serializers.CharField(allow_null=True, required=False)
    verification_code = serializers.CharField(read_only=True)
