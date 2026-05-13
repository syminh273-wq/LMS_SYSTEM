from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from features.account.consumer.serializers.consumer_serializer import RegisterSerializer
from features.account.consumer.services.consumer_service import ConsumerService
import uuid
import os

class ConsumerRegisterView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        user_uid = uuid.uuid4()
        
        # Handle avatar upload to R2
        avatar_url = ''
        if 'avatar' in request.FILES and request.FILES['avatar']:
            try:
                from core.storages.storage_service import storage_service

                avatar_file = request.FILES['avatar']
                file_extension = os.path.splitext(avatar_file.name)[1]
                unique_filename = f"avatars/{user_uid}{file_extension}"

                # Try R2 first
                try:
                    result = storage_service.upload_fileobj(avatar_file, unique_filename, is_public=True)
                    if result['success']:
                        # Store only the object key (relative path) in the database
                        avatar_url = result['object_key']
                    else:
                        raise Exception(result.get('message', 'R2 upload failed'))
                except Exception as e:
                    # Fallback to local storage if R2 fails or throws Access Denied
                    print(f"R2 upload failed, falling back to local: {str(e)}")

                    # Re-read from beginning for fallback
                    avatar_file.seek(0)
                    local_result = storage_service.save_local(avatar_file, unique_filename)
                    if local_result['success']:
                        # For local files, we store the full relative path /media/...
                        avatar_url = local_result['url']
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
        
        # Remove 'avatar' from data to prevent RegisterSerializer from trying to process it again
        # since we've already handled it manually.
        if 'avatar' in data:
            del data['avatar']
            
        # Set avatar_url and uid in data
        if avatar_url:
            data['avatar_url'] = avatar_url
        data['uid'] = user_uid
        
        serializer = RegisterSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {"message": "Registration failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Pass uid from data to register
            reg_data = serializer.validated_data
            reg_data['uid'] = user_uid
            if avatar_url:
                reg_data['avatar_url'] = avatar_url
                
            ConsumerService().register(reg_data)
            return Response(
                {"message": "Registration successful"}, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"message": "Registration failed due to an internal error", "error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
