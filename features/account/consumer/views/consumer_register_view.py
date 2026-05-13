from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from features.account.consumer.serializers.consumer_serializer import RegisterSerializer
from features.account.consumer.services.consumer_service import ConsumerService

class ConsumerRegisterView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Registration failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ConsumerService().register(serializer.validated_data)
            return Response(
                {"message": "Registration successful"}, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"message": "Registration failed due to an internal error", "error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
