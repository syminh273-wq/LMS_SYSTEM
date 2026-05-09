from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response
from ..serializers.consumer_serializer import UpdateSerializer, Serializer
from ..services.consumer_service import ConsumerService

class ConsumerUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = UpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"message": "Update failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # request.user is the Consumer instance if authenticated
            user = request.user
            updated_user = ConsumerService().repository.update(user, **serializer.validated_data)
            
            return Response(
                {
                    "message": "Profile updated successfully",
                    "data": Serializer(updated_user).data
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"message": "Update failed due to an internal error", "error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
