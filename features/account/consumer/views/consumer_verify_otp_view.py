from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from features.account.otp.serializers import VerifyOTPSerializer
from features.account.otp.services import OTPService


class ConsumerVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = OTPService().verify_otp(
            email=serializer.validated_data['email'],
            user_type='consumer',
            otp_code=serializer.validated_data['otp_code'],
        )
        return Response(result, status=status.HTTP_200_OK)
