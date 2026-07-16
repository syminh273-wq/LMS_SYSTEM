from rest_framework import serializers


class IssuedCertificateResponseSerializer(serializers.Serializer):
    """
    Enriched, frontend-friendly IssuedCertificate payload.

    The serializer is intentionally tolerant: it accepts a plain dict (already
    enriched by CertificateIssuanceService.enrich_issued_certificate) or an
    IssuedCertificate model. When given a model, only the raw UUID fields are
    populated — the service is responsible for joining related entities.
    """

    uid = serializers.CharField(read_only=True)
    student_id = serializers.CharField(read_only=True)
    certificate_id = serializers.CharField(read_only=True)
    collection_id = serializers.CharField(read_only=True)
    classroom_id = serializers.CharField(read_only=True)
    issued_by = serializers.CharField(read_only=True, allow_null=True, required=False)
    issued_at = serializers.CharField(read_only=True, allow_null=True, required=False)
    issued_at_display = serializers.CharField(read_only=True, allow_blank=True, required=False)
    pdf_url = serializers.CharField(read_only=True, allow_null=True, allow_blank=True, required=False)
    verification_code = serializers.CharField(read_only=True)

    # Resolved fields
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True, required=False)
    template_url = serializers.CharField(read_only=True, allow_null=True, allow_blank=True, required=False)

    collection_title = serializers.CharField(read_only=True, allow_blank=True, required=False)
    collection_description = serializers.CharField(read_only=True, allow_blank=True, required=False)

    student_name = serializers.CharField(read_only=True, allow_blank=True, required=False)
    student_pid = serializers.CharField(read_only=True, allow_blank=True, required=False)
    student_avatar_url = serializers.CharField(read_only=True, allow_blank=True, required=False)

    classroom_name = serializers.CharField(read_only=True, allow_blank=True, required=False)
