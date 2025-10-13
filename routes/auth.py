from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import OperationalError
from werkzeug.datastructures import FileStorage
from utils.upload import upload_file_to_r2, upload_multiple_files_to_r2
import re

try:
    from models import db, User, Provider, ServiceCategory, ProviderCategoryMembership, ProviderService, ProviderServicePhoto, UserServiceCategory, ProviderServiceSchedule
    DB_AVAILABLE = True
except Exception as e:
    print(f"Database models not available: {e}")
    DB_AVAILABLE = False

auth_ns = Namespace('auth', description='Authentication operations')

# API Models for documentation
user_register_model = auth_ns.model('UserRegister', {
    'full_name': fields.String(required=True, description='Full name of the user'),
    'email': fields.String(required=True, description='Email address'),
    'address': fields.String(required=True, description='User address'),
    'password': fields.String(required=True, description='Password'),
    'id_front': fields.String(description='Front ID document URL/path (optional)'),
    'id_back': fields.String(description='Back ID document URL/path (optional)')
})

provider_register_model = auth_ns.model('ProviderRegister', {
    'business_name': fields.String(description='Business name (optional)'),
    'full_name': fields.String(required=True, description='Full name of the provider'),
    'email': fields.String(required=True, description='Email address'),
    'contact_number': fields.String(description='Contact phone number (optional)'),
    'address': fields.String(required=True, description='Provider address'),
    'password': fields.String(required=True, description='Password'),
    'bir_id_front': fields.String(description='BIR ID front document URL/path (optional)'),
    'bir_id_back': fields.String(description='BIR ID back document URL/path (optional)'),
    'business_permit': fields.String(description='Business permit document URL/path (optional)'),
    'image_logo': fields.String(description='Business logo image URL/path (optional)'),
    'about': fields.String(description='About the provider (optional)')
})

login_model = auth_ns.model('Login', {
    'email': fields.String(required=True, description='Email address'),
    'password': fields.String(required=True, description='Password')
})

