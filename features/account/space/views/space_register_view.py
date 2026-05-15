from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from features.account.space.serializers import SpaceAccountCreateSerializer
from features.account.space.services.space_service import Service

class SpaceRegisterView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = SpaceAccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Service will handle password hashing and UID generation via BaseAuthService
        Service().register(serializer.validated_data)
        return Response(
            {"message": "Space registration successful"}, 
            status=status.HTTP_201_CREATED
        )
