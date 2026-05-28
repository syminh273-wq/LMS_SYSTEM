import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from features.payment.services import PaymentService

logger = logging.getLogger(__name__)


class MoMoIPNView(APIView):
    """
    MoMo calls this endpoint after the consumer completes (or fails) payment.
    Must always return 200 quickly; MoMo will retry on non-200.
    No JWT auth — MoMo doesn't send a token, signature is verified internally.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            PaymentService().handle_ipn(request.data)
        except PermissionError as e:
            logger.warning(f'[IPN] Signature mismatch: {e}')
        except Exception as e:
            logger.error(f'[IPN] Unexpected error: {e}')
        return Response({"message": "ok"})
