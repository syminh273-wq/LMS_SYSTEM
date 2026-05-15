from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from features.account.consumer.serializers.consumer_serializer import ConsumerAccountLoginSerializer
from features.account.consumer.services.consumer_service import ConsumerService

class ConsumerLoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ConsumerAccountLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = ConsumerService().authenticate(
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        if user:
            refresh = RefreshToken.for_user(user)
            refresh['user_type'] = 'consumer'
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "message": "Login successful"
            }, status=status.HTTP_200_OK)
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
