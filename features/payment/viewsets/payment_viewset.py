from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.views.api.base_viewset import BaseModelViewSet
from features.payment.serializers import PaymentRequestSerializer
from features.payment.serializers.payment_response_serializer import PaymentInitiateResponseSerializer, PaymentResponseSerializer
from features.payment.services import PaymentService
from features.payment.repositories import PaymentRepository


class PaymentViewSet(BaseModelViewSet):
    http_method_names = ['get', 'post']

    def get_queryset(self):
        return PaymentRepository().get_by_consumer(self.request.user.uid)

    def get_serializer_class(self):
        return PaymentResponseSerializer

    def list(self, request, *args, **kwargs):
        payments = list(self.get_queryset())
        return Response(PaymentResponseSerializer(payments, many=True).data)

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
