from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from features.account.otp.serializers import ForgotPasswordSerializer
from features.account.otp.services import OTPService


class ConsumerForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = OTPService().request_otp(
            email=serializer.validated_data['email'],
            user_type='consumer',
        )
        return Response(result, status=status.HTTP_200_OK)
