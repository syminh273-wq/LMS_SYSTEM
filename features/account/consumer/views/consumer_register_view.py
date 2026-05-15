from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from features.account.consumer.serializers import ConsumerAccountCreateSerializer
from features.account.consumer.services.consumer_service import ConsumerService

class ConsumerRegisterView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ConsumerAccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ConsumerService().register(serializer.validated_data)
        return Response(
            {"message": "Consumer registration successful"}, 
            status=status.HTTP_201_CREATED
        )