# Response models
user_response_model = auth_ns.model('UserResponse', {
    'id': fields.Integer(description='User ID'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email address'),
    'address': fields.String(description='Address'),
    'id_front': fields.String(description='Front ID document URL'),
    'id_back': fields.String(description='Back ID document URL'),
    'user_type': fields.String(description='User type', enum=['user'])
})

provider_response_model = auth_ns.model('ProviderResponse', {
    'id': fields.Integer(description='Provider ID'),
    'business_name': fields.String(description='Business name (optional)'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email address'),
    'contact_number': fields.String(description='Contact phone number'),
    'address': fields.String(description='Complete address'),
    'bir_id_front': fields.String(description='BIR ID front document URL'),
    'bir_id_back': fields.String(description='BIR ID back document URL'),
    'business_permit': fields.String(description='Business permit document URL'),
    'image_logo': fields.String(description='Business logo image URL'),
    'about': fields.String(description='About the provider/business'),
    'is_active': fields.Boolean(description='Provider account status'),
    'user_type': fields.String(description='User type', enum=['provider'])
})

register_success_user_model = auth_ns.model('RegisterSuccessUser', {
    'message': fields.String(description='Success message', example='User registered successfully'),
    'access_token': fields.String(description='JWT access token for immediate login'),
    'user': fields.Nested(user_response_model)
})

register_success_provider_model = auth_ns.model('RegisterSuccessProvider', {
    'message': fields.String(description='Success message', example='Provider registered successfully'),
    'access_token': fields.String(description='JWT access token for immediate login'),
    'provider': fields.Nested(provider_response_model)
})

login_success_user_model = auth_ns.model('LoginSuccessUser', {
    'message': fields.String(description='Success message', example='Login successful'),
    'access_token': fields.String(description='JWT access token'),
    'user': fields.Nested(user_response_model)
})

login_success_provider_model = auth_ns.model('LoginSuccessProvider', {
    'message': fields.String(description='Success message', example='Login successful'),
    'access_token': fields.String(description='JWT access token'),
    'provider': fields.Nested(provider_response_model)
})

error_model = auth_ns.model('Error', {
    'error': fields.String(description='Error message')
})

provider_category_register_model = auth_ns.model('ProviderCategoryRegister', {
    'provider_id': fields.Integer(required=True, description='Provider ID'),
    'category_ids': fields.List(fields.Integer, required=True, description='List of category IDs to register for')
})

provider_category_response_model = auth_ns.model('ProviderCategoryResponse', {
    'message': fields.String(description='Success message'),
    'provider_id': fields.Integer(description='Provider ID'),
    'registered_categories': fields.List(fields.Raw, description='List of registered categories with details')
})

provider_service_register_model = auth_ns.model('ProviderServiceRegister', {
    'provider_id': fields.Integer(required=True, description='Provider ID'),
    'category_id': fields.Integer(required=True, description='Service category ID'),
    'service_title': fields.String(required=True, description='Service title (max 150 characters)'),
    'service_description': fields.String(description='Service description (optional)'),
    'price_decimal': fields.Float(description='Service price (optional)'),
    'duration_minutes': fields.Integer(description='Service duration in minutes (optional)'),
    'is_active': fields.Boolean(description='Service active status (defaults to True)')
})

provider_service_response_model = auth_ns.model('ProviderServiceResponse', {
    'message': fields.String(description='Success message'),
    'service': fields.Raw(description='Created service details')
})

provider_service_photo_response_model = auth_ns.model('ProviderServicePhotoResponse', {
    'message': fields.String(description='Success message'),
    'photos': fields.List(fields.Raw, description='List of uploaded photo details')
})

user_service_register_model = auth_ns.model('UserServiceRegister', {
    'user_id': fields.Integer(required=True, description='User ID'),
    'category_id': fields.Integer(required=True, description='Service category ID'),
    'service_title': fields.String(required=True, description='Service title (max 150 characters)'),
    'service_description': fields.String(description='Service description (optional)'),
    'price_decimal': fields.Float(description='Service price (optional)'),
    'is_active': fields.Boolean(description='Service active status (defaults to True)')
})

user_service_response_model = auth_ns.model('UserServiceResponse', {
    'message': fields.String(description='Success message'),
    'service': fields.Raw(description='Created user service details')
})

service_category_model = auth_ns.model('ServiceCategory', {
    'id': fields.Integer(description='Category ID'),
    'category_name': fields.String(description='Category name'),
    'description': fields.String(description='Category description'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp')
})

service_categories_response_model = auth_ns.model('ServiceCategoriesResponse', {
    'categories': fields.List(fields.Nested(service_category_model), description='List of service categories'),
    'total': fields.Integer(description='Total number of categories')
})

provider_service_schedule_item_model = auth_ns.model('ProviderServiceScheduleItem', {
    'schedule_day': fields.String(required=True, description='Day of the week', enum=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
    'start_time': fields.String(required=True, description='Start time in HH:MM format'),
    'end_time': fields.String(required=True, description='End time in HH:MM format')
})

provider_service_schedule_model = auth_ns.model('ProviderServiceSchedule', {
    'provider_service_id': fields.Integer(required=True, description='Provider service ID'),
    'schedules': fields.List(fields.Nested(provider_service_schedule_item_model), required=True, description='List of schedules to create')
})

provider_service_schedule_response_model = auth_ns.model('ProviderServiceScheduleResponse', {
    'message': fields.String(description='Success message'),
    'schedules': fields.List(fields.Raw, description='Created schedule details'),
    'total_created': fields.Integer(description='Total number of schedules created'),
    'failed_schedules': fields.List(fields.Raw, description='List of schedules that failed to create (if any)')
})

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@auth_ns.route('/user/register')
class UserRegister(Resource):
    @auth_ns.expect(user_register_model)
    @auth_ns.marshal_with(register_success_user_model, code=201)
    @auth_ns.response(400, 'Validation Error', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.doc(description='''Register a new user account.
    
**Required Fields:**
- full_name: Complete name of the user
- email: Valid email address (must be unique)
- address: Complete residential address
- password: Minimum 6 characters

**Optional Fields:**
- id_front: URL/path to front ID document (driver's license, passport, etc.)
- id_back: URL/path to back ID document

**Sample Payload:**
```json
{
  "full_name": "John Michael Doe",
  "email": "john.doe@example.com",
  "address": "123 Main Street, Barangay San Miguel, Quezon City, Metro Manila 1100, Philippines",
  "password": "SecurePassword123!",
  "id_front": "https://example.com/documents/john_doe_id_front.jpg",
  "id_back": "https://example.com/documents/john_doe_id_back.jpg"
}
```''')
    def post(self):
        """Register a new user account"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
        try:
            data = request.get_json()
            
            # Validation
            if not all(k in data for k in ['full_name', 'email', 'address', 'password']):
                return {'error': 'Missing required fields'}, 400
            
            if not validate_email(data['email']):
                return {'error': 'Invalid email format'}, 400
            
            if len(data['password']) < 6:
                return {'error': 'Password must be at least 6 characters'}, 400
            
            # Check if user already exists
            if User.query.filter_by(email=data['email']).first():
                return {'error': 'Email already registered'}, 400
            
            # Create new user
            user = User(
                full_name=data['full_name'],
                email=data['email'],
                address=data['address'],
                id_front=data.get('id_front'),
                id_back=data.get('id_back')
            )
            user.set_password(data['password'])

            db.session.add(user)
            db.session.commit()

            # Create access token
            access_token = create_access_token(identity=str(user.id), additional_claims={'user_type': 'user'})
            
            return {
                'message': 'User registered successfully',
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'id_front': user.id_front,
                    'id_back': user.id_back,
                    'user_type': 'user'
                }
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@auth_ns.route('/user/login')
class UserLogin(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.marshal_with(login_success_user_model, code=200)
    @auth_ns.response(400, 'Missing credentials', error_model)
    @auth_ns.response(401, 'Invalid credentials', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Login user and get access token with full user details"""
        try:
            data = request.get_json()
            
            if not all(k in data for k in ['email', 'password']):
                return {'error': 'Missing email or password'}, 400
            
            user = User.query.filter_by(email=data['email']).first()
            
            if not user or not user.check_password(data['password']):
                return {'error': 'Invalid email or password'}, 401

            access_token = create_access_token(identity=str(user.id), additional_claims={'user_type': 'user'})
            
            return {
                'message': 'Login successful',
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'id_front': user.id_front,
                    'id_back': user.id_back,
                    'user_type': 'user'
                }
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@auth_ns.route('/provider/register')
class ProviderRegister(Resource):
    @auth_ns.doc(description='''Register a new service provider account with optional file uploads.
    
**Support both JSON and multipart/form-data requests**

**For JSON requests:**
- Content-Type: application/json
- Use URLs for document fields

**For multipart/form-data requests:**
- Content-Type: multipart/form-data  
- Upload actual files for documents
- Supports multiple image uploads like upload-photos endpoint

**Required Fields:**
- full_name: Complete name of the provider
- email: Valid email address (must be unique)
- address: Complete business/service address
- password: Minimum 6 characters

**Optional Fields:**
- business_name: Name of the business (if applicable)
- contact_number: Contact phone number
- about: Description about the provider and services

**Optional File Fields (for multipart/form-data):**
- bir_id_front: BIR ID front document file
- bir_id_back: BIR ID back document file  
- business_permit: Business permit document file
- image_logo: Business logo image file
- images: Multiple image files (similar to upload-photos functionality)

**JSON Sample Payload:**
```json
{
  "business_name": "Acme Home Services",
  "full_name": "Maria Santos",
  "email": "maria@acmeservices.com",
  "contact_number": "+63-912-345-6789",
  "address": "123 Business Ave, Makati City, Philippines",
  "password": "SecurePass123",
  "bir_id_front": "https://example.com/docs/bir_front.jpg",
  "bir_id_back": "https://example.com/docs/bir_back.jpg",
  "business_permit": "https://example.com/docs/permit.pdf",
  "image_logo": "https://example.com/docs/logo.jpg",
  "about": "Professional home cleaning and maintenance services"
}
```''')
    def post(self):
        """Register a new service provider account with optional file upload support"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            print("=== PROVIDER REGISTRATION DEBUG ===")
            
            # Determine content type and parse data accordingly
            content_type = request.content_type or ''
            is_multipart = content_type.startswith('multipart/form-data')
            
            if is_multipart:
                print("Processing multipart/form-data request")
                data = request.form.to_dict()
                files = request.files
                print(f"Form data: {data}")
                print(f"Files: {list(files.keys())}")
            else:
                print("Processing JSON request")
                data = request.get_json() or {}
                files = {}
                print(f"JSON data: {data}")
            
            # Validation
            if not all(k in data for k in ['full_name', 'email', 'address', 'password']):
                print("Missing required fields")
                return {'error': 'Missing required fields'}, 400
            
            if not validate_email(data['email']):
                print("Invalid email format")
                return {'error': 'Invalid email format'}, 400
            
            if len(data['password']) < 6:
                print("Password too short")
                return {'error': 'Password must be at least 6 characters'}, 400
            
            # Check if provider already exists
            existing_provider = Provider.query.filter_by(email=data['email']).first()
            if existing_provider:
                print(f"Email already registered: {data['email']}")
                return {'error': 'Email already registered'}, 400
            
            # Handle file uploads if multipart request
            uploaded_files = {}
            additional_images = []
            
            if is_multipart:
                print("Processing file uploads...")
                
                # Upload individual document files
                file_fields = ['bir_id_front', 'bir_id_back', 'business_permit', 'image_logo']
                for field in file_fields:
                    if field in files and files[field].filename != '':
                        print(f"Uploading {field}...")
                        upload_result = upload_file_to_r2(
                            files[field], 
                            'provider-documents',
                            prefix=f'provider_{field}'
                        )
                        if upload_result['success']:
                            uploaded_files[field] = upload_result['url']
                            print(f"{field} uploaded successfully: {upload_result['url']}")
                        else:
                            print(f"{field} upload failed: {upload_result['error']}")
                            return {'error': f'{field} upload failed: {upload_result["error"]}'}, 400
                
                # Handle multiple image uploads (similar to upload-photos)
                if 'images' in files:
                    image_files = request.files.getlist('images')
                    if image_files and len(image_files) > 0:
                        print(f"Processing {len(image_files)} additional images...")
                        
                        for i, image_file in enumerate(image_files):
                            if image_file.filename != '':
                                upload_result = upload_file_to_r2(
                                    image_file, 
                                    'provider-images',
                                    prefix='provider_image'
                                )
                                if upload_result['success']:
                                    additional_images.append({
                                        'url': upload_result['url'],
                                        'filename': image_file.filename,
                                        'sort_order': i
                                    })
                                    print(f"Additional image {i+1} uploaded: {upload_result['url']}")
                                else:
                                    print(f"Additional image {i+1} upload failed: {upload_result['error']}")
                                    # Don't fail the whole registration for additional image failures
            
            print("Creating provider object...")
            # Create new provider with file URLs or form data
            provider = Provider(
                business_name=data.get('business_name'),
                full_name=data['full_name'],
                email=data['email'],
                contact_number=data.get('contact_number'),
                address=data['address'],
                bir_id_front=uploaded_files.get('bir_id_front') or data.get('bir_id_front'),
                bir_id_back=uploaded_files.get('bir_id_back') or data.get('bir_id_back'),
                business_permit=uploaded_files.get('business_permit') or data.get('business_permit'),
                image_logo=uploaded_files.get('image_logo') or data.get('image_logo'),
                about=data.get('about'),
                is_active=True  # Default to active
            )
            print("Provider object created successfully")
            
            print("Setting password...")
            provider.set_password(data['password'])
            print("Password set successfully")
            
            print("Adding to database session...")
            db.session.add(provider)
            print("Committing to database...")
            db.session.commit()
            print("Database commit successful")
            
            # Create access token
            print("Creating access token...")
            access_token = create_access_token(identity=str(provider.id), additional_claims={'user_type': 'provider'})
            print("Access token created successfully")
            
            print("Preparing response...")
            response_data = {
                'message': 'Provider registered successfully',
                'access_token': access_token,
                'provider': {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'bir_id_front': provider.bir_id_front,
                    'bir_id_back': provider.bir_id_back,
                    'business_permit': provider.business_permit,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'user_type': 'provider'
                }
            }
            
            # Include additional images in response if any were uploaded
            if additional_images:
                response_data['additional_images'] = additional_images
                response_data['message'] += f' with {len(additional_images)} additional images'
            
            print("Response prepared successfully")
            print("=== REGISTRATION SUCCESSFUL ===")
            return response_data, 201
            
        except Exception as e:
            print(f"=== ERROR DURING REGISTRATION ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"Error details: {repr(e)}")
            import traceback
            print(f"Full traceback:")
            traceback.print_exc()
            db.session.rollback()
            return {'error': f'Registration failed: {str(e)}'}, 500

@auth_ns.route('/provider/login')
class ProviderLogin(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.marshal_with(login_success_provider_model, code=200)
    @auth_ns.response(400, 'Missing credentials', error_model)
    @auth_ns.response(401, 'Invalid credentials', error_model)
    @auth_ns.response(403, 'Account inactive', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.doc(description='''Login as a service provider.
    
**Payload:**
```json
{
  "email": "provider@example.com",
  "password": "yourpassword"
}
```

**Response includes:**
- JWT access token for API authentication
- Complete provider profile information
- Account status (is_active)

**Note:** Only active provider accounts can login. Inactive accounts will receive a 403 error.''')
    def post(self):
        """Login provider and get access token with full provider details"""
        try:
            data = request.get_json()
            
            if not all(k in data for k in ['email', 'password']):
                return {'error': 'Missing email or password'}, 400
            
            provider = Provider.query.filter_by(email=data['email']).first()
            
            if not provider or not provider.check_password(data['password']):
                return {'error': 'Invalid email or password'}, 401
            
            if not provider.is_active:
                return {'error': 'Provider account is inactive'}, 403

            access_token = create_access_token(identity=str(provider.id), additional_claims={'user_type': 'provider'})
            
            return {
                'message': 'Login successful',
                'access_token': access_token,
                'provider': {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'bir_id_front': provider.bir_id_front,
                    'bir_id_back': provider.bir_id_back,
                    'business_permit': provider.business_permit,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'user_type': 'provider'
                }
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@auth_ns.route('/user/register-with-upload')
class UserRegisterWithUpload(Resource):
    @auth_ns.doc(description='''Register a new user account with file uploads.
    
**Form Data Fields:**
- full_name: Complete name of the user (required)
- email: Valid email address (required, must be unique)
- address: Complete residential address (required)
- password: Minimum 6 characters (required)
- id_front: Front ID document file (optional)
- id_back: Back ID document file (optional)

**File Requirements:**
- Allowed formats: PNG, JPG, JPEG, GIF, PDF
- Files will be uploaded to R2 storage automatically
- Returns URLs to uploaded files

**Content-Type:** multipart/form-data''')
    def post(self):
        """Register a new user account with file uploads"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            # Get form data
            data = request.form.to_dict()
            files = request.files
            
            # Validation
            if not all(k in data for k in ['full_name', 'email', 'address', 'password']):
                return {'error': 'Missing required fields'}, 400
            
            if not validate_email(data['email']):
                return {'error': 'Invalid email format'}, 400
            
            if len(data['password']) < 6:
                return {'error': 'Password must be at least 6 characters'}, 400
            
            # Check if user already exists
            if User.query.filter_by(email=data['email']).first():
                return {'error': 'Email already registered'}, 400
            
            # Upload files if provided
            id_front_url = None
            id_back_url = None
            
            if 'id_front' in files and files['id_front'].filename != '':
                upload_result = upload_file_to_r2(
                    files['id_front'], 
                    'user-documents',
                    prefix='user_id_front'
                )
                if upload_result['success']:
                    id_front_url = upload_result['url']
                else:
                    return {'error': f'ID front upload failed: {upload_result["error"]}'}, 400
            
            if 'id_back' in files and files['id_back'].filename != '':
                upload_result = upload_file_to_r2(
                    files['id_back'], 
                    'user-documents',
                    prefix='user_id_back'
                )
                if upload_result['success']:
                    id_back_url = upload_result['url']
                else:
                    return {'error': f'ID back upload failed: {upload_result["error"]}'}, 400
            
            # Create new user
            user = User(
                full_name=data['full_name'],
                email=data['email'],
                address=data['address'],
                id_front=id_front_url,
                id_back=id_back_url
            )
            user.set_password(data['password'])

            db.session.add(user)
            db.session.commit()

            # Create access token
            access_token = create_access_token(identity=str(user.id), additional_claims={'user_type': 'user'})
            
            return {
                'message': 'User registered successfully',
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'id_front': user.id_front,
                    'id_back': user.id_back,
                    'user_type': 'user'
                }
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@auth_ns.route('/provider/register-with-upload')
class ProviderRegisterWithUpload(Resource):
    @auth_ns.doc(description='''Register a new service provider account with file uploads.
    
**Form Data Fields:**
- full_name: Complete name of the provider (required)
- email: Valid email address (required, must be unique)
- address: Complete business/service address (required)
- password: Minimum 6 characters (required)
- business_name: Name of the business (optional)
- contact_number: Contact phone number (optional)
- about: Description about the provider and services (optional)
- bir_id_front: BIR ID front document file (optional)
- bir_id_back: BIR ID back document file (optional)
- business_permit: Business permit document file (optional)
- image_logo: Business logo image file (optional)

**File Requirements:**
- Allowed formats: PNG, JPG, JPEG, GIF, PDF
- Files will be uploaded to R2 storage automatically
- Returns URLs to uploaded files

**Content-Type:** multipart/form-data''')
    def post(self):
        """Register a new service provider account with file uploads"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            # Get form data
            data = request.form.to_dict()
            files = request.files
            
            # Validation
            if not all(k in data for k in ['full_name', 'email', 'address', 'password']):
                return {'error': 'Missing required fields'}, 400
            
            if not validate_email(data['email']):
                return {'error': 'Invalid email format'}, 400
            
            if len(data['password']) < 6:
                return {'error': 'Password must be at least 6 characters'}, 400
            
            # Check if provider already exists
            if Provider.query.filter_by(email=data['email']).first():
                return {'error': 'Email already registered'}, 400
            
            # Upload files if provided
            bir_id_front_url = None
            bir_id_back_url = None
            business_permit_url = None
            image_logo_url = None
            
            if 'bir_id_front' in files and files['bir_id_front'].filename != '':
                upload_result = upload_file_to_r2(
                    files['bir_id_front'], 
                    'provider-documents',
                    prefix='provider_bir_front'
                )
                if upload_result['success']:
                    bir_id_front_url = upload_result['url']
                else:
                    return {'error': f'BIR ID front upload failed: {upload_result["error"]}'}, 400
            
            if 'bir_id_back' in files and files['bir_id_back'].filename != '':
                upload_result = upload_file_to_r2(
                    files['bir_id_back'], 
                    'provider-documents',
                    prefix='provider_bir_back'
                )
                if upload_result['success']:
                    bir_id_back_url = upload_result['url']
                else:
                    return {'error': f'BIR ID back upload failed: {upload_result["error"]}'}, 400
            
            if 'business_permit' in files and files['business_permit'].filename != '':
                upload_result = upload_file_to_r2(
                    files['business_permit'], 
                    'provider-documents',
                    prefix='provider_business_permit'
                )
                if upload_result['success']:
                    business_permit_url = upload_result['url']
                else:
                    return {'error': f'Business permit upload failed: {upload_result["error"]}'}, 400
            
            if 'image_logo' in files and files['image_logo'].filename != '':
                upload_result = upload_file_to_r2(
                    files['image_logo'], 
                    'provider-documents',
                    prefix='provider_logo'
                )
                if upload_result['success']:
                    image_logo_url = upload_result['url']
                else:
                    return {'error': f'Logo image upload failed: {upload_result["error"]}'}, 400
            
            # Create new provider
            provider = Provider(
                business_name=data.get('business_name'),
                full_name=data['full_name'],
                email=data['email'],
                contact_number=data.get('contact_number'),
                address=data['address'],
                bir_id_front=bir_id_front_url,
                bir_id_back=bir_id_back_url,
                business_permit=business_permit_url,
                image_logo=image_logo_url,
                about=data.get('about'),
                is_active=True
            )
            provider.set_password(data['password'])

            db.session.add(provider)
            db.session.commit()

            # Create access token
            access_token = create_access_token(identity=str(provider.id), additional_claims={'user_type': 'provider'})
            
            return {
                'message': 'Provider registered successfully',
                'access_token': access_token,
                'provider': {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'bir_id_front': provider.bir_id_front,
                    'bir_id_back': provider.bir_id_back,
                    'business_permit': provider.business_permit,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'user_type': 'provider'
                }
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@auth_ns.route('/me')
class GetCurrentUser(Resource):
    @auth_ns.doc(security='Bearer')
    @jwt_required()
    def get(self):
        """Get current authenticated user/provider info using Bearer token"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            claims = get_jwt()
            user_id = int(current_identity)
            user_type = claims.get('user_type')
            
            if user_type == 'user':
                user = User.query.get(user_id)
                if not user:
                    return {'error': 'User not found'}, 404
                return {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'id_front': user.id_front,
                    'id_back': user.id_back,
                    'user_type': 'user'
                }
            else:  # provider
                provider = Provider.query.get(user_id)
                if not provider:
                    return {'error': 'Provider not found'}, 404
                return {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'bir_id_front': provider.bir_id_front,
                    'bir_id_back': provider.bir_id_back,
                    'business_permit': provider.business_permit,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'user_type': 'provider'
                }
                
        except Exception as e:
            return {'error': str(e)}, 500

@auth_ns.route('/provider/register-categories')
class ProviderCategoryRegister(Resource):
    @auth_ns.expect(provider_category_register_model)
    @auth_ns.marshal_with(provider_category_response_model, code=201)
    @auth_ns.response(400, 'Validation Error', error_model)
    @auth_ns.response(404, 'Provider or Category Not Found', error_model)
    @auth_ns.response(409, 'Category Already Registered', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.doc(description='''Register a provider for multiple service categories.
    
**Required Fields:**
- provider_id: ID of the existing provider
- category_ids: Array of service category IDs to register for

**Sample Payload:**
```json
{
  "provider_id": 1,
  "category_ids": [1, 2, 3]
}
```

**Response includes:**
- Success message
- Provider ID
- List of registered categories with details (id, name, description)

**Note:** This endpoint will skip categories that are already registered for the provider and only add new ones.''')
    def post(self):
        """Register a provider for multiple service categories"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            data = request.get_json()
            
            # Validation
            if not all(k in data for k in ['provider_id', 'category_ids']):
                return {'error': 'Missing required fields: provider_id and category_ids'}, 400
            
            if not isinstance(data['category_ids'], list) or len(data['category_ids']) == 0:
                return {'error': 'category_ids must be a non-empty list'}, 400
            
            # Check if provider exists
            provider = Provider.query.get(data['provider_id'])
            if not provider:
                return {'error': 'Provider not found'}, 404
            
            # Check if all categories exist
            category_ids = data['category_ids']
            categories = ServiceCategory.query.filter(ServiceCategory.id.in_(category_ids)).all()
            
            if len(categories) != len(category_ids):
                found_ids = [cat.id for cat in categories]
                missing_ids = [cid for cid in category_ids if cid not in found_ids]
                return {'error': f'Categories not found: {missing_ids}'}, 404
            
            # Get existing registrations to avoid duplicates
            existing_registrations = ProviderCategoryMembership.query.filter(
                ProviderCategoryMembership.provider_id == data['provider_id'],
                ProviderCategoryMembership.category_id.in_(category_ids)
            ).all()
            
            existing_category_ids = [reg.category_id for reg in existing_registrations]
            new_category_ids = [cid for cid in category_ids if cid not in existing_category_ids]
            
            # Create new registrations
            new_registrations = []
            for category_id in new_category_ids:
                registration = ProviderCategoryMembership(
                    provider_id=data['provider_id'],
                    category_id=category_id
                )
                db.session.add(registration)
                new_registrations.append(registration)
            
            db.session.commit()
            
            # Prepare response with category details
            registered_categories = []
            for category in categories:
                registered_categories.append({
                    'id': category.id,
                    'category_name': category.category_name,
                    'description': category.description,
                    'already_registered': category.id in existing_category_ids
                })
            
            return {
                'message': f'Provider registered for {len(new_category_ids)} new categories (skipped {len(existing_category_ids)} already registered)',
                'provider_id': data['provider_id'],
                'registered_categories': registered_categories
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@auth_ns.route('/provider/register-service')
class ProviderServiceRegister(Resource):
    @auth_ns.expect(provider_service_register_model)
    @auth_ns.marshal_with(provider_service_response_model, code=201)
    @auth_ns.response(400, 'Validation Error', error_model)
    @auth_ns.response(404, 'Provider or Category Not Found', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.doc(description='''Register a new service for a provider.
    
**Required Fields:**
- provider_id: ID of the existing provider
- category_id: ID of the service category
- service_title: Title of the service (max 150 characters)

**Optional Fields:**
- service_description: Detailed description of the service
- price_decimal: Service price (decimal with up to 2 decimal places)
- duration_minutes: Expected duration of the service in minutes
- is_active: Whether the service is active (defaults to True)

**Sample Payload:**
```json
{
  "provider_id": 1,
  "category_id": 2,
  "service_title": "House Cleaning Service",
  "service_description": "Complete house cleaning including all rooms, kitchen, and bathrooms",
  "price_decimal": 150.00,
  "duration_minutes": 120,
  "is_active": true
}
```

**Response includes:**
- Success message
- Complete service details including timestamps''')
    def post(self):
        """Register a new service for a provider"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            data = request.get_json()
            
            # Validation
            required_fields = ['provider_id', 'category_id', 'service_title']
            if not all(k in data for k in required_fields):
                return {'error': f'Missing required fields: {", ".join(required_fields)}'}, 400
            
            # Validate service title length
            if len(data['service_title']) > 150:
                return {'error': 'Service title must be 150 characters or less'}, 400
            
            # Check if provider exists
            provider = Provider.query.get(data['provider_id'])
            if not provider:
                return {'error': 'Provider not found'}, 404
            
            # Check if category exists
            category = ServiceCategory.query.get(data['category_id'])
            if not category:
                return {'error': 'Service category not found'}, 404
            
            # Validate price if provided
            if 'price_decimal' in data and data['price_decimal'] is not None:
                try:
                    price = float(data['price_decimal'])
                    if price < 0:
                        return {'error': 'Price must be non-negative'}, 400
                except (ValueError, TypeError):
                    return {'error': 'Invalid price format'}, 400
            
            # Validate duration if provided
            if 'duration_minutes' in data and data['duration_minutes'] is not None:
                try:
                    duration = int(data['duration_minutes'])
                    if duration <= 0:
                        return {'error': 'Duration must be positive'}, 400
                except (ValueError, TypeError):
                    return {'error': 'Invalid duration format'}, 400
            
            # Create new provider service
            provider_service = ProviderService(
                provider_id=data['provider_id'],
                category_id=data['category_id'],
                service_title=data['service_title'],
                service_description=data.get('service_description'),
                price_decimal=data.get('price_decimal'),
                duration_minutes=data.get('duration_minutes'),
                is_active=data.get('is_active', True)
            )
            
            db.session.add(provider_service)
            db.session.commit()
            
            # Prepare response
            service_details = {
                'id': provider_service.id,
                'provider_id': provider_service.provider_id,
                'category_id': provider_service.category_id,
                'category_name': category.category_name,
                'service_title': provider_service.service_title,
                'service_description': provider_service.service_description,
                'price_decimal': float(provider_service.price_decimal) if provider_service.price_decimal else None,
                'duration_minutes': provider_service.duration_minutes,
                'is_active': provider_service.is_active,
                'created_at': provider_service.created_at.isoformat() if provider_service.created_at else None,
                'updated_at': provider_service.updated_at.isoformat() if provider_service.updated_at else None
            }
            
            return {
                'message': 'Provider service registered successfully',
                'service': service_details
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@auth_ns.route('/provider/service/upload-photos')
class ProviderServicePhotoUpload(Resource):
    @auth_ns.marshal_with(provider_service_photo_response_model, code=201)
    @auth_ns.response(400, 'Validation Error', error_model)
    @auth_ns.response(404, 'Provider Service Not Found', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.doc(description='''Upload photos for a provider service with bulk upload support.
    
**Form Data Fields:**
- provider_service_id: ID of the provider service (required)
- photos: One or more image files (required) - supports bulk upload
- sort_orders: Comma-separated sort order values (optional, defaults to incremental values starting from 0)

**File Requirements:**
- Allowed formats: PNG, JPG, JPEG, GIF
- Files are uploaded to CDN storage (https://cdn.jamesgalos.shop)
- Multiple files can be uploaded in a single request
- Files are renamed with proper naming convention: service_photo_service_{id}_{timestamp}_{uuid}.{ext}

**Content-Type:** multipart/form-data

**Bulk Upload Examples:**
```bash
# Upload multiple photos at once
curl -X POST /auth/provider/service/upload-photos \\
  -F "provider_service_id=1" \\
  -F "photos=@photo1.jpg" \\
  -F "photos=@photo2.jpg" \\
  -F "photos=@photo3.png" \\
  -F "sort_orders=0,1,2"

# Let system auto-assign sort orders
curl -X POST /auth/provider/service/upload-photos \\
  -F "provider_service_id=1" \\
  -F "photos=@photo1.jpg" \\
  -F "photos=@photo2.jpg"
```

**Response includes:**
- Success message with upload statistics
- List of successfully uploaded photo details with CDN URLs
- Information about failed uploads (if any)
- Total attempted vs successful upload counts''')
    def post(self):
        """Upload photos for a provider service"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            # Get form data
            data = request.form.to_dict()
            files = request.files.getlist('photos')
            
            # Validation
            if 'provider_service_id' not in data:
                return {'error': 'Missing required field: provider_service_id'}, 400
            
            if not files or len(files) == 0:
                return {'error': 'No photos provided'}, 400
            
            # Validate provider service ID
            try:
                provider_service_id = int(data['provider_service_id'])
            except (ValueError, TypeError):
                return {'error': 'Invalid provider_service_id format'}, 400
            
            # Check if provider service exists
            provider_service = ProviderService.query.get(provider_service_id)
            if not provider_service:
                return {'error': 'Provider service not found'}, 404
            
            # Parse sort orders if provided
            sort_orders = []
            if 'sort_orders' in data and data['sort_orders']:
                try:
                    sort_orders = [int(x.strip()) for x in data['sort_orders'].split(',')]
                    if len(sort_orders) != len(files):
                        return {'error': 'Number of sort_orders must match number of photos'}, 400
                except (ValueError, TypeError):
                    return {'error': 'Invalid sort_orders format'}, 400
            else:
                # Default to incremental sort orders starting from 0
                sort_orders = list(range(len(files)))
            
            # Upload files and create photo records
            uploaded_photos = []
            failed_uploads = []
            
            for i, file in enumerate(files):
                if file.filename == '':
                    failed_uploads.append({
                        'index': i,
                        'filename': 'empty',
                        'error': 'Empty filename'
                    })
                    continue
                    
                # Upload file to R2 with proper naming
                upload_result = upload_file_to_r2(
                    file, 
                    'provider-service-photos', 
                    prefix='service_photo',
                    service_id=provider_service_id
                )
                
                if not upload_result['success']:
                    failed_uploads.append({
                        'index': i,
                        'filename': file.filename,
                        'error': upload_result['error']
                    })
                    continue
                
                # Create photo record
                service_photo = ProviderServicePhoto(
                    provider_service_id=provider_service_id,
                    photo_url=upload_result['url'],
                    sort_order=sort_orders[i]
                )
                
                db.session.add(service_photo)
                uploaded_photos.append(service_photo)
            
            # Check if any files were uploaded successfully
            if not uploaded_photos:
                return {
                    'error': 'No photos were uploaded successfully',
                    'failed_uploads': failed_uploads
                }, 400
            
            db.session.commit()
            
            # Prepare response
            photo_details = []
            for photo in uploaded_photos:
                photo_details.append({
                    'id': photo.id,
                    'provider_service_id': photo.provider_service_id,
                    'photo_url': photo.photo_url,
                    'sort_order': photo.sort_order,
                    'created_at': photo.created_at.isoformat() if photo.created_at else None
                })
            
            response_data = {
                'message': f'{len(photo_details)} photos uploaded successfully',
                'photos': photo_details,
                'total_attempted': len(files),
                'successful_uploads': len(photo_details),
                'failed_uploads_count': len(failed_uploads)
            }
            
            # Include failed uploads info if any
            if failed_uploads:
                response_data['failed_uploads'] = failed_uploads
                response_data['message'] = f'{len(photo_details)} photos uploaded successfully, {len(failed_uploads)} failed'
            
            return response_data, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@auth_ns.route('/user/register-service')
class UserServiceRegister(Resource):
    @auth_ns.expect(user_service_register_model)
    @auth_ns.marshal_with(user_service_response_model, code=201)
    @auth_ns.response(400, 'Validation Error', error_model)
    @auth_ns.response(404, 'User or Category Not Found', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.doc(description='''Register a new service for a user.
    
**Required Fields:**
- user_id: ID of the existing user
- category_id: ID of the service category
- service_title: Title of the service (max 150 characters)

**Optional Fields:**
- service_description: Detailed description of the service
- price_decimal: Service price (decimal with up to 2 decimal places)
- is_active: Whether the service is active (defaults to True)

**Sample Payload:**
```json
{
  "user_id": 1,
  "category_id": 2,
  "service_title": "Tutoring Service",
  "service_description": "Mathematics and science tutoring for high school students",
  "price_decimal": 25.00,
  "is_active": true
}
```

**Response includes:**
- Success message
- Complete service details including timestamps''')
    def post(self):
        """Register a new service for a user"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            data = request.get_json()
            
            # Validation
            required_fields = ['user_id', 'category_id', 'service_title']
            if not all(k in data for k in required_fields):
                return {'error': f'Missing required fields: {", ".join(required_fields)}'}, 400
            
            # Validate service title length
            if len(data['service_title']) > 150:
                return {'error': 'Service title must be 150 characters or less'}, 400
            
            # Check if user exists
            user = User.query.get(data['user_id'])
            if not user:
                return {'error': 'User not found'}, 404
            
            # Check if category exists
            category = ServiceCategory.query.get(data['category_id'])
            if not category:
                return {'error': 'Service category not found'}, 404
            
            # Validate price if provided
            if 'price_decimal' in data and data['price_decimal'] is not None:
                try:
                    price = float(data['price_decimal'])
                    if price < 0:
                        return {'error': 'Price must be non-negative'}, 400
                except (ValueError, TypeError):
                    return {'error': 'Invalid price format'}, 400
            
            # Create new user service
            user_service = UserServiceCategory(
                user_id=data['user_id'],
                category_id=data['category_id'],
                service_title=data['service_title'],
                service_description=data.get('service_description'),
                price_decimal=data.get('price_decimal'),
                is_active=data.get('is_active', True)
            )
            
            db.session.add(user_service)
            db.session.commit()
            
            # Prepare response
            service_details = {
                'id': user_service.id,
                'user_id': user_service.user_id,
                'category_id': user_service.category_id,
                'category_name': category.category_name,
                'service_title': user_service.service_title,
                'service_description': user_service.service_description,
                'price_decimal': float(user_service.price_decimal) if user_service.price_decimal else None,
                'is_active': user_service.is_active,
                'created_at': user_service.created_at.isoformat() if user_service.created_at else None,
                'updated_at': user_service.updated_at.isoformat() if user_service.updated_at else None
            }
            
            return {
                'message': 'User service registered successfully',
                'service': service_details
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@auth_ns.route('/service-categories')
class ServiceCategoriesList(Resource):
    @auth_ns.marshal_with(service_categories_response_model, code=200)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.doc(description='''Get all available service categories.
    
**Response includes:**
- List of all service categories with details
- Total count of categories

**Sample Response:**
```json
{
  "categories": [
    {
      "id": 1,
      "category_name": "Home Cleaning",
      "description": "Professional home cleaning services",
      "created_at": "2024-01-01T10:00:00",
      "updated_at": "2024-01-01T10:00:00"
    },
    {
      "id": 2,
      "category_name": "Tutoring",
      "description": "Educational tutoring services",
      "created_at": "2024-01-01T11:00:00",
      "updated_at": "2024-01-01T11:00:00"
    }
  ],
  "total": 2
}
```

**Note:** This endpoint does not require authentication and returns all active service categories.''')
    def get(self):
        """Get all service categories"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            # Get all service categories
            categories = ServiceCategory.query.all()
            
            # Prepare response
            category_list = []
            for category in categories:
                category_list.append({
                    'id': category.id,
                    'category_name': category.category_name,
                    'description': category.description,
                    'created_at': category.created_at.isoformat() if category.created_at else None,
                    'updated_at': category.updated_at.isoformat() if category.updated_at else None
                })
            
            return {
                'categories': category_list,
                'total': len(category_list)
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@auth_ns.route('/providers/schedule')
class ProviderServiceScheduleCreate(Resource):
    @auth_ns.expect(provider_service_schedule_model)
    @auth_ns.marshal_with(provider_service_schedule_response_model, code=201)
    @auth_ns.response(400, 'Validation Error', error_model)
    @auth_ns.response(404, 'Provider Service Not Found', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.doc(description='''Create multiple schedules for a provider service in one request.
    
**Required Fields:**
- provider_service_id: ID of the existing provider service
- schedules: Array of schedule objects, each containing:
  - schedule_day: Day of the week (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
  - start_time: Start time (HH:MM format, 24-hour)
  - end_time: End time (HH:MM format, 24-hour)

**Sample Payload (Multiple Schedules):**
```json
{
  "provider_service_id": 1,
  "schedules": [
    {
      "schedule_day": "Monday",
      "start_time": "09:00",
      "end_time": "17:00"
    },
    {
      "schedule_day": "Tuesday", 
      "start_time": "10:00",
      "end_time": "16:00"
    },
    {
      "schedule_day": "Wednesday",
      "start_time": "08:30",
      "end_time": "17:30"
    }
  ]
}
```

**Response includes:**
- Success message with statistics
- List of created schedule details
- Total count of created schedules
- List of failed schedules (if any)

**Validation:**
- Provider service must exist
- Each schedule day must be a valid day of the week
- Start time must be before end time for each schedule
- Duplicate schedule days for the same service will be rejected

**Features:**
- Bulk creation of multiple schedules
- Partial success handling (some schedules may succeed while others fail)
- Detailed error reporting for failed schedules''')
    def post(self):
        """Create multiple schedules for a provider service"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            from datetime import datetime
            data = request.get_json()
            
            # Validation
            required_fields = ['provider_service_id', 'schedules']
            if not all(k in data for k in required_fields):
                return {'error': f'Missing required fields: {", ".join(required_fields)}'}, 400
            
            # Validate schedules is a list and not empty
            if not isinstance(data['schedules'], list) or len(data['schedules']) == 0:
                return {'error': 'schedules must be a non-empty list'}, 400
            
            # Check if provider service exists
            provider_service = ProviderService.query.get(data['provider_service_id'])
            if not provider_service:
                return {'error': 'Provider service not found'}, 404
            
            # Validate each schedule and prepare data
            valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            created_schedules = []
            failed_schedules = []
            seen_days = set()
            
            for i, schedule_data in enumerate(data['schedules']):
                # Validate required fields for each schedule
                schedule_required = ['schedule_day', 'start_time', 'end_time']
                if not all(k in schedule_data for k in schedule_required):
                    failed_schedules.append({
                        'index': i,
                        'schedule_data': schedule_data,
                        'error': f'Missing required fields: {", ".join(schedule_required)}'
                    })
                    continue
                
                # Validate schedule day
                if schedule_data['schedule_day'] not in valid_days:
                    failed_schedules.append({
                        'index': i,
                        'schedule_data': schedule_data,
                        'error': f'Invalid schedule_day. Must be one of: {", ".join(valid_days)}'
                    })
                    continue
                
                # Check for duplicate days in the same request
                if schedule_data['schedule_day'] in seen_days:
                    failed_schedules.append({
                        'index': i,
                        'schedule_data': schedule_data,
                        'error': f'Duplicate schedule_day: {schedule_data["schedule_day"]} already exists in this request'
                    })
                    continue
                
                seen_days.add(schedule_data['schedule_day'])
                
                # Validate time formats
                try:
                    start_time = datetime.strptime(schedule_data['start_time'], '%H:%M').time()
                    end_time = datetime.strptime(schedule_data['end_time'], '%H:%M').time()
                except ValueError:
                    failed_schedules.append({
                        'index': i,
                        'schedule_data': schedule_data,
                        'error': 'Invalid time format. Use HH:MM (24-hour format)'
                    })
                    continue
                
                # Validate that start time is before end time
                if start_time >= end_time:
                    failed_schedules.append({
                        'index': i,
                        'schedule_data': schedule_data,
                        'error': 'Start time must be before end time'
                    })
                    continue
                
                # Check if schedule for this day already exists in database
                existing_schedule = ProviderServiceSchedule.query.filter_by(
                    provider_service_id=data['provider_service_id'],
                    schedule_day=schedule_data['schedule_day']
                ).first()
                
                if existing_schedule:
                    failed_schedules.append({
                        'index': i,
                        'schedule_data': schedule_data,
                        'error': f'Schedule for {schedule_data["schedule_day"]} already exists for this service'
                    })
                    continue
                
                # Create schedule object
                try:
                    schedule = ProviderServiceSchedule(
                        provider_service_id=data['provider_service_id'],
                        schedule_day=schedule_data['schedule_day'],
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    db.session.add(schedule)
                    db.session.flush()  # Flush to get the ID but don't commit yet
                    
                    created_schedules.append({
                        'id': schedule.id,
                        'provider_service_id': schedule.provider_service_id,
                        'schedule_day': schedule.schedule_day,
                        'start_time': schedule.start_time.strftime('%H:%M'),
                        'end_time': schedule.end_time.strftime('%H:%M'),
                        'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
                        'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None
                    })
                    
                except Exception as e:
                    failed_schedules.append({
                        'index': i,
                        'schedule_data': schedule_data,
                        'error': f'Database error: {str(e)}'
                    })
            
            # Commit all successful schedules
            if created_schedules:
                db.session.commit()
            else:
                db.session.rollback()
                return {
                    'error': 'No schedules were created successfully',
                    'failed_schedules': failed_schedules
                }, 400
            
            # Prepare response
            response_data = {
                'message': f'{len(created_schedules)} schedule(s) created successfully',
                'schedules': created_schedules,
                'total_created': len(created_schedules)
            }
            
            if failed_schedules:
                response_data['failed_schedules'] = failed_schedules
                response_data['message'] = f'{len(created_schedules)} schedule(s) created successfully, {len(failed_schedules)} failed'
            
            return response_data, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500
        
