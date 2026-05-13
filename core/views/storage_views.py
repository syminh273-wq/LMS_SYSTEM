import os
import tempfile
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from core.storages.storage_service import storage_service
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def upload_file(request: Request):
    """
    Upload a file to R2 storage
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'message': 'No file provided'
            }, status=400)
        
        file = request.FILES['file']
        object_key = request.POST.get('object_key', file.name)
        
        # Upload file using the storage service
        result = storage_service.upload_fileobj(file, object_key)
        
        if result['success']:
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Upload file error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def get_file(request: Request, object_key: str):
    """
    Get a file from R2 storage
    """
    try:
        result = storage_service.get_object(object_key)
        
        if not result['success']:
            return JsonResponse(result, status=404)
        
        # Return file as HttpResponse
        response = HttpResponse(
            result['body'].read(),
            content_type=result.get('content_type', 'application/octet-stream')
        )
        
        # Set content disposition for download
        response['Content-Disposition'] = f'attachment; filename="{object_key}"'
        response['Content-Length'] = result.get('content_length', 0)
        
        return response
        
    except Exception as e:
        logger.error(f"Get file error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Get file failed: {str(e)}'
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def list_files(request: Request):
    """
    List files in R2 storage
    """
    try:
        prefix = request.GET.get('prefix', '')
        max_keys = int(request.GET.get('max_keys', 1000))
        
        result = storage_service.list_objects(prefix=prefix, max_keys=max_keys)
        
        if result['success']:
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': f'Invalid parameter: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.error(f"List files error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'List files failed: {str(e)}'
        }, status=500)


@csrf_exempt
@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_file(request: Request, object_key: str):
    """
    Delete a file from R2 storage
    """
    try:
        result = storage_service.delete_object(object_key)
        
        if result['success']:
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Delete file error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Delete file failed: {str(e)}'
        }, status=500)


@csrf_exempt
@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_files(request: Request):
    """
    Delete multiple files from R2 storage
    """
    try:
        object_keys = request.data.get('object_keys', [])
        
        if not object_keys:
            return JsonResponse({
                'success': False,
                'message': 'No object keys provided'
            }, status=400)
        
        result = storage_service.delete_objects(object_keys)
        
        return JsonResponse(result, status=200)
            
    except Exception as e:
        logger.error(f"Delete files error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Delete files failed: {str(e)}'
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def check_storage_connection(request: Request):
    """
    Check connection to R2 storage
    """
    try:
        result = storage_service.check_connection()
        
        if result['success']:
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Check storage connection error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Connection check failed: {str(e)}'
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def upload_local_file(request: Request):
    """
    Upload a local file to R2 storage (for testing/sync purposes)
    """
    try:
        file_path = request.data.get('file_path')
        object_key = request.data.get('object_key')
        
        if not file_path:
            return JsonResponse({
                'success': False,
                'message': 'File path is required'
            }, status=400)
        
        if not os.path.exists(file_path):
            return JsonResponse({
                'success': False,
                'message': f'File not found: {file_path}'
            }, status=404)
        
        result = storage_service.upload_file(file_path, object_key)
        
        if result['success']:
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Upload local file error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Upload local file failed: {str(e)}'
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def download_file(request: Request, object_key: str):
    """
    Download a file from R2 storage to local temp directory
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        result = storage_service.download_file(object_key, temp_path)
        
        if result['success']:
            # Read the file and return as response
            with open(temp_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{object_key}"'
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return response
        else:
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Download file error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Download file failed: {str(e)}'
        }, status=500)
