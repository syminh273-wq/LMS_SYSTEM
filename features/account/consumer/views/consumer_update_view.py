from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from ..serializers.consumer_serializer import ConsumerAccountUpdateSerializer, ConsumerAccountSerializer
from ..services.consumer_service import ConsumerService
import uuid
import os

class ConsumerUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user
        user_uid = user.uid
        
        # Handle avatar upload to R2
        if 'avatar' in request.FILES and request.FILES['avatar']:
            try:
                from core.storages.storage_service import storage_service
                
                avatar_file = request.FILES['avatar']
                file_extension = os.path.splitext(avatar_file.name)[1]
                # Ensure UID is string and format prefix correctly
                unique_filename = f"avatars/{str(user_uid)}{file_extension}"
                print(f"DEBUG: uploading {unique_filename}")
                
                # Try R2 first
                try:
                    result = storage_service.upload_fileobj(avatar_file, unique_filename, is_public=True)
                    if result['success']:
                        # Store only the object key (relative path)
                        data['avatar_url'] = result['object_key']
                        print(f"DEBUG: R2 upload success, key={result['object_key']}")
                except Exception as e:
                    # Fallback to local storage
                    print(f"R2 upload failed, falling back to local: {str(e)}")
                    
                    # Re-read from beginning for fallback
                    avatar_file.seek(0)
                    local_result = storage_service.save_local(avatar_file, unique_filename)
                    if local_result['success']:
                        data['avatar_url'] = local_result['url']
                    else:
                        return Response(
                            {"message": "Avatar upload failed", "error": local_result['message']},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            except Exception as e:
                return Response(
                    {"message": "Avatar upload failed", "error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Remove 'avatar' from data to prevent ConsumerSerializer/ConsumerUpdateSerializer from trying to process it again
        if 'avatar' in data:
            del data['avatar']
        
        serializer = ConsumerAccountUpdateSerializer(data=data, partial=True)
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
                    "data": ConsumerAccountSerializer(updated_user).data
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"message": "Update failed due to an internal error", "error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
