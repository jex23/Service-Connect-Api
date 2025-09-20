from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.upload import upload_file_to_r2, delete_file_from_r2

try:
    from models import (
        db, Provider, ProviderService, ProviderServicePhoto,
        ServiceCategory, ProviderCategoryMembership, ProviderServiceSchedule, ServiceBooking, User, PaymentStatus
    )
    DB_AVAILABLE = True
except Exception as e:
    print(f"Database models not available: {e}")
    DB_AVAILABLE = False

providers_ns = Namespace('providers', description='Provider management operations')

# API Models for documentation
provider_response_model = providers_ns.model('ProviderResponse', {
    'id': fields.Integer(description='Provider ID'),
    'business_name': fields.String(description='Business name'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email address'),
    'contact_number': fields.String(description='Contact phone number'),
    'address': fields.String(description='Address'),
    'bir_id_front': fields.String(description='BIR ID front document URL'),
    'bir_id_back': fields.String(description='BIR ID back document URL'),
    'business_permit': fields.String(description='Business permit document URL'),
    'image_logo': fields.String(description='Business logo image URL'),
    'about': fields.String(description='About the provider'),
    'is_active': fields.Boolean(description='Provider account status'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp')
})

provider_update_model = providers_ns.model('ProviderUpdate', {
    'business_name': fields.String(description='Business name'),
    'full_name': fields.String(description='Full name'),
    'address': fields.String(description='Address'),
    'about': fields.String(description='About the provider'),
    'password': fields.String(description='New password (minimum 6 characters)')
})

provider_service_model = providers_ns.model('ProviderService', {
    'id': fields.Integer(description='Service ID'),
    'category_id': fields.Integer(description='Category ID'),
    'category_name': fields.String(description='Category name'),
    'service_title': fields.String(description='Service title'),
    'service_description': fields.String(description='Service description'),
    'price_decimal': fields.Float(description='Service price'),
    'duration_minutes': fields.Integer(description='Duration in minutes'),
    'is_active': fields.Boolean(description='Service active status'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp'),
    'photos': fields.List(fields.Raw, description='Service photos')
})

provider_service_create_model = providers_ns.model('ProviderServiceCreate', {
    'category_id': fields.Integer(required=True, description='Service category ID'),
    'service_title': fields.String(required=True, description='Service title (max 150 characters)'),
    'service_description': fields.String(description='Service description'),
    'price_decimal': fields.Float(description='Service price'),
    'duration_minutes': fields.Integer(description='Service duration in minutes'),
    'is_active': fields.Boolean(description='Service active status (defaults to True)')
})

provider_service_photo_model = providers_ns.model('ProviderServicePhoto', {
    'id': fields.Integer(description='Photo ID'),
    'photo_url': fields.String(description='CDN URL of the photo'),
    'sort_order': fields.Integer(description='Display order'),
    'created_at': fields.String(description='Upload timestamp')
})

provider_category_model = providers_ns.model('ProviderCategory', {
    'id': fields.Integer(description='Category ID'),
    'category_name': fields.String(description='Category name'),
    'description': fields.String(description='Category description'),
    'is_registered': fields.Boolean(description='Whether provider is registered for this category')
})

error_model = providers_ns.model('Error', {
    'error': fields.String(description='Error message')
})

# ADMIN PROVIDER SERVICE MODELS
admin_provider_service_create_model = providers_ns.model('AdminProviderServiceCreate', {
    'category_id': fields.Integer(required=True, description='Service category ID'),
    'service_title': fields.String(required=True, description='Service title (max 150 characters)'),
    'service_description': fields.String(description='Service description'),
    'price_decimal': fields.Float(description='Service price'),
    'duration_minutes': fields.Integer(description='Service duration in minutes'),
    'is_active': fields.Boolean(description='Service active status (defaults to True)')
})

admin_provider_service_update_model = providers_ns.model('AdminProviderServiceUpdate', {
    'category_id': fields.Integer(description='Service category ID'),
    'service_title': fields.String(description='Service title (max 150 characters)'),
    'service_description': fields.String(description='Service description'),
    'price_decimal': fields.Float(description='Service price'),
    'duration_minutes': fields.Integer(description='Service duration in minutes'),
    'is_active': fields.Boolean(description='Service active status')
})

admin_provider_service_response_model = providers_ns.model('AdminProviderServiceResponse', {
    'id': fields.Integer(description='Service ID'),
    'provider_id': fields.Integer(description='Provider ID'),
    'category_id': fields.Integer(description='Category ID'),
    'category_name': fields.String(description='Category name'),
    'service_title': fields.String(description='Service title'),
    'service_description': fields.String(description='Service description'),
    'price_decimal': fields.Float(description='Service price'),
    'duration_minutes': fields.Integer(description='Duration in minutes'),
    'is_active': fields.Boolean(description='Service active status'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp'),
    'photos': fields.List(fields.Raw, description='Service photos'),
    'schedules': fields.List(fields.Raw, description='Service schedules')
})

admin_service_schedule_model = providers_ns.model('AdminServiceSchedule', {
    'schedule_day': fields.String(required=True, enum=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], description='Day of the week'),
    'start_time': fields.String(required=True, description='Start time (HH:MM format)'),
    'end_time': fields.String(required=True, description='End time (HH:MM format)')
})

# SERVICE BOOKING MODELS
service_booking_response_model = providers_ns.model('ServiceBookingResponse', {
    'id': fields.Integer(description='Booking ID'),
    'user_id': fields.Integer(description='User ID'),
    'user_name': fields.String(description='User full name'),
    'user_email': fields.String(description='User email'),
    'provider_id': fields.Integer(description='Provider ID'),
    'provider_service_id': fields.Integer(description='Provider Service ID'),
    'service_title': fields.String(description='Service title'),
    'booking_date': fields.String(description='Booking date (YYYY-MM-DD)'),
    'booking_day': fields.String(description='Booking day'),
    'booking_time': fields.String(description='Booking time (HH:MM:SS)'),
    'status': fields.String(description='Booking status'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp')
})

service_booking_create_model = providers_ns.model('ServiceBookingCreate', {
    'user_id': fields.Integer(required=True, description='User ID'),
    'provider_service_id': fields.Integer(required=True, description='Provider Service ID'),
    'booking_date': fields.String(required=True, description='Booking date (YYYY-MM-DD format)'),
    'booking_day': fields.String(required=True, enum=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], description='Day of the week'),
    'booking_time': fields.String(required=True, description='Booking time (HH:MM format)'),
    'status': fields.String(enum=['Pending', 'Confirmed', 'Completed', 'Cancelled'], description='Booking status (defaults to Pending)')
})

service_booking_update_model = providers_ns.model('ServiceBookingUpdate', {
    'booking_date': fields.String(description='Booking date (YYYY-MM-DD format)'),
    'booking_day': fields.String(enum=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], description='Day of the week'),
    'booking_time': fields.String(description='Booking time (HH:MM format)'),
    'status': fields.String(enum=['Pending', 'Confirmed', 'Completed', 'Cancelled'], description='Booking status')
})

# PROVIDER PROFILE MANAGEMENT
@providers_ns.route('/me')
class ProviderProfile(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.marshal_with(provider_response_model, code=200)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Provider not found', error_model)
    @jwt_required()
    def get(self):
        """Get current provider profile details"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']
            provider = Provider.query.get(provider_id)

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
                'created_at': provider.created_at.isoformat() if provider.created_at else None,
                'updated_at': provider.updated_at.isoformat() if provider.updated_at else None
            }, 200

        except Exception as e:
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.expect(provider_update_model)
    @providers_ns.marshal_with(provider_response_model, code=200)
    @providers_ns.response(400, 'Validation Error', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Provider not found', error_model)
    @providers_ns.doc(description='''Update current provider profile with optional document uploads.

**Supports both JSON and multipart/form-data requests**

**For JSON requests:**
- Content-Type: application/json
- Use URLs for document fields

**For multipart/form-data requests:**
- Content-Type: multipart/form-data
- Upload files directly for: bir_id_front, bir_id_back, business_permit, image_logo
- Text fields: business_name, full_name, address, about, password

**Text Fields:**
- business_name: Business name (optional)
- full_name: Full name (optional)
- address: Address (optional)
- about: About the provider (optional)
- password: New password (minimum 6 characters, optional)

**Document Fields (multipart only):**
- bir_id_front: BIR ID front document file (optional)
- bir_id_back: BIR ID back document file (optional)
- business_permit: Business permit document file (optional)
- image_logo: Business logo image file (optional)

**File Requirements:**
- Allowed formats: PNG, JPG, JPEG, GIF, PDF
- Files are uploaded to CDN storage (https://cdn.jamesgalos.shop)
- Old files are automatically deleted when replacing

**Examples:**
```json
PUT /api/providers/me
{
  "business_name": "Updated Business Name",
  "about": "Updated description"
}
```

**Or multipart form:**
```
PUT /api/providers/me
Content-Type: multipart/form-data

business_name=Updated Business Name
bir_id_front=<file>
image_logo=<file>
```''')
    @jwt_required()
    def put(self):
        """Update current provider profile with optional document uploads"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']
            provider = Provider.query.get(provider_id)

            if not provider:
                return {'error': 'Provider not found'}, 404

            # Determine content type and parse data accordingly
            content_type = request.content_type or ''
            is_multipart = content_type.startswith('multipart/form-data')

            if is_multipart:
                # Handle multipart/form-data request with file uploads
                data = request.form.to_dict()
                files = request.files

                # Handle document uploads
                uploaded_files = {}
                document_mappings = {
                    'bir_id_front': ('provider_bir_front', 'bir_id_front'),
                    'bir_id_back': ('provider_bir_back', 'bir_id_back'),
                    'business_permit': ('provider_business_permit', 'business_permit'),
                    'image_logo': ('provider_logo', 'image_logo')
                }

                for file_key, (prefix, db_field) in document_mappings.items():
                    if file_key in files and files[file_key].filename != '':
                        # Delete old file if exists
                        old_url = getattr(provider, db_field)
                        if old_url:
                            try:
                                delete_file_from_r2(old_url)
                            except Exception as e:
                                print(f"Warning: Failed to delete old {file_key}: {e}")

                        # Upload new file
                        upload_result = upload_file_to_r2(
                            files[file_key],
                            'provider-documents',
                            prefix=prefix
                        )
                        if upload_result['success']:
                            setattr(provider, db_field, upload_result['url'])
                            uploaded_files[file_key] = upload_result['url']
                        else:
                            return {'error': f'{file_key} upload failed: {upload_result["error"]}'}, 400
            else:
                # Handle JSON request
                data = request.get_json() or {}
                uploaded_files = {}

            # Update text fields if provided
            if 'business_name' in data:
                provider.business_name = data['business_name']
            if 'full_name' in data and data['full_name']:
                provider.full_name = data['full_name']
            if 'address' in data and data['address']:
                provider.address = data['address']
            if 'about' in data:
                provider.about = data['about']
            if 'password' in data and data['password']:
                if len(data['password']) < 6:
                    return {'error': 'Password must be at least 6 characters'}, 400
                provider.set_password(data['password'])

            db.session.commit()

            response = {
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
                'created_at': provider.created_at.isoformat() if provider.created_at else None,
                'updated_at': provider.updated_at.isoformat() if provider.updated_at else None
            }

            # Add uploaded files info if any were uploaded
            if uploaded_files:
                response['uploaded_files'] = uploaded_files
                response['message'] = f'Profile updated successfully with {len(uploaded_files)} document(s)'
            else:
                response['message'] = 'Profile updated successfully'

            return response, 200

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Provider account deleted successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Provider not found', error_model)
    @jwt_required()
    def delete(self):
        """Delete current provider account and all associated data"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            provider = Provider.query.get(provider_id)
            
            if not provider:
                return {'error': 'Provider not found'}, 404
            
            # Collect files to delete
            files_to_delete = []
            if provider.bir_id_front:
                files_to_delete.append(provider.bir_id_front)
            if provider.bir_id_back:
                files_to_delete.append(provider.bir_id_back)
            if provider.business_permit:
                files_to_delete.append(provider.business_permit)
            if provider.image_logo:
                files_to_delete.append(provider.image_logo)
            
            # Get service photos
            service_photos = db.session.query(ProviderServicePhoto).join(
                ProviderService, ProviderServicePhoto.provider_service_id == ProviderService.id
            ).filter(ProviderService.provider_id == provider_id).all()
            
            for photo in service_photos:
                files_to_delete.append(photo.photo_url)
            
            # Delete provider (cascade will handle related records)
            db.session.delete(provider)
            db.session.commit()
            
            # Delete files from storage
            for file_url in files_to_delete:
                try:
                    delete_file_from_r2(file_url)
                except Exception as e:
                    print(f"Warning: Failed to delete file {file_url}: {e}")
            
            return {'message': 'Provider account and all associated data deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# PROVIDER DOCUMENT MANAGEMENT
@providers_ns.route('/me/upload-documents')
class ProviderDocumentUpload(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Documents uploaded successfully')
    @providers_ns.response(400, 'Validation Error', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Provider not found', error_model)
    @providers_ns.doc(description='''Upload or update provider documents.
    
**Form Data Fields:**
- bir_id_front: BIR ID front document file (optional)
- bir_id_back: BIR ID back document file (optional)
- business_permit: Business permit document file (optional)
- image_logo: Business logo image file (optional)

**File Requirements:**
- Allowed formats: PNG, JPG, JPEG, GIF, PDF
- Files are uploaded to CDN storage (https://cdn.jamesgalos.shop)
- Old files are automatically deleted when replacing

**Content-Type:** multipart/form-data''')
    @jwt_required()
    def post(self):
        """Upload or update provider documents"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            provider = Provider.query.get(provider_id)
            
            if not provider:
                return {'error': 'Provider not found'}, 404
                
            files = request.files
            uploaded_files = {}
            
            # Handle document uploads
            document_mappings = {
                'bir_id_front': ('provider_bir_front', 'bir_id_front'),
                'bir_id_back': ('provider_bir_back', 'bir_id_back'),
                'business_permit': ('provider_business_permit', 'business_permit'),
                'image_logo': ('provider_logo', 'image_logo')
            }
            
            for file_key, (prefix, db_field) in document_mappings.items():
                if file_key in files and files[file_key].filename != '':
                    # Delete old file if exists
                    old_url = getattr(provider, db_field)
                    if old_url:
                        try:
                            delete_file_from_r2(old_url)
                        except Exception as e:
                            print(f"Warning: Failed to delete old {file_key}: {e}")
                    
                    # Upload new file
                    upload_result = upload_file_to_r2(
                        files[file_key], 
                        'provider-documents',
                        prefix=prefix
                    )
                    if upload_result['success']:
                        setattr(provider, db_field, upload_result['url'])
                        uploaded_files[file_key] = upload_result['url']
                    else:
                        return {'error': f'{file_key} upload failed: {upload_result["error"]}'}, 400
            
            if not uploaded_files:
                return {'error': 'No documents provided for upload'}, 400
            
            db.session.commit()
            
            return {
                'message': f'{len(uploaded_files)} document(s) uploaded successfully',
                'uploaded_files': uploaded_files
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# PROVIDER SERVICES MANAGEMENT
@providers_ns.route('/me/services')
class ProviderServices(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Services retrieved successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.doc(description='''Get all services for the current provider with photos included by default.
    
**Query Parameters:**
- active: Filter by active status (true/false) - optional
- category_id: Filter by specific category ID - optional
- include_photos: Include service photos (true/false, default: true) - optional
- limit: Maximum number of results - optional
- offset: Number of results to skip - optional''')
    @jwt_required()
    def get(self):
        """Get all services for the current provider"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            # Get query parameters
            active_filter = request.args.get('active')
            category_id_filter = request.args.get('category_id')
            include_photos = request.args.get('include_photos', 'true').lower() == 'true'
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', type=int, default=0)
            
            # Build query
            query = db.session.query(ProviderService, ServiceCategory).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).filter(ProviderService.provider_id == provider_id)
            
            # Apply filters
            if active_filter is not None:
                is_active = active_filter.lower() in ('true', '1', 'yes')
                query = query.filter(ProviderService.is_active == is_active)
            
            if category_id_filter is not None:
                try:
                    category_id = int(category_id_filter)
                    query = query.filter(ProviderService.category_id == category_id)
                except ValueError:
                    return {'error': 'Invalid category_id format'}, 400
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            if limit is not None:
                query = query.limit(limit)
            if offset > 0:
                query = query.offset(offset)
            
            results = query.all()
            
            # Prepare services list
            services = []
            for service, category in results:
                service_data = {
                    'id': service.id,
                    'category_id': service.category_id,
                    'category_name': category.category_name,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes,
                    'is_active': service.is_active,
                    'created_at': service.created_at.isoformat() if service.created_at else None,
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None
                }
                
                if include_photos:
                    photos = ProviderServicePhoto.query.filter_by(
                        provider_service_id=service.id
                    ).order_by(ProviderServicePhoto.sort_order).all()
                    
                    service_data['photos'] = [{
                        'id': photo.id,
                        'photo_url': photo.photo_url,
                        'sort_order': photo.sort_order,
                        'created_at': photo.created_at.isoformat() if photo.created_at else None
                    } for photo in photos]
                    service_data['photo_count'] = len(photos)
                    service_data['has_photos'] = len(photos) > 0
                else:
                    # Even if photos aren't included, provide photo count
                    photo_count = ProviderServicePhoto.query.filter_by(provider_service_id=service.id).count()
                    service_data['photo_count'] = photo_count
                    service_data['has_photos'] = photo_count > 0
                
                services.append(service_data)
            
            return {
                'services': services,
                'total': total_count,
                'count': len(services)
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.expect(provider_service_create_model)
    @providers_ns.response(201, 'Service created successfully')
    @providers_ns.response(400, 'Validation Error', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Category not found', error_model)
    @jwt_required()
    def post(self):
        """Create a new service for the current provider"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            data = request.get_json()
            
            # Validation
            required_fields = ['category_id', 'service_title']
            if not all(k in data for k in required_fields):
                return {'error': f'Missing required fields: {", ".join(required_fields)}'}, 400
            
            if len(data['service_title']) > 150:
                return {'error': 'Service title must be 150 characters or less'}, 400
            
            # Check if category exists
            category = ServiceCategory.query.get(data['category_id'])
            if not category:
                return {'error': 'Service category not found'}, 404
            
            # Validate price and duration
            if 'price_decimal' in data and data['price_decimal'] is not None:
                try:
                    price = float(data['price_decimal'])
                    if price < 0:
                        return {'error': 'Price must be non-negative'}, 400
                except (ValueError, TypeError):
                    return {'error': 'Invalid price format'}, 400
            
            if 'duration_minutes' in data and data['duration_minutes'] is not None:
                try:
                    duration = int(data['duration_minutes'])
                    if duration <= 0:
                        return {'error': 'Duration must be positive'}, 400
                except (ValueError, TypeError):
                    return {'error': 'Invalid duration format'}, 400
            
            # Create service
            service = ProviderService(
                provider_id=provider_id,
                category_id=data['category_id'],
                service_title=data['service_title'],
                service_description=data.get('service_description'),
                price_decimal=data.get('price_decimal'),
                duration_minutes=data.get('duration_minutes'),
                is_active=str(data.get('is_active', True)).lower() in ('true', '1', 'yes')
            )
            
            db.session.add(service)
            db.session.commit()
            
            return {
                'message': 'Service created successfully',
                'service': {
                    'id': service.id,
                    'category_id': service.category_id,
                    'category_name': category.category_name,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes,
                    'is_active': service.is_active,
                    'created_at': service.created_at.isoformat() if service.created_at else None,
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None
                }
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@providers_ns.route('/me/services/<int:service_id>')
class ProviderServiceDetail(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Service retrieved successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Service not found', error_model)
    @providers_ns.doc(description='''Get details of a specific service including all photos.
    
**Response includes:**
- Complete service information
- All service photos ordered by sort_order
- Category details
- Photo count and statistics''')
    @jwt_required()
    def get(self, service_id):
        """Get details of a specific service with photos"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            service = db.session.query(ProviderService, ServiceCategory).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).filter(
                ProviderService.id == service_id,
                ProviderService.provider_id == provider_id
            ).first()
            
            if not service:
                return {'error': 'Service not found or access denied'}, 404
            
            service_obj, category = service
            
            # Get photos
            photos = ProviderServicePhoto.query.filter_by(
                provider_service_id=service_id
            ).order_by(ProviderServicePhoto.sort_order).all()
            
            return {
                'id': service_obj.id,
                'category_id': service_obj.category_id,
                'category_name': category.category_name,
                'service_title': service_obj.service_title,
                'service_description': service_obj.service_description,
                'price_decimal': float(service_obj.price_decimal) if service_obj.price_decimal else None,
                'duration_minutes': service_obj.duration_minutes,
                'is_active': service_obj.is_active,
                'created_at': service_obj.created_at.isoformat() if service_obj.created_at else None,
                'updated_at': service_obj.updated_at.isoformat() if service_obj.updated_at else None,
                'photos': [{
                    'id': photo.id,
                    'photo_url': photo.photo_url,
                    'sort_order': photo.sort_order,
                    'created_at': photo.created_at.isoformat() if photo.created_at else None
                } for photo in photos],
                'photo_count': len(photos),
                'has_photos': len(photos) > 0
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.expect(provider_service_create_model)
    @providers_ns.response(200, 'Service updated successfully')
    @providers_ns.response(400, 'Validation Error', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Service not found', error_model)
    @jwt_required()
    def put(self, service_id):
        """Update a specific service"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            service = ProviderService.query.filter_by(
                id=service_id,
                provider_id=provider_id
            ).first()
            
            if not service:
                return {'error': 'Service not found or access denied'}, 404
            
            data = request.get_json()
            
            # Update fields if provided
            if 'category_id' in data:
                category = ServiceCategory.query.get(data['category_id'])
                if not category:
                    return {'error': 'Service category not found'}, 404
                service.category_id = data['category_id']
            
            if 'service_title' in data and data['service_title']:
                if len(data['service_title']) > 150:
                    return {'error': 'Service title must be 150 characters or less'}, 400
                service.service_title = data['service_title']
            
            if 'service_description' in data:
                service.service_description = data['service_description']
            
            if 'price_decimal' in data:
                if data['price_decimal'] is not None:
                    try:
                        price = float(data['price_decimal'])
                        if price < 0:
                            return {'error': 'Price must be non-negative'}, 400
                        service.price_decimal = price
                    except (ValueError, TypeError):
                        return {'error': 'Invalid price format'}, 400
                else:
                    service.price_decimal = None
            
            if 'duration_minutes' in data:
                if data['duration_minutes'] is not None:
                    try:
                        duration = int(data['duration_minutes'])
                        if duration <= 0:
                            return {'error': 'Duration must be positive'}, 400
                        service.duration_minutes = duration
                    except (ValueError, TypeError):
                        return {'error': 'Invalid duration format'}, 400
                else:
                    service.duration_minutes = None
            
            if 'is_active' in data:
                service.is_active = bool(data['is_active'])
            
            db.session.commit()
            
            # Get updated service with category
            updated_service = db.session.query(ProviderService, ServiceCategory).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).filter(ProviderService.id == service_id).first()
            
            service_obj, category = updated_service
            
            return {
                'message': 'Service updated successfully',
                'service': {
                    'id': service_obj.id,
                    'category_id': service_obj.category_id,
                    'category_name': category.category_name,
                    'service_title': service_obj.service_title,
                    'service_description': service_obj.service_description,
                    'price_decimal': float(service_obj.price_decimal) if service_obj.price_decimal else None,
                    'duration_minutes': service_obj.duration_minutes,
                    'is_active': service_obj.is_active,
                    'created_at': service_obj.created_at.isoformat() if service_obj.created_at else None,
                    'updated_at': service_obj.updated_at.isoformat() if service_obj.updated_at else None
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Service deleted successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Service not found', error_model)
    @jwt_required()
    def delete(self, service_id):
        """Delete a specific service and all its photos"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            service = ProviderService.query.filter_by(
                id=service_id,
                provider_id=provider_id
            ).first()
            
            if not service:
                return {'error': 'Service not found or access denied'}, 404
            
            # Get photos to delete from CDN
            photos = ProviderServicePhoto.query.filter_by(provider_service_id=service_id).all()
            photo_urls = [photo.photo_url for photo in photos]
            
            # Delete service (cascade will handle photos)
            db.session.delete(service)
            db.session.commit()
            
            # Delete photos from CDN
            for photo_url in photo_urls:
                try:
                    delete_file_from_r2(photo_url)
                except Exception as e:
                    print(f"Warning: Failed to delete photo {photo_url}: {e}")
            
            return {'message': 'Service and all associated photos deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# SERVICE PHOTOS MANAGEMENT
@providers_ns.route('/me/services/<int:service_id>/photos')
class ProviderServicePhotos(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Photos retrieved successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Service not found', error_model)
    @jwt_required()
    def get(self, service_id):
        """Get all photos for a service"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            # Check if service exists and belongs to provider
            service = ProviderService.query.filter_by(
                id=service_id,
                provider_id=provider_id
            ).first()
            
            if not service:
                return {'error': 'Service not found or access denied'}, 404
            
            # Get photos
            sort_order = request.args.get('sort', 'asc').lower()
            query = ProviderServicePhoto.query.filter_by(provider_service_id=service_id)
            
            if sort_order == 'desc':
                query = query.order_by(ProviderServicePhoto.sort_order.desc())
            else:
                query = query.order_by(ProviderServicePhoto.sort_order.asc())
            
            photos = query.all()
            
            return {
                'photos': [{
                    'id': photo.id,
                    'photo_url': photo.photo_url,
                    'sort_order': photo.sort_order,
                    'created_at': photo.created_at.isoformat() if photo.created_at else None
                } for photo in photos],
                'total': len(photos),
                'service_id': service_id
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@providers_ns.route('/me/services/<int:service_id>/photos/<int:photo_id>')
class ProviderServicePhotoDetail(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Photo updated successfully')
    @providers_ns.response(400, 'Validation Error', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Photo not found', error_model)
    @jwt_required()
    def put(self, service_id, photo_id):
        """Update photo sort order"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            # Check photo ownership
            photo = db.session.query(ProviderServicePhoto).join(
                ProviderService, ProviderServicePhoto.provider_service_id == ProviderService.id
            ).filter(
                ProviderService.provider_id == provider_id,
                ProviderService.id == service_id,
                ProviderServicePhoto.id == photo_id
            ).first()
            
            if not photo:
                return {'error': 'Photo not found or access denied'}, 404
            
            data = request.get_json()
            
            if 'sort_order' in data:
                try:
                    sort_order = int(data['sort_order'])
                    if sort_order < 0:
                        return {'error': 'Sort order must be non-negative'}, 400
                    photo.sort_order = sort_order
                except (ValueError, TypeError):
                    return {'error': 'Invalid sort_order format'}, 400
            
            db.session.commit()
            
            return {
                'message': 'Photo updated successfully',
                'photo': {
                    'id': photo.id,
                    'photo_url': photo.photo_url,
                    'sort_order': photo.sort_order,
                    'created_at': photo.created_at.isoformat() if photo.created_at else None
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Photo deleted successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Photo not found', error_model)
    @jwt_required()
    def delete(self, service_id, photo_id):
        """Delete a specific photo"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            # Check photo ownership
            photo = db.session.query(ProviderServicePhoto).join(
                ProviderService, ProviderServicePhoto.provider_service_id == ProviderService.id
            ).filter(
                ProviderService.provider_id == provider_id,
                ProviderService.id == service_id,
                ProviderServicePhoto.id == photo_id
            ).first()
            
            if not photo:
                return {'error': 'Photo not found or access denied'}, 404
            
            photo_url = photo.photo_url
            
            # Delete from database
            db.session.delete(photo)
            db.session.commit()
            
            # Delete from CDN
            try:
                delete_file_from_r2(photo_url)
            except Exception as e:
                print(f"Warning: Failed to delete file from CDN: {e}")
            
            return {'message': 'Photo deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# PROVIDER CATEGORIES MANAGEMENT
@providers_ns.route('/me/categories')
class ProviderCategories(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Categories retrieved successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @jwt_required()
    def get(self):
        """Get all categories with provider registration status"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            # Get all categories
            categories = ServiceCategory.query.all()
            
            # Get provider's registered categories
            registered_category_ids = set([
                membership.category_id for membership in 
                ProviderCategoryMembership.query.filter_by(provider_id=provider_id).all()
            ])
            
            category_list = []
            for category in categories:
                category_list.append({
                    'id': category.id,
                    'category_name': category.category_name,
                    'description': category.description,
                    'is_registered': category.id in registered_category_ids
                })
            
            return {
                'categories': category_list,
                'total': len(category_list),
                'registered_count': len(registered_category_ids)
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.response(201, 'Categories registered successfully')
    @providers_ns.response(400, 'Validation Error', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Category not found', error_model)
    @providers_ns.doc(description='''Register for categories.
    
**Request Body:**
```json
{
  "category_ids": [1, 2, 3]
}
```''')
    @jwt_required()
    def post(self):
        """Register for multiple categories"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            data = request.get_json()
            
            if 'category_ids' not in data or not isinstance(data['category_ids'], list):
                return {'error': 'category_ids array required'}, 400
            
            category_ids = data['category_ids']
            
            # Check if categories exist
            categories = ServiceCategory.query.filter(ServiceCategory.id.in_(category_ids)).all()
            if len(categories) != len(category_ids):
                found_ids = [cat.id for cat in categories]
                missing_ids = [cid for cid in category_ids if cid not in found_ids]
                return {'error': f'Categories not found: {missing_ids}'}, 404
            
            # Get existing registrations
            existing = ProviderCategoryMembership.query.filter(
                ProviderCategoryMembership.provider_id == provider_id,
                ProviderCategoryMembership.category_id.in_(category_ids)
            ).all()
            existing_ids = [reg.category_id for reg in existing]
            
            # Create new registrations
            new_registrations = 0
            for category_id in category_ids:
                if category_id not in existing_ids:
                    membership = ProviderCategoryMembership(
                        provider_id=provider_id,
                        category_id=category_id
                    )
                    db.session.add(membership)
                    new_registrations += 1
            
            db.session.commit()
            
            return {
                'message': f'Registered for {new_registrations} new categories',
                'new_registrations': new_registrations,
                'already_registered': len(existing_ids)
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@providers_ns.route('/me/categories/<int:category_id>')
class ProviderCategoryDetail(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Category unregistered successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Category registration not found', error_model)
    @jwt_required()
    def delete(self, category_id):
        """Unregister from a category"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403
                
            provider_id = current_identity['user_id']
            
            # Find registration
            membership = ProviderCategoryMembership.query.filter_by(
                provider_id=provider_id,
                category_id=category_id
            ).first()
            
            if not membership:
                return {'error': 'Category registration not found'}, 404
            
            db.session.delete(membership)
            db.session.commit()
            
            return {'message': 'Category unregistered successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@providers_ns.route('/me/categories/registered')
class ProviderRegisteredCategories(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Registered categories retrieved successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.doc(description='''Get only the service categories that the current provider is registered to.

**Returns:**
- List of categories the provider is registered for
- Each category includes: id, category_name, description, created_at, updated_at
- Total count of registered categories''')
    @jwt_required()
    def get(self):
        """Get service categories registered to the current provider"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']

            # Get provider's registered categories with details
            registered_categories = db.session.query(ServiceCategory).join(
                ProviderCategoryMembership,
                ServiceCategory.id == ProviderCategoryMembership.category_id
            ).filter(
                ProviderCategoryMembership.provider_id == provider_id
            ).all()

            category_list = []
            for category in registered_categories:
                category_list.append({
                    'id': category.id,
                    'category_name': category.category_name,
                    'description': category.description,
                    'created_at': category.created_at.isoformat() if category.created_at else None,
                    'updated_at': category.updated_at.isoformat() if category.updated_at else None
                })

            return {
                'registered_categories': category_list,
                'total_registered': len(category_list)
            }, 200

        except Exception as e:
            return {'error': str(e)}, 500

# PUBLIC SERVICES ENDPOINTS (No Authentication Required)
@providers_ns.route('/services')
class PublicServices(Resource):
    @providers_ns.response(200, 'Services retrieved successfully')
    @providers_ns.response(500, 'Internal Server Error', error_model)
    @providers_ns.doc(description='''Get all public services from all providers. No authentication required.
    
**Query Parameters:**
- active: Filter by active status (true/false, default: true) - optional
- category_id: Filter by specific category ID - optional  
- provider_id: Filter by specific provider ID - optional
- search: Search in service titles and descriptions - optional
- min_price: Minimum price filter - optional
- max_price: Maximum price filter - optional
- has_photos: Filter services with photos (true/false) - optional
- limit: Maximum number of results (default: 50, max: 200) - optional
- offset: Number of results to skip for pagination (default: 0) - optional
- sort: Sort order (newest, oldest, price_low, price_high, name_asc, name_desc) - optional

**Examples:**
```
GET /api/providers/services
GET /api/providers/services?category_id=2&active=true
GET /api/providers/services?search=cleaning&min_price=50&max_price=200
GET /api/providers/services?provider_id=1&has_photos=true
GET /api/providers/services?sort=price_low&limit=20&offset=0
```

**Response includes:**
- Service details with photos and schedules
- Provider information (name, business_name)
- Category information
- Photo count and availability
- Schedule information with days and times
- Schedule count and availability''')
    def get(self):
        """Get all public services from all providers"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            # Get query parameters
            active_filter = request.args.get('active', 'true').lower() == 'true'
            category_id_filter = request.args.get('category_id', type=int)
            provider_id_filter = request.args.get('provider_id', type=int)
            search = request.args.get('search', '').strip()
            min_price = request.args.get('min_price', type=float)
            max_price = request.args.get('max_price', type=float)
            has_photos_filter = request.args.get('has_photos')
            limit = min(request.args.get('limit', 50, type=int), 200)  # Max 200
            offset = request.args.get('offset', 0, type=int)
            sort = request.args.get('sort', 'newest')
            
            # Build query with joins
            query = db.session.query(
                ProviderService, 
                ServiceCategory, 
                Provider
            ).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).join(
                Provider, ProviderService.provider_id == Provider.id
            ).filter(
                Provider.is_active == True  # Only active providers
            )
            
            # Apply filters
            if active_filter is not None:
                query = query.filter(ProviderService.is_active == active_filter)
            
            if category_id_filter is not None:
                query = query.filter(ProviderService.category_id == category_id_filter)
                
            if provider_id_filter is not None:
                query = query.filter(ProviderService.provider_id == provider_id_filter)
            
            if search:
                search_term = f'%{search}%'
                query = query.filter(
                    db.or_(
                        ProviderService.service_title.ilike(search_term),
                        ProviderService.service_description.ilike(search_term),
                        Provider.business_name.ilike(search_term),
                        Provider.full_name.ilike(search_term)
                    )
                )
            
            if min_price is not None:
                query = query.filter(ProviderService.price_decimal >= min_price)
                
            if max_price is not None:
                query = query.filter(ProviderService.price_decimal <= max_price)
            
            # Apply sorting
            if sort == 'newest':
                query = query.order_by(ProviderService.created_at.desc())
            elif sort == 'oldest':
                query = query.order_by(ProviderService.created_at.asc())
            elif sort == 'price_low':
                query = query.order_by(ProviderService.price_decimal.asc().nullslast())
            elif sort == 'price_high':
                query = query.order_by(ProviderService.price_decimal.desc().nullsfirst())
            elif sort == 'name_asc':
                query = query.order_by(ProviderService.service_title.asc())
            elif sort == 'name_desc':
                query = query.order_by(ProviderService.service_title.desc())
            else:
                query = query.order_by(ProviderService.created_at.desc())
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            results = query.all()
            
            # Prepare services list
            services = []
            for service, category, provider in results:
                # Get photos for each service
                photos = ProviderServicePhoto.query.filter_by(
                    provider_service_id=service.id
                ).order_by(ProviderServicePhoto.sort_order).all()
                
                # Get schedule for each service
                schedules = ProviderServiceSchedule.query.filter_by(
                    provider_service_id=service.id
                ).order_by(
                    db.case(
                        (ProviderServiceSchedule.schedule_day == 'Monday', 1),
                        (ProviderServiceSchedule.schedule_day == 'Tuesday', 2),
                        (ProviderServiceSchedule.schedule_day == 'Wednesday', 3),
                        (ProviderServiceSchedule.schedule_day == 'Thursday', 4),
                        (ProviderServiceSchedule.schedule_day == 'Friday', 5),
                        (ProviderServiceSchedule.schedule_day == 'Saturday', 6),
                        (ProviderServiceSchedule.schedule_day == 'Sunday', 7),
                        else_=8
                    )
                ).all()
                
                # Apply has_photos filter if specified
                if has_photos_filter is not None:
                    has_photos = has_photos_filter.lower() == 'true'
                    if (has_photos and len(photos) == 0) or (not has_photos and len(photos) > 0):
                        continue
                
                service_data = {
                    'id': service.id,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes,
                    'is_active': service.is_active,
                    'created_at': service.created_at.isoformat() if service.created_at else None,
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None,
                    'category': {
                        'id': category.id,
                        'category_name': category.category_name,
                        'description': category.description
                    },
                    'provider': {
                        'id': provider.id,
                        'business_name': provider.business_name,
                        'full_name': provider.full_name,
                        'address': provider.address,
                        'about': provider.about,
                        'image_logo': provider.image_logo
                    },
                    'photos': [{
                        'id': photo.id,
                        'photo_url': photo.photo_url,
                        'sort_order': photo.sort_order,
                        'created_at': photo.created_at.isoformat() if photo.created_at else None
                    } for photo in photos],
                    'photo_count': len(photos),
                    'has_photos': len(photos) > 0,
                    'schedules': [{
                        'id': schedule.id,
                        'schedule_day': schedule.schedule_day,
                        'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                        'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                        'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
                        'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None
                    } for schedule in schedules],
                    'schedule_count': len(schedules),
                    'has_schedule': len(schedules) > 0
                }
                
                services.append(service_data)
            
            return {
                'services': services,
                'total': total_count,
                'count': len(services),
                'limit': limit,
                'offset': offset,
                'has_more': total_count > (offset + len(services))
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@providers_ns.route('/services/<int:service_id>')
class PublicServiceDetail(Resource):
    @providers_ns.response(200, 'Service and related provider services retrieved successfully')
    @providers_ns.response(404, 'Service not found', error_model)
    @providers_ns.response(500, 'Internal Server Error', error_model)
    @providers_ns.doc(description='''Get details of a specific service and all provider_services from the same provider. No authentication required.
    
**Response includes:**
- Main service information with photos and schedules
- All provider_services from the same provider based on provider_id match
- Provider details (business info, contact)
- Category information for each service
- Complete provider_services table data structure''')
    def get(self, service_id):
        """Get public details of a specific service and all related provider services"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            # Get the main service with provider and category info
            main_service_result = db.session.query(
                ProviderService, 
                ServiceCategory, 
                Provider
            ).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).join(
                Provider, ProviderService.provider_id == Provider.id
            ).filter(
                ProviderService.id == service_id,
                ProviderService.is_active == True,
                Provider.is_active == True
            ).first()
            
            if not main_service_result:
                return {'error': 'Service not found or not available'}, 404
            
            main_service, main_category, provider = main_service_result
            
            # Get photos for main service
            main_photos = ProviderServicePhoto.query.filter_by(
                provider_service_id=service_id
            ).order_by(ProviderServicePhoto.sort_order).all()
            
            # Get schedule for main service
            main_schedules = ProviderServiceSchedule.query.filter_by(
                provider_service_id=service_id
            ).order_by(
                db.case(
                    (ProviderServiceSchedule.schedule_day == 'Monday', 1),
                    (ProviderServiceSchedule.schedule_day == 'Tuesday', 2),
                    (ProviderServiceSchedule.schedule_day == 'Wednesday', 3),
                    (ProviderServiceSchedule.schedule_day == 'Thursday', 4),
                    (ProviderServiceSchedule.schedule_day == 'Friday', 5),
                    (ProviderServiceSchedule.schedule_day == 'Saturday', 6),
                    (ProviderServiceSchedule.schedule_day == 'Sunday', 7),
                    else_=8
                )
            ).all()
            
            # Get ALL provider_services from same provider using provider_id match
            all_provider_services = db.session.query(
                ProviderService, 
                ServiceCategory
            ).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).filter(
                ProviderService.provider_id == provider.id,
                ProviderService.is_active == True
            ).order_by(ProviderService.created_at.desc()).all()
            
            # Build provider_services array with complete table data
            provider_services_list = []
            for service, category in all_provider_services:
                # Get photos for each service
                service_photos = ProviderServicePhoto.query.filter_by(
                    provider_service_id=service.id
                ).order_by(ProviderServicePhoto.sort_order).all()
                
                # Get schedules for each service
                service_schedules = ProviderServiceSchedule.query.filter_by(
                    provider_service_id=service.id
                ).order_by(
                    db.case(
                        (ProviderServiceSchedule.schedule_day == 'Monday', 1),
                        (ProviderServiceSchedule.schedule_day == 'Tuesday', 2),
                        (ProviderServiceSchedule.schedule_day == 'Wednesday', 3),
                        (ProviderServiceSchedule.schedule_day == 'Thursday', 4),
                        (ProviderServiceSchedule.schedule_day == 'Friday', 5),
                        (ProviderServiceSchedule.schedule_day == 'Saturday', 6),
                        (ProviderServiceSchedule.schedule_day == 'Sunday', 7),
                        else_=8
                    )
                ).all()
                
                # Complete provider_services table structure
                service_data = {
                    # Direct provider_services table fields
                    'id': service.id,                                    # int, PRI, auto_increment
                    'provider_id': service.provider_id,                  # int, MUL
                    'category_id': service.category_id,                  # int, MUL  
                    'service_title': service.service_title,              # varchar(150)
                    'service_description': service.service_description,  # text
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,  # decimal(10,2)
                    'duration_minutes': service.duration_minutes,        # int
                    'is_active': service.is_active,                      # tinyint(1), MUL, default 1
                    'created_at': service.created_at.isoformat() if service.created_at else None,      # timestamp, CURRENT_TIMESTAMP
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None,      # timestamp, on update CURRENT_TIMESTAMP
                    
                    # Associated category data
                    'category': {
                        'id': category.id,
                        'category_name': category.category_name,
                        'description': category.description
                    },
                    
                    # Complete provider_service_photos table structure
                    'provider_service_photos': [{
                        # Direct provider_service_photos table fields
                        'id': photo.id,                                          # int, PRI, auto_increment
                        'provider_service_id': photo.provider_service_id,        # int, MUL
                        'photo_url': photo.photo_url,                            # varchar(255)
                        'sort_order': photo.sort_order,                          # int, MUL, default 0
                        'created_at': photo.created_at.isoformat() if photo.created_at else None  # timestamp, CURRENT_TIMESTAMP
                    } for photo in service_photos],
                    'photo_count': len(service_photos),
                    'has_photos': len(service_photos) > 0,
                    
                    # Associated schedules data  
                    'schedules': [{
                        'id': schedule.id,
                        'schedule_day': schedule.schedule_day,
                        'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                        'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                        'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
                        'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None
                    } for schedule in service_schedules],
                    'schedule_count': len(service_schedules),
                    'has_schedule': len(service_schedules) > 0
                }
                
                provider_services_list.append(service_data)
            
            # Main response structure
            response = {
                # Main service details (the requested service)
                'main_service': {
                    'id': main_service.id,
                    'provider_id': main_service.provider_id,
                    'category_id': main_service.category_id,
                    'service_title': main_service.service_title,
                    'service_description': main_service.service_description,
                    'price_decimal': float(main_service.price_decimal) if main_service.price_decimal else None,
                    'duration_minutes': main_service.duration_minutes,
                    'is_active': main_service.is_active,
                    'created_at': main_service.created_at.isoformat() if main_service.created_at else None,
                    'updated_at': main_service.updated_at.isoformat() if main_service.updated_at else None,
                    'category': {
                        'id': main_category.id,
                        'category_name': main_category.category_name,
                        'description': main_category.description
                    },
                    'provider_service_photos': [{
                        # Direct provider_service_photos table fields
                        'id': photo.id,                                          # int, PRI, auto_increment
                        'provider_service_id': photo.provider_service_id,        # int, MUL
                        'photo_url': photo.photo_url,                            # varchar(255)
                        'sort_order': photo.sort_order,                          # int, MUL, default 0
                        'created_at': photo.created_at.isoformat() if photo.created_at else None  # timestamp, CURRENT_TIMESTAMP
                    } for photo in main_photos],
                    'photo_count': len(main_photos),
                    'has_photos': len(main_photos) > 0,
                    'schedules': [{
                        'id': schedule.id,
                        'schedule_day': schedule.schedule_day,
                        'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                        'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                        'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
                        'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None
                    } for schedule in main_schedules],
                    'schedule_count': len(main_schedules),
                    'has_schedule': len(main_schedules) > 0
                },
                
                # Provider information
                'provider': {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'address': provider.address,
                    'about': provider.about,
                    'email': provider.email,
                    'image_logo': provider.image_logo
                },
                
                # All provider_services from same provider (using provider_id match)
                'provider_services': provider_services_list,
                'provider_services_count': len(provider_services_list),
                
                # Meta information
                'requested_service_id': service_id,
                'provider_id': provider.id
            }
            
            return response, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@providers_ns.route('/<int:provider_id>/services')
class ProviderPublicServices(Resource):
    @providers_ns.response(200, 'Provider services retrieved successfully')
    @providers_ns.response(404, 'Provider not found', error_model)
    @providers_ns.response(500, 'Internal Server Error', error_model)
    @providers_ns.doc(description='''Get all public services from a specific provider. No authentication required.
    
**Path Parameters:**
- provider_id: ID of the provider

**Query Parameters:**
- active: Filter by active status (true/false, default: true) - optional
- category_id: Filter by specific category ID - optional
- limit: Maximum number of results (default: 50) - optional
- offset: Number of results to skip for pagination (default: 0) - optional

**Response includes:**
- Provider information
- All provider services with photos
- Service statistics''')
    def get(self, provider_id):
        """Get all public services from a specific provider"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            # Check if provider exists and is active
            provider = Provider.query.filter_by(id=provider_id, is_active=True).first()
            if not provider:
                return {'error': 'Provider not found or not active'}, 404
            
            # Get query parameters
            active_filter = request.args.get('active', 'true').lower() == 'true'
            category_id_filter = request.args.get('category_id', type=int)
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # Build query
            query = db.session.query(ProviderService, ServiceCategory).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).filter(ProviderService.provider_id == provider_id)
            
            # Apply filters
            if active_filter is not None:
                query = query.filter(ProviderService.is_active == active_filter)
            
            if category_id_filter is not None:
                query = query.filter(ProviderService.category_id == category_id_filter)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination and get results
            query = query.order_by(ProviderService.created_at.desc())
            query = query.limit(limit).offset(offset)
            results = query.all()
            
            # Prepare services list
            services = []
            for service, category in results:
                # Get photos
                photos = ProviderServicePhoto.query.filter_by(
                    provider_service_id=service.id
                ).order_by(ProviderServicePhoto.sort_order).all()
                
                service_data = {
                    'id': service.id,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes,
                    'is_active': service.is_active,
                    'created_at': service.created_at.isoformat() if service.created_at else None,
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None,
                    'category': {
                        'id': category.id,
                        'category_name': category.category_name,
                        'description': category.description
                    },
                    'photos': [{
                        'id': photo.id,
                        'photo_url': photo.photo_url,
                        'sort_order': photo.sort_order,
                        'created_at': photo.created_at.isoformat() if photo.created_at else None
                    } for photo in photos],
                    'photo_count': len(photos),
                    'has_photos': len(photos) > 0
                }
                
                services.append(service_data)
            
            return {
                'provider': {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'address': provider.address,
                    'about': provider.about,
                    'email': provider.email,
                    'image_logo': provider.image_logo
                },
                'services': services,
                'total': total_count,
                'count': len(services),
                'limit': limit,
                'offset': offset,
                'has_more': total_count > (offset + len(services))
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# NEW PUBLIC ENDPOINT TO GET ALL PROVIDERS
@providers_ns.route('')
class PublicProvidersList(Resource):
    @providers_ns.response(200, 'Providers retrieved successfully')
    @providers_ns.response(500, 'Internal Server Error', error_model)
    @providers_ns.doc(description='''Get all active providers. No authentication required.
    
**Query Parameters:**
- active: Filter by active status (true/false, default: true) - optional
- limit: Maximum number of results (default: 50, max: 200) - optional
- offset: Number of results to skip for pagination (default: 0) - optional
- search: Search in business name, full name, or address - optional

**Examples:**
```
GET /api/providers
GET /api/providers?active=true&limit=20
GET /api/providers?search=cleaning&offset=10
```

**Response includes:**
- Complete provider information (excluding sensitive data like password_hash)
- Provider documents URLs (BIR IDs, business permit, logo)
- Business details and contact information
- Account status and timestamps

**Note:** This endpoint only returns active providers by default and excludes sensitive information like password hashes.''')
    def get(self):
        """Get all public providers"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            # Get query parameters
            active_filter = request.args.get('active', 'true').lower() == 'true'
            limit = min(request.args.get('limit', 50, type=int), 200)  # Max 200
            offset = request.args.get('offset', 0, type=int)
            search = request.args.get('search', '').strip()
            
            # Build query
            query = Provider.query
            
            # Apply active filter
            if active_filter is not None:
                query = query.filter(Provider.is_active == active_filter)
            
            # Apply search filter
            if search:
                search_term = f'%{search}%'
                query = query.filter(
                    db.or_(
                        Provider.business_name.ilike(search_term),
                        Provider.full_name.ilike(search_term),
                        Provider.address.ilike(search_term),
                        Provider.about.ilike(search_term)
                    )
                )
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination and ordering
            query = query.order_by(Provider.created_at.desc())
            query = query.limit(limit).offset(offset)
            providers = query.all()
            
            # Prepare providers list (excluding sensitive information)
            provider_list = []
            for provider in providers:
                provider_data = {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'address': provider.address,
                    'bir_id_front': provider.bir_id_front,
                    'bir_id_back': provider.bir_id_back,
                    'business_permit': provider.business_permit,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'created_at': provider.created_at.isoformat() if provider.created_at else None,
                    'updated_at': provider.updated_at.isoformat() if provider.updated_at else None
                }
                provider_list.append(provider_data)
            
            return {
                'providers': provider_list,
                'total': total_count,
                'count': len(provider_list),
                'limit': limit,
                'offset': offset,
                'has_more': total_count > (offset + len(provider_list))
            }, 200

        except Exception as e:
            return {'error': str(e)}, 500

# ADMIN PROVIDER SERVICES MANAGEMENT
@providers_ns.route('/me/adminprovider/services')
class AdminProviderServices(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Services retrieved successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.doc(description='''Get all services for the current provider (Admin view with full details).

**Query Parameters:**
- active: Filter by active status (true/false) - optional
- category_id: Filter by specific category ID - optional
- include_photos: Include service photos (true/false, default: true) - optional
- include_schedules: Include service schedules (true/false, default: true) - optional
- limit: Maximum number of results - optional
- offset: Number of results to skip - optional''')
    @jwt_required()
    def get(self):
        """Get all services for the current provider (Admin view)"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']

            # Get query parameters
            active_filter = request.args.get('active')
            category_id_filter = request.args.get('category_id')
            include_photos = request.args.get('include_photos', 'true').lower() == 'true'
            include_schedules = request.args.get('include_schedules', 'true').lower() == 'true'
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', type=int, default=0)

            # Build query
            query = db.session.query(ProviderService, ServiceCategory).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).filter(ProviderService.provider_id == provider_id)

            # Apply filters
            if active_filter is not None:
                is_active = active_filter.lower() in ('true', '1', 'yes')
                query = query.filter(ProviderService.is_active == is_active)

            if category_id_filter is not None:
                try:
                    category_id = int(category_id_filter)
                    query = query.filter(ProviderService.category_id == category_id)
                except ValueError:
                    return {'error': 'Invalid category_id format'}, 400

            # Get total count
            total_count = query.count()

            # Apply pagination
            if limit is not None:
                query = query.limit(limit)
            if offset > 0:
                query = query.offset(offset)

            results = query.all()

            # Prepare services list
            services = []
            for service, category in results:
                service_data = {
                    'id': service.id,
                    'provider_id': service.provider_id,
                    'category_id': service.category_id,
                    'category_name': category.category_name,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes,
                    'is_active': service.is_active,
                    'created_at': service.created_at.isoformat() if service.created_at else None,
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None
                }

                if include_photos:
                    photos = ProviderServicePhoto.query.filter_by(
                        provider_service_id=service.id
                    ).order_by(ProviderServicePhoto.sort_order).all()

                    service_data['photos'] = [{
                        'id': photo.id,
                        'provider_service_id': photo.provider_service_id,
                        'photo_url': photo.photo_url,
                        'sort_order': photo.sort_order,
                        'created_at': photo.created_at.isoformat() if photo.created_at else None
                    } for photo in photos]
                    service_data['photo_count'] = len(photos)
                    service_data['has_photos'] = len(photos) > 0

                if include_schedules:
                    schedules = ProviderServiceSchedule.query.filter_by(
                        provider_service_id=service.id
                    ).order_by(
                        db.case(
                            (ProviderServiceSchedule.schedule_day == 'Monday', 1),
                            (ProviderServiceSchedule.schedule_day == 'Tuesday', 2),
                            (ProviderServiceSchedule.schedule_day == 'Wednesday', 3),
                            (ProviderServiceSchedule.schedule_day == 'Thursday', 4),
                            (ProviderServiceSchedule.schedule_day == 'Friday', 5),
                            (ProviderServiceSchedule.schedule_day == 'Saturday', 6),
                            (ProviderServiceSchedule.schedule_day == 'Sunday', 7),
                            else_=8
                        )
                    ).all()

                    service_data['schedules'] = [{
                        'id': schedule.id,
                        'provider_service_id': schedule.provider_service_id,
                        'schedule_day': schedule.schedule_day,
                        'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                        'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                        'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
                        'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None
                    } for schedule in schedules]
                    service_data['schedule_count'] = len(schedules)
                    service_data['has_schedules'] = len(schedules) > 0

                services.append(service_data)

            return {
                'services': services,
                'total': total_count,
                'count': len(services)
            }, 200

        except Exception as e:
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.expect(admin_provider_service_create_model)
    @providers_ns.response(201, 'Service created successfully')
    @providers_ns.response(400, 'Validation Error', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Category not found', error_model)
    @providers_ns.doc(description='''Create a new service with optional photo upload and schedules.

**Supports both JSON and multipart/form-data requests**

**For JSON requests:**
- Content-Type: application/json
- Use standard service fields

**For multipart/form-data requests:**
- Content-Type: multipart/form-data
- Service fields: category_id, service_title, service_description, price_decimal, duration_minutes, is_active
- Photo upload: photos (multiple files supported)
- Schedule data: schedules (JSON string with schedule array)

**Photo Upload:**
- Field name: photos (supports multiple files)
- Allowed formats: PNG, JPG, JPEG, GIF
- Files uploaded to R2 storage with auto-generated sort order

**Schedule Format (JSON string):**
```json
[
  {
    "schedule_day": "Monday",
    "start_time": "09:00",
    "end_time": "17:00"
  },
  {
    "schedule_day": "Tuesday",
    "start_time": "09:00",
    "end_time": "17:00"
  }
]
```

**Examples:**

JSON Request:
```json
POST /api/providers/me/adminprovider/services
{
  "category_id": 1,
  "service_title": "House Cleaning",
  "service_description": "Professional house cleaning service",
  "price_decimal": 150.00,
  "duration_minutes": 120,
  "is_active": true
}
```

Multipart Request:
```
POST /api/providers/me/adminprovider/services
Content-Type: multipart/form-data

category_id=1
service_title=House Cleaning
service_description=Professional house cleaning service
price_decimal=150.00
duration_minutes=120
is_active=true
photos=<file1>
photos=<file2>
schedules=[{"schedule_day":"Monday","start_time":"09:00","end_time":"17:00"}]
```''')
    @jwt_required()
    def post(self):
        """Create a new service with optional photo upload and schedules"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']

            # Determine content type and parse data accordingly
            content_type = request.content_type or ''
            is_multipart = content_type.startswith('multipart/form-data')

            if is_multipart:
                # Handle multipart/form-data request
                data = request.form.to_dict()
                files = request.files.getlist('photos') if 'photos' in request.files else []
            else:
                # Handle JSON request
                data = request.get_json() or {}
                files = []

            # Validation
            required_fields = ['category_id', 'service_title']
            if not all(k in data for k in required_fields):
                return {'error': f'Missing required fields: {", ".join(required_fields)}'}, 400

            if len(data['service_title']) > 150:
                return {'error': 'Service title must be 150 characters or less'}, 400

            # Check if category exists
            category = ServiceCategory.query.get(data['category_id'])
            if not category:
                return {'error': 'Service category not found'}, 404

            # Validate price and duration
            if 'price_decimal' in data and data['price_decimal'] is not None:
                try:
                    price = float(data['price_decimal'])
                    if price < 0:
                        return {'error': 'Price must be non-negative'}, 400
                except (ValueError, TypeError):
                    return {'error': 'Invalid price format'}, 400

            if 'duration_minutes' in data and data['duration_minutes'] is not None:
                try:
                    duration = int(data['duration_minutes'])
                    if duration <= 0:
                        return {'error': 'Duration must be positive'}, 400
                except (ValueError, TypeError):
                    return {'error': 'Invalid duration format'}, 400

            # Create service
            service = ProviderService(
                provider_id=provider_id,
                category_id=data['category_id'],
                service_title=data['service_title'],
                service_description=data.get('service_description'),
                price_decimal=data.get('price_decimal'),
                duration_minutes=data.get('duration_minutes'),
                is_active=str(data.get('is_active', True)).lower() in ('true', '1', 'yes')
            )

            db.session.add(service)
            db.session.flush()  # Get service ID

            # Handle photo uploads if provided
            uploaded_photos = []
            if files:
                for i, file in enumerate(files):
                    if file.filename != '':
                        # Upload file to R2
                        upload_result = upload_file_to_r2(
                            file,
                            'provider-service-photos',
                            prefix='service_photo',
                            service_id=service.id
                        )

                        if upload_result['success']:
                            # Create photo record
                            service_photo = ProviderServicePhoto(
                                provider_service_id=service.id,
                                photo_url=upload_result['url'],
                                sort_order=i
                            )
                            db.session.add(service_photo)
                            uploaded_photos.append({
                                'photo_url': upload_result['url'],
                                'sort_order': i
                            })

            # Handle schedules if provided
            created_schedules = []
            if 'schedules' in data and data['schedules']:
                try:
                    import json
                    schedules_data = json.loads(data['schedules']) if isinstance(data['schedules'], str) else data['schedules']

                    for schedule_data in schedules_data:
                        # Validate schedule data
                        if not all(k in schedule_data for k in ['schedule_day', 'start_time', 'end_time']):
                            return {'error': 'Invalid schedule format - missing required fields'}, 400

                        # Validate day
                        valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        if schedule_data['schedule_day'] not in valid_days:
                            return {'error': f'Invalid schedule_day: {schedule_data["schedule_day"]}'}, 400

                        # Validate time format
                        from datetime import datetime
                        try:
                            start_time = datetime.strptime(schedule_data['start_time'], '%H:%M').time()
                            end_time = datetime.strptime(schedule_data['end_time'], '%H:%M').time()
                        except ValueError:
                            return {'error': 'Invalid time format - use HH:MM'}, 400

                        schedule = ProviderServiceSchedule(
                            provider_service_id=service.id,
                            schedule_day=schedule_data['schedule_day'],
                            start_time=start_time,
                            end_time=end_time
                        )
                        db.session.add(schedule)
                        created_schedules.append({
                            'schedule_day': schedule_data['schedule_day'],
                            'start_time': schedule_data['start_time'],
                            'end_time': schedule_data['end_time']
                        })

                except (json.JSONDecodeError, ValueError) as e:
                    return {'error': f'Invalid schedules format: {str(e)}'}, 400

            db.session.commit()

            response = {
                'message': 'Service created successfully',
                'service': {
                    'id': service.id,
                    'provider_id': service.provider_id,
                    'category_id': service.category_id,
                    'category_name': category.category_name,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes,
                    'is_active': service.is_active,
                    'created_at': service.created_at.isoformat() if service.created_at else None,
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None,
                    'photos': uploaded_photos,
                    'schedules': created_schedules
                }
            }

            if uploaded_photos:
                response['photos_uploaded'] = len(uploaded_photos)
            if created_schedules:
                response['schedules_created'] = len(created_schedules)

            return response, 201

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@providers_ns.route('/me/adminprovider/services/<int:service_id>')
class AdminProviderServiceDetail(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Service retrieved successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Service not found', error_model)
    @providers_ns.doc(description='''Get details of a specific service with all related data.

**Response includes:**
- Complete service information from provider_services table
- All service photos from provider_service_photos table
- All service schedules from provider_service_schedule table
- Category details
- Photo and schedule counts''')
    @jwt_required()
    def get(self, service_id):
        """Get details of a specific service (Admin view)"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']

            # Get service with category
            service = db.session.query(ProviderService, ServiceCategory).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).filter(
                ProviderService.id == service_id,
                ProviderService.provider_id == provider_id
            ).first()

            if not service:
                return {'error': 'Service not found or access denied'}, 404

            service_obj, category = service

            # Get photos
            photos = ProviderServicePhoto.query.filter_by(
                provider_service_id=service_id
            ).order_by(ProviderServicePhoto.sort_order).all()

            # Get schedules
            schedules = ProviderServiceSchedule.query.filter_by(
                provider_service_id=service_id
            ).order_by(
                db.case(
                    (ProviderServiceSchedule.schedule_day == 'Monday', 1),
                    (ProviderServiceSchedule.schedule_day == 'Tuesday', 2),
                    (ProviderServiceSchedule.schedule_day == 'Wednesday', 3),
                    (ProviderServiceSchedule.schedule_day == 'Thursday', 4),
                    (ProviderServiceSchedule.schedule_day == 'Friday', 5),
                    (ProviderServiceSchedule.schedule_day == 'Saturday', 6),
                    (ProviderServiceSchedule.schedule_day == 'Sunday', 7),
                    else_=8
                )
            ).all()

            return {
                'id': service_obj.id,
                'provider_id': service_obj.provider_id,
                'category_id': service_obj.category_id,
                'category_name': category.category_name,
                'service_title': service_obj.service_title,
                'service_description': service_obj.service_description,
                'price_decimal': float(service_obj.price_decimal) if service_obj.price_decimal else None,
                'duration_minutes': service_obj.duration_minutes,
                'is_active': service_obj.is_active,
                'created_at': service_obj.created_at.isoformat() if service_obj.created_at else None,
                'updated_at': service_obj.updated_at.isoformat() if service_obj.updated_at else None,
                'photos': [{
                    'id': photo.id,
                    'provider_service_id': photo.provider_service_id,
                    'photo_url': photo.photo_url,
                    'sort_order': photo.sort_order,
                    'created_at': photo.created_at.isoformat() if photo.created_at else None
                } for photo in photos],
                'photo_count': len(photos),
                'has_photos': len(photos) > 0,
                'schedules': [{
                    'id': schedule.id,
                    'provider_service_id': schedule.provider_service_id,
                    'schedule_day': schedule.schedule_day,
                    'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                    'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                    'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
                    'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None
                } for schedule in schedules],
                'schedule_count': len(schedules),
                'has_schedules': len(schedules) > 0
            }, 200

        except Exception as e:
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.expect(admin_provider_service_update_model)
    @providers_ns.response(200, 'Service updated successfully')
    @providers_ns.response(400, 'Validation Error', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Service not found', error_model)
    @providers_ns.doc(description='''Update a service with optional photo upload and schedule management.

**Supports both JSON and multipart/form-data requests**

**For JSON requests:**
- Content-Type: application/json
- Use standard service fields

**For multipart/form-data requests:**
- Content-Type: multipart/form-data
- Service fields: category_id, service_title, service_description, price_decimal, duration_minutes, is_active
- Photo upload: photos (multiple files supported) - appends to existing photos
- Schedule data: schedules (JSON string with schedule array) - replaces ALL existing schedules

**Photo Addition:**
- When photos are uploaded, they are added to existing photos (no deletion)
- Field name: photos (supports multiple files)
- Allowed formats: PNG, JPG, JPEG, GIF
- Files uploaded to R2 storage with continued sort order from existing photos

**Schedule Replacement:**
- When schedules are provided, ALL existing schedules are deleted and replaced
- Schedule Format (JSON string): Same as create endpoint

**Examples:**

JSON Update:
```json
PUT /api/providers/me/adminprovider/services/1
{
  "service_title": "Updated House Cleaning",
  "price_decimal": 175.00,
  "is_active": false
}
```

Multipart Update with New Photos:
```
PUT /api/providers/me/adminprovider/services/1
Content-Type: multipart/form-data

service_title=Updated House Cleaning
price_decimal=175.00
photos=<new_file1>
photos=<new_file2>
schedules=[{"schedule_day":"Monday","start_time":"10:00","end_time":"18:00"}]
```''')
    @jwt_required()
    def put(self, service_id):
        """Update a service with optional photo upload and schedule management"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']

            # Get service
            service = ProviderService.query.filter_by(
                id=service_id,
                provider_id=provider_id
            ).first()

            if not service:
                return {'error': 'Service not found or access denied'}, 404

            # Determine content type and parse data accordingly
            content_type = request.content_type or ''
            is_multipart = content_type.startswith('multipart/form-data')

            if is_multipart:
                # Handle multipart/form-data request
                data = request.form.to_dict()
                files = request.files.getlist('photos') if 'photos' in request.files else []
            else:
                # Handle JSON request
                data = request.get_json() or {}
                files = []

            # Update fields if provided
            if 'category_id' in data:
                category = ServiceCategory.query.get(data['category_id'])
                if not category:
                    return {'error': 'Service category not found'}, 404
                service.category_id = data['category_id']

            if 'service_title' in data and data['service_title']:
                if len(data['service_title']) > 150:
                    return {'error': 'Service title must be 150 characters or less'}, 400
                service.service_title = data['service_title']

            if 'service_description' in data:
                service.service_description = data['service_description']

            if 'price_decimal' in data:
                if data['price_decimal'] is not None:
                    try:
                        price = float(data['price_decimal'])
                        if price < 0:
                            return {'error': 'Price must be non-negative'}, 400
                        service.price_decimal = price
                    except (ValueError, TypeError):
                        return {'error': 'Invalid price format'}, 400
                else:
                    service.price_decimal = None

            if 'duration_minutes' in data:
                if data['duration_minutes'] is not None:
                    try:
                        duration = int(data['duration_minutes'])
                        if duration <= 0:
                            return {'error': 'Duration must be positive'}, 400
                        service.duration_minutes = duration
                    except (ValueError, TypeError):
                        return {'error': 'Invalid duration format'}, 400
                else:
                    service.duration_minutes = None

            if 'is_active' in data:
                service.is_active = bool(data['is_active'])

            # Handle photo addition if files provided
            uploaded_photos = []
            if files:
                # Get existing photos count to continue sort order
                existing_photos_count = ProviderServicePhoto.query.filter_by(provider_service_id=service_id).count()

                # Upload new photos (append to existing ones)
                for i, file in enumerate(files):
                    if file.filename != '':
                        # Upload file to R2
                        upload_result = upload_file_to_r2(
                            file,
                            'provider-service-photos',
                            prefix='service_photo',
                            service_id=service_id
                        )

                        if upload_result['success']:
                            # Create photo record with continued sort order
                            service_photo = ProviderServicePhoto(
                                provider_service_id=service_id,
                                photo_url=upload_result['url'],
                                sort_order=existing_photos_count + i
                            )
                            db.session.add(service_photo)
                            uploaded_photos.append({
                                'photo_url': upload_result['url'],
                                'sort_order': existing_photos_count + i
                            })

            # Handle schedule replacement if provided
            updated_schedules = []
            if 'schedules' in data and data['schedules']:
                try:
                    import json
                    schedules_data = json.loads(data['schedules']) if isinstance(data['schedules'], str) else data['schedules']

                    # Delete existing schedules
                    existing_schedules = ProviderServiceSchedule.query.filter_by(provider_service_id=service_id).all()
                    for schedule in existing_schedules:
                        db.session.delete(schedule)

                    # Create new schedules
                    for schedule_data in schedules_data:
                        # Validate schedule data
                        if not all(k in schedule_data for k in ['schedule_day', 'start_time', 'end_time']):
                            return {'error': 'Invalid schedule format - missing required fields'}, 400

                        # Validate day
                        valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        if schedule_data['schedule_day'] not in valid_days:
                            return {'error': f'Invalid schedule_day: {schedule_data["schedule_day"]}'}, 400

                        # Validate time format
                        from datetime import datetime
                        try:
                            start_time = datetime.strptime(schedule_data['start_time'], '%H:%M').time()
                            end_time = datetime.strptime(schedule_data['end_time'], '%H:%M').time()
                        except ValueError:
                            return {'error': 'Invalid time format - use HH:MM'}, 400

                        schedule = ProviderServiceSchedule(
                            provider_service_id=service_id,
                            schedule_day=schedule_data['schedule_day'],
                            start_time=start_time,
                            end_time=end_time
                        )
                        db.session.add(schedule)
                        updated_schedules.append({
                            'schedule_day': schedule_data['schedule_day'],
                            'start_time': schedule_data['start_time'],
                            'end_time': schedule_data['end_time']
                        })

                except (json.JSONDecodeError, ValueError) as e:
                    return {'error': f'Invalid schedules format: {str(e)}'}, 400

            db.session.commit()

            # Get updated service with category
            updated_service = db.session.query(ProviderService, ServiceCategory).join(
                ServiceCategory, ProviderService.category_id == ServiceCategory.id
            ).filter(ProviderService.id == service_id).first()

            service_obj, category = updated_service

            response = {
                'message': 'Service updated successfully',
                'service': {
                    'id': service_obj.id,
                    'provider_id': service_obj.provider_id,
                    'category_id': service_obj.category_id,
                    'category_name': category.category_name,
                    'service_title': service_obj.service_title,
                    'service_description': service_obj.service_description,
                    'price_decimal': float(service_obj.price_decimal) if service_obj.price_decimal else None,
                    'duration_minutes': service_obj.duration_minutes,
                    'is_active': service_obj.is_active,
                    'created_at': service_obj.created_at.isoformat() if service_obj.created_at else None,
                    'updated_at': service_obj.updated_at.isoformat() if service_obj.updated_at else None
                }
            }

            if uploaded_photos:
                response['photos_updated'] = len(uploaded_photos)
                response['service']['photos'] = uploaded_photos
            if updated_schedules:
                response['schedules_updated'] = len(updated_schedules)
                response['service']['schedules'] = updated_schedules

            return response, 200

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.response(200, 'Service deleted successfully')
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Service not found', error_model)
    @providers_ns.doc(description='''Delete a service and all related data.

**This operation will:**
- Delete the service record from provider_services table
- Delete all associated photos from provider_service_photos table
- Delete all associated schedules from provider_service_schedule table
- Remove all photo files from R2 storage
- This action cannot be undone

**Response:**
- Success message with deletion statistics
- Count of deleted photos and schedules''')
    @jwt_required()
    def delete(self, service_id):
        """Delete a service and all its related data"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']

            # Get service
            service = ProviderService.query.filter_by(
                id=service_id,
                provider_id=provider_id
            ).first()

            if not service:
                return {'error': 'Service not found or access denied'}, 404

            # Get photos to delete from R2 storage
            photos = ProviderServicePhoto.query.filter_by(provider_service_id=service_id).all()
            photo_count = len(photos)
            photo_urls = [photo.photo_url for photo in photos]

            # Get schedules count
            schedules = ProviderServiceSchedule.query.filter_by(provider_service_id=service_id).all()
            schedule_count = len(schedules)

            # Delete service (cascade will handle related records)
            db.session.delete(service)
            db.session.commit()

            # Delete photos from R2 storage
            deleted_files_count = 0
            for photo_url in photo_urls:
                try:
                    delete_file_from_r2(photo_url)
                    deleted_files_count += 1
                except Exception as e:
                    print(f"Warning: Failed to delete photo {photo_url}: {e}")

            return {
                'message': 'Service and all associated data deleted successfully',
                'deleted_data': {
                    'service_id': service_id,
                    'photos_deleted': photo_count,
                    'schedules_deleted': schedule_count,
                    'files_deleted_from_storage': deleted_files_count
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# PROVIDER BOOKINGS MANAGEMENT
@providers_ns.route('/me/provider/mybookings')
class ProviderBookings(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.marshal_list_with(service_booking_response_model, code=200)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @jwt_required()
    def get(self):
        """Get all bookings for the current provider"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']

            # Query bookings for this provider with joins to get user, service, and payment details
            bookings = db.session.query(
                ServiceBooking,
                User.full_name.label('user_name'),
                User.email.label('user_email'),
                ProviderService.service_title,
                ProviderService.price_decimal,
                PaymentStatus.status.label('payment_status'),
                PaymentStatus.description.label('payment_description'),
                PaymentStatus.created_at.label('payment_created_at'),
                PaymentStatus.updated_at.label('payment_updated_at')
            ).join(
                User, ServiceBooking.user_id == User.id
            ).join(
                ProviderService, ServiceBooking.provider_service_id == ProviderService.id
            ).outerjoin(
                PaymentStatus, ServiceBooking.id == PaymentStatus.booking_id
            ).filter(
                ServiceBooking.provider_id == provider_id
            ).order_by(ServiceBooking.created_at.desc()).all()

            booking_list = []
            for booking, user_name, user_email, service_title, price_decimal, payment_status, payment_description, payment_created_at, payment_updated_at in bookings:
                booking_data = {
                    'id': booking.id,
                    'user_id': booking.user_id,
                    'user_name': user_name,
                    'user_email': user_email,
                    'provider_id': booking.provider_id,
                    'provider_service_id': booking.provider_service_id,
                    'service_title': service_title,
                    'price_decimal': float(price_decimal) if price_decimal else None,
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d'),
                    'booking_day': booking.booking_day,
                    'booking_time': booking.booking_time.strftime('%H:%M:%S'),
                    'status': booking.status,
                    'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': booking.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'payment_status': payment_status,
                    'payment_description': payment_description,
                    'payment_created_at': payment_created_at.strftime('%Y-%m-%d %H:%M:%S') if payment_created_at else None,
                    'payment_updated_at': payment_updated_at.strftime('%Y-%m-%d %H:%M:%S') if payment_updated_at else None
                }
                booking_list.append(booking_data)

            return booking_list, 200

        except Exception as e:
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.expect(service_booking_create_model)
    @providers_ns.marshal_with(service_booking_response_model, code=201)
    @providers_ns.response(400, 'Bad request', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Service not found', error_model)
    @jwt_required()
    def post(self):
        """Create a new booking for the provider"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']
            data = request.get_json()

            # Validate required fields
            required_fields = ['user_id', 'provider_service_id', 'booking_date', 'booking_day', 'booking_time']
            for field in required_fields:
                if field not in data or not data[field]:
                    return {'error': f'Missing required field: {field}'}, 400

            # Verify the service belongs to this provider
            service = ProviderService.query.filter_by(
                id=data['provider_service_id'],
                provider_id=provider_id
            ).first()

            if not service:
                return {'error': 'Service not found or access denied'}, 404

            # Verify user exists
            user = User.query.filter_by(id=data['user_id']).first()
            if not user:
                return {'error': 'User not found'}, 404

            # Parse date and time
            from datetime import datetime, date, time
            try:
                booking_date = datetime.strptime(data['booking_date'], '%Y-%m-%d').date()
                booking_time = datetime.strptime(data['booking_time'], '%H:%M').time()
            except ValueError:
                return {'error': 'Invalid date or time format'}, 400

            # Create new booking
            new_booking = ServiceBooking(
                user_id=data['user_id'],
                provider_id=provider_id,
                provider_service_id=data['provider_service_id'],
                booking_date=booking_date,
                booking_day=data['booking_day'],
                booking_time=booking_time,
                status=data.get('status', 'Pending')
            )

            db.session.add(new_booking)
            db.session.commit()

            # Return the created booking with user and service details
            booking_response = {
                'id': new_booking.id,
                'user_id': new_booking.user_id,
                'user_name': user.full_name,
                'user_email': user.email,
                'provider_id': new_booking.provider_id,
                'provider_service_id': new_booking.provider_service_id,
                'service_title': service.service_title,
                'booking_date': new_booking.booking_date.strftime('%Y-%m-%d'),
                'booking_day': new_booking.booking_day,
                'booking_time': new_booking.booking_time.strftime('%H:%M:%S'),
                'status': new_booking.status,
                'created_at': new_booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': new_booking.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }

            return booking_response, 201

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@providers_ns.route('/me/provider/mybookings/<int:booking_id>')
class ProviderBookingDetail(Resource):
    @providers_ns.doc(security='Bearer')
    @providers_ns.marshal_with(service_booking_response_model, code=200)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Booking not found', error_model)
    @jwt_required()
    def get(self, booking_id):
        """Get a specific booking by ID"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']

            # Query booking with user, service, and payment details
            booking_data = db.session.query(
                ServiceBooking,
                User.full_name.label('user_name'),
                User.email.label('user_email'),
                ProviderService.service_title,
                ProviderService.price_decimal,
                PaymentStatus.status.label('payment_status'),
                PaymentStatus.description.label('payment_description'),
                PaymentStatus.created_at.label('payment_created_at'),
                PaymentStatus.updated_at.label('payment_updated_at')
            ).join(
                User, ServiceBooking.user_id == User.id
            ).join(
                ProviderService, ServiceBooking.provider_service_id == ProviderService.id
            ).outerjoin(
                PaymentStatus, ServiceBooking.id == PaymentStatus.booking_id
            ).filter(
                ServiceBooking.id == booking_id,
                ServiceBooking.provider_id == provider_id
            ).first()

            if not booking_data:
                return {'error': 'Booking not found or access denied'}, 404

            booking, user_name, user_email, service_title, price_decimal, payment_status, payment_description, payment_created_at, payment_updated_at = booking_data

            booking_response = {
                'id': booking.id,
                'user_id': booking.user_id,
                'user_name': user_name,
                'user_email': user_email,
                'provider_id': booking.provider_id,
                'provider_service_id': booking.provider_service_id,
                'service_title': service_title,
                'price_decimal': float(price_decimal) if price_decimal else None,
                'booking_date': booking.booking_date.strftime('%Y-%m-%d'),
                'booking_day': booking.booking_day,
                'booking_time': booking.booking_time.strftime('%H:%M:%S'),
                'status': booking.status,
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': booking.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_status': payment_status,
                'payment_description': payment_description,
                'payment_created_at': payment_created_at.strftime('%Y-%m-%d %H:%M:%S') if payment_created_at else None,
                'payment_updated_at': payment_updated_at.strftime('%Y-%m-%d %H:%M:%S') if payment_updated_at else None
            }

            return booking_response, 200

        except Exception as e:
            return {'error': str(e)}, 500

    @providers_ns.doc(security='Bearer')
    @providers_ns.expect(service_booking_update_model)
    @providers_ns.marshal_with(service_booking_response_model, code=200)
    @providers_ns.response(400, 'Bad request', error_model)
    @providers_ns.response(401, 'Unauthorized', error_model)
    @providers_ns.response(403, 'Access denied - provider account required', error_model)
    @providers_ns.response(404, 'Booking not found', error_model)
    @jwt_required()
    def put(self, booking_id):
        """Update a specific booking"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            if user_type != 'provider':
                return {'error': 'Access denied - provider account required'}, 403

            provider_id = current_identity['user_id']
            data = request.get_json()

            # Find the booking
            booking = ServiceBooking.query.filter_by(
                id=booking_id,
                provider_id=provider_id
            ).first()

            if not booking:
                return {'error': 'Booking not found or access denied'}, 404

            # Update fields if provided
            if 'booking_date' in data:
                try:
                    from datetime import datetime
                    booking.booking_date = datetime.strptime(data['booking_date'], '%Y-%m-%d').date()
                except ValueError:
                    return {'error': 'Invalid date format'}, 400

            if 'booking_day' in data:
                booking.booking_day = data['booking_day']

            if 'booking_time' in data:
                try:
                    from datetime import datetime
                    booking.booking_time = datetime.strptime(data['booking_time'], '%H:%M').time()
                except ValueError:
                    return {'error': 'Invalid time format'}, 400

            if 'status' in data:
                booking.status = data['status']

            db.session.commit()

            # Get user and service details for response
            user = User.query.filter_by(id=booking.user_id).first()
            service = ProviderService.query.filter_by(id=booking.provider_service_id).first()

            booking_response = {
                'id': booking.id,
                'user_id': booking.user_id,
                'user_name': user.full_name,
                'user_email': user.email,
                'provider_id': booking.provider_id,
                'provider_service_id': booking.provider_service_id,
                'service_title': service.service_title,
                'booking_date': booking.booking_date.strftime('%Y-%m-%d'),
                'booking_day': booking.booking_day,
                'booking_time': booking.booking_time.strftime('%H:%M:%S'),
                'status': booking.status,
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': booking.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }

            return booking_response, 200

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500