import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from features.payment.services import PaymentService

logger = logging.getLogger(__name__)


class MoMoIPNView(APIView):
    """
    Handle MoMo's payment result callback. Always returns 200 quickly (MoMo retries on non-200);
    no JWT auth since MoMo doesn't send a token — signature is verified internally.
    @return: {"message": "ok"}
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
