from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from features.account.space.serializers import SpaceAccountLoginSerializer
from features.account.space.services.space_service import Service

class SpaceLoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = SpaceAccountLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = Service().authenticate(
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        if user:
            refresh = RefreshToken.for_user(user)
            refresh['user_type'] = 'space'
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "message": "Login successful"
            }, status=status.HTTP_200_OK)
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
