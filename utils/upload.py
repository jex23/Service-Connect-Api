import boto3
import uuid
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from botocore.exceptions import NoCredentialsError, ClientError

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_r2_client():
    """Initialize and return R2 client"""
    try:
        return boto3.client(
            's3',
            aws_access_key_id=current_app.config['R2_ACCESS_KEY'],
            aws_secret_access_key=current_app.config['R2_SECRET_KEY'],
            endpoint_url=current_app.config['R2_ENDPOINT'],
            region_name='auto'
        )
    except Exception as e:
        print(f"Error creating R2 client: {e}")
        return None

def generate_proper_filename(original_filename, prefix='', service_id=None):
    """
    Generate properly formatted filename with timestamp and UUID
    
    Args:
        original_filename: Original file name
        prefix: Optional prefix for the filename
        service_id: Optional service ID to include in filename
    
    Returns:
        str: Properly formatted filename
    """
    # Get file extension
    if '.' in original_filename:
        ext = original_filename.rsplit('.', 1)[1].lower()
    else:
        ext = 'jpg'  # default extension
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Generate unique ID
    unique_id = str(uuid.uuid4())[:8]
    
    # Build filename components
    filename_parts = []
    if prefix:
        filename_parts.append(prefix)
    if service_id:
        filename_parts.append(f'service_{service_id}')
    filename_parts.extend([timestamp, unique_id])
    
    return f"{'_'.join(filename_parts)}.{ext}"

def upload_file_to_r2(file, folder='uploads', prefix='', service_id=None):
    """
    Upload file to R2 storage with proper naming
    
    Args:
        file: File object from request
        folder: Folder name in bucket (default: 'uploads')
        prefix: Optional prefix for filename
        service_id: Optional service ID for filename
    
    Returns:
        dict: {'success': bool, 'url': str, 'error': str}
    """
    if not file or file.filename == '':
        return {'success': False, 'error': 'No file selected'}
    
    if not allowed_file(file.filename):
        return {'success': False, 'error': 'File type not allowed'}
    
    try:
        # Generate proper filename
        unique_filename = generate_proper_filename(file.filename, prefix, service_id)
        key = f"{folder}/{unique_filename}"
        
        # Get R2 client
        s3_client = get_r2_client()
        if not s3_client:
            return {'success': False, 'error': 'Could not connect to R2 storage'}
        
        # Upload file
        s3_client.upload_fileobj(
            file,
            current_app.config['R2_BUCKET_NAME'],
            key,
            ExtraArgs={'ACL': 'public-read'}
        )
        
        # Generate CDN URL with https for document folders
        if folder in ['user-documents', 'provider-documents', 'provider-service-photos']:
            cdn_url = f"https://cdn.jamesgalos.shop/{key}"
        else:
            cdn_url = f"cdn.jamesgalos.shop/{key}"
        
        return {
            'success': True,
            'url': cdn_url,
            'filename': unique_filename,
            'original_filename': secure_filename(file.filename)
        }
        
    except NoCredentialsError:
        return {'success': False, 'error': 'R2 credentials not found'}
    except ClientError as e:
        return {'success': False, 'error': f'Upload failed: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Upload error: {str(e)}'}

def upload_multiple_files_to_r2(files, folder='uploads', prefix='', service_id=None):
    """
    Upload multiple files to R2 storage with proper naming
    
    Args:
        files: List of file objects or dict of files
        folder: Folder name in bucket
        prefix: Optional prefix for filenames
        service_id: Optional service ID for filenames
    
    Returns:
        dict: Results for each file
    """
    results = {}
    
    # Handle both list and dict inputs
    if isinstance(files, dict):
        file_items = files.items()
    else:
        file_items = enumerate(files)
    
    for key, file in file_items:
        if file and file.filename != '':
            result = upload_file_to_r2(file, folder, prefix, service_id)
            results[key] = result
        else:
            results[key] = {'success': False, 'error': 'No file provided'}
    
    return results

def delete_file_from_r2(file_url):
    """
    Delete file from R2 storage using its URL
    
    Args:
        file_url: Full URL of the file in R2
    
    Returns:
        dict: {'success': bool, 'error': str}
    """
    try:
        # Extract key from URL
        bucket_name = current_app.config['R2_BUCKET_NAME']
        endpoint = current_app.config['R2_ENDPOINT']
        
        # Parse key from URL - handle both CDN and direct R2 URLs
        if "cdn.jamesgalos.shop/" in file_url:
            key = file_url.split("cdn.jamesgalos.shop/")[1]
        elif f"{endpoint}/{bucket_name}/" in file_url:
            key = file_url.split(f"{endpoint}/{bucket_name}/")[1]
        else:
            return {'success': False, 'error': 'Invalid file URL'}
        
        # Get R2 client
        s3_client = get_r2_client()
        if not s3_client:
            return {'success': False, 'error': 'Could not connect to R2 storage'}
        
        # Delete file
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=key
        )
        
        return {'success': True}
        
    except ClientError as e:
        return {'success': False, 'error': f'Delete failed: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Delete error: {str(e)}'}