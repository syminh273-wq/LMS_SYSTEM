from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import ConsumerScopeMixin
from features.payment.serializers import PaymentRequestSerializer
from features.payment.serializers.payment_response_serializer import PaymentInitiateResponseSerializer, PaymentResponseSerializer
from features.payment.services import PaymentService
from features.payment.repositories import PaymentRepository


class ConsumerPaymentViewSet(ConsumerScopeMixin, BaseModelViewSet):
    """Consumer payment history + initiate MoMo payment."""
    http_method_names = ['get', 'post']

    def get_queryset(self):
        return PaymentRepository().get_by_consumer(self.request.user.uid)

    def get_serializer_class(self):
        return PaymentResponseSerializer

    def list(self, request, *args, **kwargs):
        """GET /api/v1/consumer/payment/
        Query params: ?status=completed&resource_type=classroom&limit=50
        """
        payments = list(self.get_queryset())
        status_filter = (request.query_params.get('status') or '').strip().lower()
        if status_filter:
            payments = [p for p in payments if (p.status or '').lower() == status_filter]
        resource_type = (request.query_params.get('resource_type') or '').strip().lower()
        if resource_type:
            from features.payment.serializers.payment_response_serializer import decode_meta
            payments = [p for p in payments if (decode_meta(getattr(p, 'extra_data', '')).get('resource_type') or '').lower() == resource_type]
        try:
            limit = int(request.query_params.get('limit') or 50)
        except (TypeError, ValueError):
            limit = 50
        payments = payments[:max(1, min(limit, 200))]
        return Response(PaymentResponseSerializer(payments, many=True).data)

    @action(detail=False, methods=['get'], url_path=r'by-order/(?P<order_id>[^/.]+)')
    def find_by_order(self, request, order_id=None):
        """GET /api/v1/consumer/payment/by-order/{order_id}/ — lookup one payment by order id (scoped to caller)."""
        payment = PaymentRepository().get_by_order_id(order_id)
        if not payment or str(payment.consumer_id) != str(request.user.uid):
            return Response({'error': 'Không tìm thấy đơn hàng.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentResponseSerializer(payment).data)

    @action(detail=False, methods=['post'], url_path='create')
    def initiate(self, request):
        serializer = PaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = PaymentService().initiate(
            consumer_id=request.user.uid,
            amount=data['amount'],
            order_info=data['order_info'],
            resource_type=data['resource_type'],
            resource_id=str(data['resource_id']),
        )
        return Response(PaymentInitiateResponseSerializer(result).data, status=status.HTTP_201_CREATED)
