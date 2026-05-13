import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings
from decouple import config
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Cloudflare R2 Storage Service using boto3 S3-compatible API"""
    
    def __init__(self):
        self.account_id = config('R2_ACCOUNT_ID', default='')
        self.access_key_id = config('R2_ACCESS_KEY_ID', default='')
        self.secret_access_key = config('R2_SECRET_ACCESS_KEY', default='')
        
        # Two buckets for separation
        self.private_bucket = config('R2_BUCKET_NAME_PRIVATE', default='lms-system')
        self.public_bucket = config('R2_BUCKET_NAME_PUBLIC', default='lms-system-public')
        
        self.endpoint_url = config('R2_ENDPOINT_URL', default=f'https://{self.account_id}.r2.cloudflarestorage.com')
        
        self._s3_client = None
        self._initialized = False

    @property
    def public_domain(self):
        return config('R2_PUBLIC_DOMAIN', default='')

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._initialize_client()
        return self._s3_client

    @property
    def is_initialized(self):
        return self._initialized

    def _initialize_client(self):
        """Lazy initialization of the S3 client"""
        try:
            if not all([self.access_key_id, self.secret_access_key]):
                logger.warning("R2 storage credentials not properly configured")
            
            self._s3_client = boto3.client(
                service_name='s3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='auto'
            )
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self._initialized = False
            raise
    
    def get_public_url(self, object_key: str) -> str:
        """
        Generate a public URL for an object from the public bucket.
        """
        if not object_key:
            return ""
        
        # Debug
        pd = self.public_domain
        print(f"DEBUG: resolving {object_key}, public_domain='{pd}'")

        # If it's already a full URL or local media path
        if object_key.startswith('/media/') or object_key.startswith('http'):
            return object_key
            
        # R2 Public Access MUST use a Custom Domain or R2.dev Subdomain
        if self.public_domain:
            return f"{self.public_domain.rstrip('/')}/{object_key.lstrip('/')}"
            
        # IMPORTANT: R2 API endpoint (r2.cloudflarestorage.com) does NOT support 
        # anonymous public access. You MUST configure a Public Domain in R2 Settings.
        logger.warning(f"R2_PUBLIC_DOMAIN not set. Cannot generate public URL for {object_key}. Falling back to local if exists.")
        
        # Fallback to local media if the file exists there (useful for dev)
        local_path = os.path.join(settings.MEDIA_ROOT, object_key)
        if os.path.exists(local_path):
            return f"{settings.MEDIA_URL}{object_key}"

        # If all else fails, returning the key or a placeholder is better than a broken API link
        return object_key

    def upload_fileobj(self, file_obj, object_key: str, is_public: bool = True) -> Dict[str, Any]:
        """
        Upload a file-like object to R2 storage. Default to public bucket.
        """
        try:
            bucket = self.public_bucket if is_public else self.private_bucket
            
            extra_args = {}
            if is_public:
                # Ensure correct content type for images so browsers display them
                import mimetypes
                content_type, _ = mimetypes.guess_type(object_key)
                if content_type:
                    extra_args['ContentType'] = content_type
                # Note: R2 uses bucket-level/domain-level public access, 
                # but 'public-read' is a standard S3 hint.
                extra_args['ACL'] = 'public-read'

            self.s3_client.upload_fileobj(file_obj, bucket, object_key, ExtraArgs=extra_args)
            
            return {
                'success': True,
                'message': f'Successfully uploaded {object_key} to {bucket}',
                'object_key': object_key,
                'url': self.get_public_url(object_key) if is_public else object_key
            }
            
        except ClientError as e:
            logger.error(f"Upload error: {e}")
            return {
                'success': False,
                'message': f'Upload failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected upload error: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }
    
    def download_file(self, object_key: str, file_path: str, is_public: bool = True) -> Dict[str, Any]:
        """
        Download a file from R2 storage
        """
        try:
            bucket = self.public_bucket if is_public else self.private_bucket
            self.s3_client.download_file(bucket, object_key, file_path)
            
            return {
                'success': True,
                'message': f'Successfully downloaded {object_key} from {bucket} to {file_path}',
                'object_key': object_key,
                'file_path': file_path
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {
                    'success': False,
                    'message': f'Object not found: {object_key}'
                }
            logger.error(f"Download error: {e}")
            return {
                'success': False,
                'message': f'Download failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected download error: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }
    
    def get_object(self, object_key: str, is_public: bool = True) -> Dict[str, Any]:
        """
        Get object data from R2 storage
        """
        try:
            bucket = self.public_bucket if is_public else self.private_bucket
            response = self.s3_client.get_object(Bucket=bucket, Key=object_key)
            
            return {
                'success': True,
                'message': f'Successfully retrieved {object_key} from {bucket}',
                'object_key': object_key,
                'body': response['Body'],
                'content_type': response.get('ContentType', ''),
                'content_length': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {
                    'success': False,
                    'message': f'Object not found: {object_key}'
                }
            logger.error(f"Get object error: {e}")
            return {
                'success': False,
                'message': f'Get object failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected get object error: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }
    
    def list_objects(self, prefix: str = '', max_keys: int = 1000, is_public: bool = True) -> Dict[str, Any]:
        """
        List objects in R2 storage bucket
        """
        try:
            bucket = self.public_bucket if is_public else self.private_bucket
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    objects.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"'),
                        'url': self.get_public_url(obj['Key']) if is_public else obj['Key']
                    })
            
            return {
                'success': True,
                'message': f'Found {len(objects)} objects in {bucket}',
                'objects': objects,
                'count': len(objects),
                'is_truncated': response.get('IsTruncated', False),
                'next_continuation_token': response.get('NextContinuationToken')
            }
            
        except ClientError as e:
            logger.error(f"List objects error: {e}")
            return {
                'success': False,
                'message': f'List objects failed: {str(e)}',
                'objects': []
            }
        except Exception as e:
            logger.error(f"Unexpected list objects error: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'objects': []
            }
    
    def delete_object(self, object_key: str, is_public: bool = True) -> Dict[str, Any]:
        """
        Delete an object from R2 storage
        """
        try:
            bucket = self.public_bucket if is_public else self.private_bucket
            self.s3_client.delete_object(Bucket=bucket, Key=object_key)
            
            return {
                'success': True,
                'message': f'Successfully deleted {object_key} from {bucket}',
                'object_key': object_key
            }
            
        except ClientError as e:
            logger.error(f"Delete object error: {e}")
            return {
                'success': False,
                'message': f'Delete failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected delete error: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }
    
    def delete_objects(self, object_keys: List[str], is_public: bool = True) -> Dict[str, Any]:
        """
        Delete multiple objects from R2 storage
        """
        try:
            bucket = self.public_bucket if is_public else self.private_bucket
            delete_objects = [{'Key': key} for key in object_keys]
            response = self.s3_client.delete_objects(
                Bucket=bucket,
                Delete={'Objects': delete_objects}
            )
            
            deleted = response.get('Deleted', [])
            errors = response.get('Errors', [])
            
            return {
                'success': len(errors) == 0,
                'message': f'Deleted {len(deleted)} objects from {bucket}, {len(errors)} errors',
                'deleted': [{'key': obj['Key']} for obj in deleted],
                'errors': [{'key': obj['Key'], 'error': obj['Message']} for obj in errors]
            }
            
        except ClientError as e:
            logger.error(f"Delete objects error: {e}")
            return {
                'success': False,
                'message': f'Delete objects failed: {str(e)}',
                'deleted': [],
                'errors': []
            }
        except Exception as e:
            logger.error(f"Unexpected delete objects error: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'deleted': [],
                'errors': []
            }
    
    def check_connection(self, is_public: bool = True) -> Dict[str, Any]:
        """
        Check connection to R2 storage
        """
        try:
            bucket = self.public_bucket if is_public else self.private_bucket
            response = self.s3_client.list_buckets()
            buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
            
            return {
                'success': True,
                'message': f'Connection successful to {bucket}',
                'buckets': buckets,
                'bucket_exists': bucket in buckets
            }
            
        except NoCredentialsError:
            return {
                'success': False,
                'message': 'No credentials provided'
            }
        except ClientError as e:
            logger.error(f"Connection error: {e}")
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }

    def save_local(self, file_obj, object_key: str) -> Dict[str, Any]:
        """
        Fallback method to save file to local media directory
        """
        try:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            # Ensure the directory exists
            path = default_storage.save(object_key, ContentFile(file_obj.read()))
            url = f"{settings.MEDIA_URL}{path}"
            
            return {
                'success': True,
                'message': f'Successfully saved locally to {path}',
                'object_key': path,
                'url': url
            }
        except Exception as e:
            logger.error(f"Local save error: {e}")
            return {
                'success': False,
                'message': f'Local save failed: {str(e)}'
            }


# Global storage service instance
storage_service = StorageService()
