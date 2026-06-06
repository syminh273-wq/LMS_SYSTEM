from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from features.account.otp.serializers import ResetPasswordSerializer
from features.account.otp.services import OTPService


class ConsumerResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = OTPService().reset_password(
            reset_token=serializer.validated_data['reset_token'],
            new_password=serializer.validated_data['new_password'],
            user_type='consumer',
        )
        return Response(result, status=status.HTTP_200_OK)
