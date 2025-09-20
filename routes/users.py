from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import OperationalError
from werkzeug.datastructures import FileStorage
from utils.upload import upload_file_to_r2, delete_file_from_r2
import re

try:
    from models import db, User, UserServiceCategory, ServiceCategory, Provider, ProviderService, ProviderServiceSchedule, ServiceBooking, PaymentStatus
    DB_AVAILABLE = True
except Exception as e:
    print(f"Database models not available: {e}")
    DB_AVAILABLE = False

users_ns = Namespace('users', description='User management operations')

# API Models for documentation
user_update_model = users_ns.model('UserUpdate', {
    'full_name': fields.String(description='Full name of the user'),
    'address': fields.String(description='User address'),
    'password': fields.String(description='New password (minimum 6 characters)'),
    'id_front': fields.String(description='Front ID document URL (for JSON requests) or file (for multipart requests)'),
    'id_back': fields.String(description='Back ID document URL (for JSON requests) or file (for multipart requests)')
})

user_response_model = users_ns.model('UserResponse', {
    'id': fields.Integer(description='User ID'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email address'),
    'address': fields.String(description='Address'),
    'id_front': fields.String(description='Front ID document URL'),
    'id_back': fields.String(description='Back ID document URL'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp')
})

user_update_success_model = users_ns.model('UserUpdateSuccess', {
    'message': fields.String(description='Success message'),
    'user': fields.Nested(user_response_model)
})

error_model = users_ns.model('Error', {
    'error': fields.String(description='Error message')
})

# User Service Models
user_service_model = users_ns.model('UserService', {
    'id': fields.Integer(description='Service ID'),
    'category_id': fields.Integer(description='Category ID'),
    'category_name': fields.String(description='Category name'),
    'service_title': fields.String(description='Service title'),
    'service_description': fields.String(description='Service description'),
    'price_decimal': fields.Float(description='Service price'),
    'is_active': fields.Boolean(description='Service active status'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp')
})

user_services_response_model = users_ns.model('UserServicesResponse', {
    'services': fields.List(fields.Nested(user_service_model), description='List of user services'),
    'total': fields.Integer(description='Total number of services'),
    'active_count': fields.Integer(description='Number of active services'),
    'inactive_count': fields.Integer(description='Number of inactive services')
})

# User Booking Models
user_booking_model = users_ns.model('UserBooking', {
    'id': fields.Integer(description='Booking ID'),
    'booking_date': fields.String(description='Booking date (YYYY-MM-DD)'),
    'booking_day': fields.String(description='Day of the week'),
    'booking_time': fields.String(description='Booking time (HH:MM)'),
    'status': fields.String(description='Booking status', enum=['Pending', 'Confirmed', 'Completed', 'Cancelled']),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp'),
    'provider': fields.Raw(description='Provider information'),
    'service': fields.Raw(description='Service information'),
    'payment_status': fields.Raw(description='Payment status information')
})

user_bookings_response_model = users_ns.model('UserBookingsResponse', {
    'bookings': fields.List(fields.Nested(user_booking_model), description='List of user bookings'),
    'total': fields.Integer(description='Total number of bookings'),
    'pending_count': fields.Integer(description='Number of pending bookings'),
    'confirmed_count': fields.Integer(description='Number of confirmed bookings'),
    'completed_count': fields.Integer(description='Number of completed bookings'),
    'cancelled_count': fields.Integer(description='Number of cancelled bookings')
})

booking_status_update_model = users_ns.model('BookingStatusUpdate', {
    'booking_id': fields.Integer(required=True, description='Booking ID to update'),
    'status': fields.String(required=True, description='New booking status', enum=['Pending', 'Confirmed', 'Completed', 'Cancelled'])
})

booking_status_update_response_model = users_ns.model('BookingStatusUpdateResponse', {
    'message': fields.String(description='Success message'),
    'booking': fields.Nested(user_booking_model, description='Updated booking details')
})

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@users_ns.route('/me')
class UserProfile(Resource):
    @users_ns.doc(security='Bearer')
    @users_ns.marshal_with(user_response_model, code=200)
    @users_ns.response(401, 'Unauthorized', error_model)
    @users_ns.response(403, 'Access denied - user account required', error_model)
    @users_ns.response(404, 'User not found', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def get(self):
        """Get current user profile details"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            # Only allow users (not providers) to access this endpoint
            if user_type != 'user':
                return {'error': 'Access denied - user account required'}, 403
                
            user_id = current_identity['user_id']
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
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

    @users_ns.doc(security='Bearer')
    @users_ns.expect(user_update_model)
    @users_ns.marshal_with(user_update_success_model, code=200)
    @users_ns.response(400, 'Validation Error', error_model)
    @users_ns.response(401, 'Unauthorized', error_model)
    @users_ns.response(403, 'Access denied - user account required', error_model)
    @users_ns.response(404, 'User not found', error_model)
    @users_ns.response(409, 'Email already exists', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Update current user profile with optional file upload support.

**Supports both JSON and multipart/form-data requests**

**For JSON requests:**
- Content-Type: application/json
- Use URLs for document fields (id_front, id_back)

**For multipart/form-data requests:**
- Content-Type: multipart/form-data
- Upload actual files for documents
- Supports image upload for ID documents

**Fields:**
- full_name: User's complete name (optional)
- address: Complete residential address (optional)
- password: New password, minimum 6 characters (optional)
- id_front: Front ID document URL (JSON) or file (multipart) (optional)
- id_back: Back ID document URL (JSON) or file (multipart) (optional)

**JSON Sample Payload:**
```json
{
  "full_name": "John Michael Doe",
  "address": "123 Main Street, Barangay San Miguel, Quezon City, Metro Manila 1100, Philippines",
  "password": "NewPassword123!",
  "id_front": "https://cdn.jamesgalos.shop/user-documents/new_id_front.jpg",
  "id_back": "https://cdn.jamesgalos.shop/user-documents/new_id_back.jpg"
}
```

**File Upload Requirements (for multipart requests):**
- Allowed formats: PNG, JPG, JPEG, GIF, PDF
- Files are uploaded to CDN storage automatically
- Old files are replaced and deleted from storage
- Returns updated URLs in response''')
    @jwt_required()
    def put(self):
        """Update current user profile with optional file upload support"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            # Only allow users (not providers) to access this endpoint
            if user_type != 'user':
                return {'error': 'Access denied - user account required'}, 403

            user_id = current_identity['user_id']
            user = User.query.get(user_id)

            if not user:
                return {'error': 'User not found'}, 404

            # Determine content type and parse data accordingly
            content_type = request.content_type or ''
            is_multipart = content_type.startswith('multipart/form-data')

            if is_multipart:
                # Handle multipart/form-data request
                data = request.form.to_dict()
                files = request.files
            else:
                # Handle JSON request
                data = request.get_json() or {}
                files = {}

            # Handle file uploads if multipart request
            uploaded_files = {}

            if is_multipart:
                # Handle ID front upload
                if 'id_front' in files and files['id_front'].filename != '':
                    # Delete old file if exists
                    if user.id_front:
                        try:
                            delete_file_from_r2(user.id_front)
                        except Exception as e:
                            print(f"Warning: Failed to delete old id_front: {e}")

                    # Upload new file
                    upload_result = upload_file_to_r2(
                        files['id_front'],
                        'user-documents',
                        prefix='user_id_front'
                    )
                    if upload_result['success']:
                        user.id_front = upload_result['url']
                        uploaded_files['id_front'] = upload_result['url']
                    else:
                        return {'error': f'ID front upload failed: {upload_result["error"]}'}, 400

                # Handle ID back upload
                if 'id_back' in files and files['id_back'].filename != '':
                    # Delete old file if exists
                    if user.id_back:
                        try:
                            delete_file_from_r2(user.id_back)
                        except Exception as e:
                            print(f"Warning: Failed to delete old id_back: {e}")

                    # Upload new file
                    upload_result = upload_file_to_r2(
                        files['id_back'],
                        'user-documents',
                        prefix='user_id_back'
                    )
                    if upload_result['success']:
                        user.id_back = upload_result['url']
                        uploaded_files['id_back'] = upload_result['url']
                    else:
                        return {'error': f'ID back upload failed: {upload_result["error"]}'}, 400

            # Update fields if provided
            if 'full_name' in data and data['full_name']:
                user.full_name = data['full_name']

            if 'address' in data and data['address']:
                user.address = data['address']

            # Handle ID document URLs for JSON requests
            if not is_multipart:
                if 'id_front' in data and data['id_front']:
                    user.id_front = data['id_front']

                if 'id_back' in data and data['id_back']:
                    user.id_back = data['id_back']

            if 'password' in data and data['password']:
                if len(data['password']) < 6:
                    return {'error': 'Password must be at least 6 characters'}, 400
                user.set_password(data['password'])

            db.session.commit()
            
            # Prepare response
            response_data = {
                'message': 'User profile updated successfully',
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'id_front': user.id_front,
                    'id_back': user.id_back,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                }
            }

            # Include upload info for multipart requests
            if uploaded_files:
                response_data['uploaded_files'] = uploaded_files
                response_data['message'] += f' with {len(uploaded_files)} file(s) uploaded'

            return response_data, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @users_ns.doc(security='Bearer')
    @users_ns.response(200, 'User account deleted successfully')
    @users_ns.response(401, 'Unauthorized', error_model)
    @users_ns.response(403, 'Access denied - user account required', error_model)
    @users_ns.response(404, 'User not found', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def delete(self):
        """Delete current user account"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            # Only allow users (not providers) to access this endpoint
            if user_type != 'user':
                return {'error': 'Access denied - user account required'}, 403
                
            user_id = current_identity['user_id']
            user = User.query.get(user_id)
            
            if not user:
                return {'error': 'User not found'}, 404
            
            # Delete associated files from R2 storage
            files_to_delete = []
            if user.id_front:
                files_to_delete.append(user.id_front)
            if user.id_back:
                files_to_delete.append(user.id_back)
            
            # Delete user from database
            db.session.delete(user)
            db.session.commit()
            
            # Delete files from storage (do this after DB commit to avoid inconsistency)
            for file_url in files_to_delete:
                try:
                    delete_file_from_r2(file_url)
                except Exception as e:
                    print(f"Warning: Failed to delete file {file_url}: {e}")
            
            return {'message': 'User account deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

@users_ns.route('/me/services')
class UserServices(Resource):
    @users_ns.doc(security='Bearer')
    @users_ns.marshal_with(user_services_response_model, code=200)
    @users_ns.response(401, 'Unauthorized', error_model)
    @users_ns.response(403, 'Access denied - user account required', error_model)
    @users_ns.response(404, 'User not found', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Get all services registered by the current user.
    
**Query Parameters:**
- active: Filter by active status (true/false) - optional
- category_id: Filter by specific category ID - optional
- limit: Maximum number of results to return (default: all) - optional
- offset: Number of results to skip for pagination (default: 0) - optional

**Examples:**
```
GET /users/me/services
GET /users/me/services?active=true
GET /users/me/services?category_id=2
GET /users/me/services?active=true&category_id=2&limit=10&offset=0
```

**Response includes:**
- List of all user services with category details
- Total count of services
- Count of active and inactive services
- Service pricing and description information''')
    @jwt_required()
    def get(self):
        """Get all services registered by the current user"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            # Only allow users (not providers) to access this endpoint
            if user_type != 'user':
                return {'error': 'Access denied - user account required'}, 403
                
            user_id = current_identity['user_id']
            user = User.query.get(user_id)
            
            if not user:
                return {'error': 'User not found'}, 404
            
            # Get query parameters for filtering
            active_filter = request.args.get('active')
            category_id_filter = request.args.get('category_id')
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', type=int, default=0)
            
            # Build query with joins
            query = db.session.query(UserServiceCategory, ServiceCategory).join(
                ServiceCategory, UserServiceCategory.category_id == ServiceCategory.id
            ).filter(UserServiceCategory.user_id == user_id)
            
            # Apply filters
            if active_filter is not None:
                is_active = active_filter.lower() in ('true', '1', 'yes')
                query = query.filter(UserServiceCategory.is_active == is_active)
            
            if category_id_filter is not None:
                try:
                    category_id = int(category_id_filter)
                    query = query.filter(UserServiceCategory.category_id == category_id)
                except ValueError:
                    return {'error': 'Invalid category_id format'}, 400
            
            # Get total count before applying limit/offset
            total_count = query.count()
            
            # Apply pagination
            if limit is not None:
                query = query.limit(limit)
            if offset > 0:
                query = query.offset(offset)
            
            # Execute query
            results = query.all()
            
            # Prepare service list
            services = []
            active_count = 0
            inactive_count = 0
            
            for user_service, category in results:
                service_data = {
                    'id': user_service.id,
                    'category_id': user_service.category_id,
                    'category_name': category.category_name,
                    'service_title': user_service.service_title,
                    'service_description': user_service.service_description,
                    'price_decimal': float(user_service.price_decimal) if user_service.price_decimal else None,
                    'is_active': user_service.is_active,
                    'created_at': user_service.created_at.isoformat() if user_service.created_at else None,
                    'updated_at': user_service.updated_at.isoformat() if user_service.updated_at else None
                }
                services.append(service_data)
                
                if user_service.is_active:
                    active_count += 1
                else:
                    inactive_count += 1
            
            # If no filters were applied, get actual counts from all user services
            if active_filter is None and category_id_filter is None:
                all_services_query = UserServiceCategory.query.filter_by(user_id=user_id)
                active_count = all_services_query.filter_by(is_active=True).count()
                inactive_count = all_services_query.filter_by(is_active=False).count()
            
            return {
                'services': services,
                'total': total_count,
                'active_count': active_count,
                'inactive_count': inactive_count
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@users_ns.route('/me/upload-documents')
class UserDocumentUpload(Resource):
    @users_ns.doc(security='Bearer')
    @users_ns.response(200, 'Documents uploaded successfully')
    @users_ns.response(400, 'Validation Error', error_model)
    @users_ns.response(401, 'Unauthorized', error_model)
    @users_ns.response(403, 'Access denied - user account required', error_model)
    @users_ns.response(404, 'User not found', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Upload or update user documents.
    
**Form Data Fields:**
- id_front: Front ID document file (optional)
- id_back: Back ID document file (optional)

**File Requirements:**
- Allowed formats: PNG, JPG, JPEG, GIF, PDF
- Files are uploaded to CDN storage (https://cdn.jamesgalos.shop)
- Old files are automatically deleted when replacing

**Content-Type:** multipart/form-data

**Example using curl:**
```bash
curl -X POST /users/me/upload-documents \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -F "id_front=@new_id_front.jpg" \\
  -F "id_back=@new_id_back.jpg"
```

**Response includes:**
- Success message
- Updated document URLs''')
    @jwt_required()
    def post(self):
        """Upload or update user ID documents"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            
            # Only allow users (not providers) to access this endpoint
            if user_type != 'user':
                return {'error': 'Access denied - user account required'}, 403
                
            user_id = current_identity['user_id']
            user = User.query.get(user_id)
            
            if not user:
                return {'error': 'User not found'}, 404
                
            files = request.files
            uploaded_files = {}
            
            # Handle ID front upload
            if 'id_front' in files and files['id_front'].filename != '':
                # Delete old file if exists
                if user.id_front:
                    try:
                        delete_file_from_r2(user.id_front)
                    except Exception as e:
                        print(f"Warning: Failed to delete old id_front: {e}")
                
                # Upload new file
                upload_result = upload_file_to_r2(
                    files['id_front'], 
                    'user-documents',
                    prefix='user_id_front'
                )
                if upload_result['success']:
                    user.id_front = upload_result['url']
                    uploaded_files['id_front'] = upload_result['url']
                else:
                    return {'error': f'ID front upload failed: {upload_result["error"]}'}, 400
            
            # Handle ID back upload
            if 'id_back' in files and files['id_back'].filename != '':
                # Delete old file if exists
                if user.id_back:
                    try:
                        delete_file_from_r2(user.id_back)
                    except Exception as e:
                        print(f"Warning: Failed to delete old id_back: {e}")
                
                # Upload new file
                upload_result = upload_file_to_r2(
                    files['id_back'], 
                    'user-documents',
                    prefix='user_id_back'
                )
                if upload_result['success']:
                    user.id_back = upload_result['url']
                    uploaded_files['id_back'] = upload_result['url']
                else:
                    return {'error': f'ID back upload failed: {upload_result["error"]}'}, 400
            
            if not uploaded_files:
                return {'error': 'No documents provided for upload'}, 400
            
            db.session.commit()
            
            return {
                'message': f'{len(uploaded_files)} document(s) uploaded successfully',
                'uploaded_files': uploaded_files,
                'user': {
                    'id': user.id,
                    'id_front': user.id_front,
                    'id_back': user.id_back
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()

@users_ns.route('/me/bookings')
class UserBookings(Resource):
    @users_ns.doc(security='Bearer')
    @users_ns.marshal_with(user_bookings_response_model, code=200)
    @users_ns.response(401, 'Unauthorized', error_model)
    @users_ns.response(403, 'Access denied - user account required', error_model)
    @users_ns.response(404, 'User not found', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Get all bookings made by the current user.

**Query Parameters:**
- status: Filter by booking status (Pending/Confirmed/Completed/Cancelled) - optional
- start_date: Start date filter (YYYY-MM-DD format) - optional
- end_date: End date filter (YYYY-MM-DD format) - optional
- provider_id: Filter by specific provider ID - optional
- limit: Maximum number of results to return (default: all) - optional
- offset: Number of results to skip for pagination (default: 0) - optional

**Examples:**
```
GET /users/me/bookings
GET /users/me/bookings?status=Confirmed
GET /users/me/bookings?start_date=2024-01-01&end_date=2024-01-31
GET /users/me/bookings?provider_id=5&status=Pending
```

**Response includes:**
- List of user bookings with complete details
- Provider information (name, contact, address)
- Service information (title, description, price, duration)
- Payment status if available
- Total count and status-wise counts''')
    @jwt_required()
    def get(self):
        """Get all bookings made by the current user"""
        print("=== /me/bookings GET endpoint called ===")

        if not DB_AVAILABLE:
            print("Database not available")
            return {'error': 'Database connection not available'}, 503

        try:
            print("Getting JWT identity...")
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            print(f"User type: {user_type}")

            # Only allow users (not providers) to access this endpoint
            if user_type != 'user':
                print(f"Access denied for user_type: {user_type}")
                return {'error': 'Access denied - user account required'}, 403

            user_id = current_identity['user_id']
            print(f"User ID: {user_id}")

            user = User.query.get(user_id)
            print(f"User found: {user.full_name if user else 'None'}")

            if not user:
                print("User not found in database")
                return {'error': 'User not found'}, 404

            # Get query parameters for filtering
            status_filter = request.args.get('status')
            start_date_filter = request.args.get('start_date')
            end_date_filter = request.args.get('end_date')
            provider_id_filter = request.args.get('provider_id', type=int)
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', type=int, default=0)

            print(f"Query parameters: status={status_filter}, start_date={start_date_filter}, end_date={end_date_filter}, provider_id={provider_id_filter}, limit={limit}, offset={offset}")

            # Check if ServiceBooking model is available
            try:
                print("Testing ServiceBooking model access...")
                test_query = ServiceBooking.query.first()
                print(f"ServiceBooking model accessible, test query result: {test_query}")
            except Exception as model_error:
                print(f"ServiceBooking model error: {str(model_error)}")
                raise model_error

            # Build query
            print("Building query...")
            query = ServiceBooking.query.filter_by(user_id=user_id)
            print("Base query created successfully")

            # Apply filters
            if status_filter:
                valid_statuses = ['Pending', 'Confirmed', 'Completed', 'Cancelled']
                if status_filter not in valid_statuses:
                    return {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, 400
                query = query.filter(ServiceBooking.status == status_filter)

            if start_date_filter:
                try:
                    from datetime import datetime
                    start_dt = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
                    query = query.filter(ServiceBooking.booking_date >= start_dt)
                except ValueError:
                    return {'error': 'Invalid start_date format. Use YYYY-MM-DD'}, 400

            if end_date_filter:
                try:
                    from datetime import datetime
                    end_dt = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
                    query = query.filter(ServiceBooking.booking_date <= end_dt)
                except ValueError:
                    return {'error': 'Invalid end_date format. Use YYYY-MM-DD'}, 400

            if provider_id_filter:
                query = query.filter(ServiceBooking.provider_id == provider_id_filter)

            # Get total count before applying limit/offset
            total_count = query.count()

            # Apply ordering BEFORE pagination (SQLAlchemy requirement)
            print("Applying ordering...")
            query = query.order_by(ServiceBooking.booking_date.desc())

            # Apply pagination AFTER ordering
            if limit:
                print(f"Applying limit: {limit}")
                query = query.limit(limit)
            if offset > 0:
                print(f"Applying offset: {offset}")
                query = query.offset(offset)

            # Execute final query
            print("Executing final query...")
            bookings = query.all()
            print(f"Found {len(bookings)} bookings")

            # Prepare booking list with full details
            booking_list = []
            status_counts = {'Pending': 0, 'Confirmed': 0, 'Completed': 0, 'Cancelled': 0}

            print("Processing bookings...")
            for i, booking in enumerate(bookings):
                print(f"Processing booking {i+1}/{len(bookings)}: ID {booking.id}")

                # Get related data
                try:
                    print(f"Getting provider for booking {booking.id}, provider_id: {booking.provider_id}")
                    provider = Provider.query.get(booking.provider_id)
                    print(f"Provider found: {provider.full_name if provider else 'None'}")
                except Exception as e:
                    print(f"Error getting provider: {str(e)}")
                    provider = None

                try:
                    print(f"Getting provider_service for booking {booking.id}, provider_service_id: {booking.provider_service_id}")
                    provider_service = ProviderService.query.get(booking.provider_service_id)
                    print(f"Provider service found: {provider_service.service_title if provider_service else 'None'}")
                except Exception as e:
                    print(f"Error getting provider_service: {str(e)}")
                    provider_service = None

                try:
                    service_category = ServiceCategory.query.get(provider_service.category_id) if provider_service else None
                    print(f"Service category found: {service_category.category_name if service_category else 'None'}")
                except Exception as e:
                    print(f"Error getting service_category: {str(e)}")
                    service_category = None

                try:
                    payment_status = PaymentStatus.query.filter_by(booking_id=booking.id).first()
                    print(f"Payment status found: {payment_status.status if payment_status else 'None'}")
                except Exception as e:
                    print(f"Error getting payment_status: {str(e)}")
                    payment_status = None

                booking_data = {
                    'id': booking.id,
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else None,
                    'booking_day': booking.booking_day,
                    'booking_time': booking.booking_time.strftime('%H:%M') if booking.booking_time else None,
                    'status': booking.status,
                    'created_at': booking.created_at.isoformat() if booking.created_at else None,
                    'updated_at': booking.updated_at.isoformat() if booking.updated_at else None,
                    'provider': {
                        'id': provider.id,
                        'business_name': provider.business_name,
                        'full_name': provider.full_name,
                        'email': provider.email,
                        'contact_number': provider.contact_number,
                        'address': provider.address,
                        'about': provider.about,
                        'is_active': provider.is_active
                    } if provider else None,
                    'service': {
                        'id': provider_service.id,
                        'service_title': provider_service.service_title,
                        'service_description': provider_service.service_description,
                        'price_decimal': float(provider_service.price_decimal) if provider_service.price_decimal else None,
                        'duration_minutes': provider_service.duration_minutes,
                        'category': {
                            'id': service_category.id,
                            'category_name': service_category.category_name,
                            'description': service_category.description
                        } if service_category else None
                    } if provider_service else None,
                    'payment_status': {
                        'id': payment_status.id,
                        'status': payment_status.status,
                        'description': payment_status.description,
                        'created_at': payment_status.created_at.isoformat() if payment_status.created_at else None
                    } if payment_status else None
                }

                booking_list.append(booking_data)
                status_counts[booking.status] += 1

            print("Preparing final response...")
            final_response = {
                'bookings': booking_list,
                'total': total_count,
                'pending_count': status_counts['Pending'],
                'confirmed_count': status_counts['Confirmed'],
                'completed_count': status_counts['Completed'],
                'cancelled_count': status_counts['Cancelled']
            }
            print(f"Returning response with {len(booking_list)} bookings")
            return final_response, 200

        except Exception as e:
            print(f"=== ERROR in /me/bookings GET endpoint ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print("Full traceback:")
            traceback.print_exc()
            print("=== END ERROR LOG ===")
            return {'error': str(e)}, 500

    @users_ns.doc(security='Bearer')
    @users_ns.expect(booking_status_update_model)
    @users_ns.marshal_with(booking_status_update_response_model, code=200)
    @users_ns.response(400, 'Validation Error', error_model)
    @users_ns.response(401, 'Unauthorized', error_model)
    @users_ns.response(403, 'Access denied - user account required', error_model)
    @users_ns.response(404, 'Booking not found', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Update booking status for a specific booking owned by the current user.

**Required Fields:**
- booking_id: ID of the booking to update
- status: New booking status (Pending, Confirmed, Completed, Cancelled)

**Sample Payload:**
```json
{
  "booking_id": 123,
  "status": "Confirmed"
}
```

**Business Rules:**
- User can only update their own bookings
- All status transitions are allowed
- System will validate that the booking belongs to the authenticated user

**Response includes:**
- Success message
- Complete updated booking details with provider and service information''')
    @jwt_required()
    def post(self):
        """Update booking status for current user's booking"""
        print("=== /me/bookings POST endpoint called ===")

        if not DB_AVAILABLE:
            print("Database not available")
            return {'error': 'Database connection not available'}, 503

        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')

            # Only allow users (not providers) to access this endpoint
            if user_type != 'user':
                return {'error': 'Access denied - user account required'}, 403

            user_id = current_identity['user_id']
            user = User.query.get(user_id)

            if not user:
                return {'error': 'User not found'}, 404

            data = request.get_json()

            # Validation
            if not all(k in data for k in ['booking_id', 'status']):
                return {'error': 'Missing required fields: booking_id and status'}, 400

            # Validate status
            valid_statuses = ['Pending', 'Confirmed', 'Completed', 'Cancelled']
            if data['status'] not in valid_statuses:
                return {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, 400

            # Get booking and verify ownership
            booking = ServiceBooking.query.filter_by(
                id=data['booking_id'],
                user_id=user_id
            ).first()

            if not booking:
                return {'error': 'Booking not found or does not belong to current user'}, 404

            # Update booking status
            booking.status = data['status']
            db.session.commit()

            # Get related data for response
            provider = Provider.query.get(booking.provider_id)
            provider_service = ProviderService.query.get(booking.provider_service_id)
            service_category = ServiceCategory.query.get(provider_service.category_id) if provider_service else None
            payment_status = PaymentStatus.query.filter_by(booking_id=booking.id).first()

            # Prepare response
            booking_data = {
                'id': booking.id,
                'booking_date': booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else None,
                'booking_day': booking.booking_day,
                'booking_time': booking.booking_time.strftime('%H:%M') if booking.booking_time else None,
                'status': booking.status,
                'created_at': booking.created_at.isoformat() if booking.created_at else None,
                'updated_at': booking.updated_at.isoformat() if booking.updated_at else None,
                'provider': {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'about': provider.about,
                    'is_active': provider.is_active
                } if provider else None,
                'service': {
                    'id': provider_service.id,
                    'service_title': provider_service.service_title,
                    'service_description': provider_service.service_description,
                    'price_decimal': float(provider_service.price_decimal) if provider_service.price_decimal else None,
                    'duration_minutes': provider_service.duration_minutes,
                    'category': {
                        'id': service_category.id,
                        'category_name': service_category.category_name,
                        'description': service_category.description
                    } if service_category else None
                } if provider_service else None,
                'payment_status': {
                    'id': payment_status.id,
                    'status': payment_status.status,
                    'description': payment_status.description,
                    'created_at': payment_status.created_at.isoformat() if payment_status.created_at else None
                } if payment_status else None
            }

            return {
                'message': f'Booking status updated to {data["status"]} successfully',
                'booking': booking_data
            }, 200

        except Exception as e:
            print(f"=== ERROR in /me/bookings POST endpoint ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print("Full traceback:")
            traceback.print_exc()
            print("=== END ERROR LOG ===")
            db.session.rollback()
            return {'error': str(e)}, 500

# Service Booking Models
service_booking_model = users_ns.model('ServiceBooking', {
    'user_id': fields.Integer(required=True, description='User ID who is making the booking'),
    'provider_service_id': fields.Integer(required=True, description='Provider service ID to book'),
    'booking_date': fields.String(required=True, description='Date for booking in YYYY-MM-DD format'),
    'booking_day': fields.String(required=True, description='Day of the week for booking', enum=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
    'booking_time': fields.String(required=True, description='Time for booking in HH:MM format'),
    'status': fields.String(description='Booking status (optional, defaults to Pending)', enum=['Pending', 'Confirmed', 'Completed', 'Cancelled'])
})

service_booking_response_model = users_ns.model('ServiceBookingResponse', {
    'message': fields.String(description='Success message'),
    'booking': fields.Raw(description='Created booking details'),
    'service_info': fields.Raw(description='Service information'),
    'provider_info': fields.Raw(description='Provider information')
})

error_model = users_ns.model('Error', {
    'error': fields.String(description='Error message')
})

@users_ns.route('/service-booking')
class ServiceBookingCreate(Resource):
    @users_ns.expect(service_booking_model)
    @users_ns.marshal_with(service_booking_response_model, code=201)
    @users_ns.response(400, 'Validation Error', error_model)
    @users_ns.response(404, 'Service/User Not Found', error_model)
    @users_ns.response(409, 'Booking Conflict', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Create a new service booking for a user.
    
**Required Fields:**
- user_id: ID of the user making the booking
- provider_service_id: ID of the provider service to book
- booking_date: Date for booking (YYYY-MM-DD format)
- booking_day: Day of the week (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
- booking_time: Time for booking (HH:MM format, 24-hour)

**Optional Fields:**
- status: Booking status (Pending, Confirmed, Completed, Cancelled) - defaults to 'Pending'

**Sample Payload:**
```json
{
  "user_id": 1,
  "provider_service_id": 5,
  "booking_date": "2024-01-15",
  "booking_day": "Monday",
  "booking_time": "10:30",
  "status": "Pending"
}
```

**Sample Payload (with custom status):**
```json
{
  "user_id": 1,
  "provider_service_id": 5,
  "booking_date": "2024-01-15",
  "booking_day": "Monday",
  "booking_time": "10:30",
  "status": "Confirmed"
}
```

**Response includes:**
- Success message
- Complete booking details with status
- Service information (title, description, price)
- Provider information (name, contact)

**Business Rules:**
- User and provider service must exist
- Provider service must be active
- Booking time must fall within provider's available schedule for that day
- No duplicate bookings for the same user, service, day, and time
- Provider must be active
- Status defaults to 'Pending' if not specified

**Validation:**
- Valid booking day (Monday-Sunday)  
- Valid time format (HH:MM)
- Valid status (Pending, Confirmed, Completed, Cancelled)
- Booking time must be within service schedule
- User cannot book same service multiple times for same day/time

**Status Meanings:**
- Pending: Booking created, awaiting provider confirmation
- Confirmed: Provider has accepted the booking
- Completed: Service has been delivered
- Cancelled: Booking has been cancelled by user or provider''')
    def post(self):
        """Create a new service booking"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            from datetime import datetime
            data = request.get_json()
            
            print(f"Service booking request data: {data}")
            
            # Validation
            required_fields = ['user_id', 'provider_service_id', 'booking_date', 'booking_day', 'booking_time']
            missing_fields = [field for field in required_fields if field not in data or data[field] is None]
            if missing_fields:
                print(f"Missing required fields: {missing_fields}")
                return {'error': f'Missing required fields: {", ".join(missing_fields)}'}, 400
            
            # Validate booking day
            valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            if data['booking_day'] not in valid_days:
                print(f"Invalid booking day: {data['booking_day']}")
                return {'error': f'Invalid booking_day. Must be one of: {", ".join(valid_days)}'}, 400
            
            # Validate status if provided
            valid_statuses = ['Pending', 'Confirmed', 'Completed', 'Cancelled']
            booking_status = data.get('status', 'Pending')  # Default to 'Pending' if not provided
            if booking_status not in valid_statuses:
                print(f"Invalid status: {booking_status}")
                return {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, 400
            
            # Validate booking_date format
            try:
                booking_date = datetime.strptime(data['booking_date'], '%Y-%m-%d').date()
                print(f"Parsed booking_date: {booking_date}")
            except ValueError as e:
                print(f"Invalid booking_date format: {data['booking_date']}, error: {e}")
                return {'error': 'Invalid booking_date format. Use YYYY-MM-DD'}, 400
            
            # Validate time format
            try:
                booking_time = datetime.strptime(data['booking_time'], '%H:%M').time()
                print(f"Parsed booking_time: {booking_time}")
            except ValueError as e:
                print(f"Invalid booking_time format: {data['booking_time']}, error: {e}")
                return {'error': 'Invalid booking_time format. Use HH:MM (24-hour format)'}, 400
            
            # Check if user exists
            print(f"Checking user with ID: {data['user_id']}")
            user = User.query.get(data['user_id'])
            if not user:
                print(f"User not found with ID: {data['user_id']}")
                return {'error': 'User not found'}, 404
            print(f"User found: {user.full_name}")
            
            # Check if provider service exists and is active
            print(f"Checking provider service with ID: {data['provider_service_id']}")
            provider_service = ProviderService.query.get(data['provider_service_id'])
            if not provider_service:
                print(f"Provider service not found with ID: {data['provider_service_id']}")
                return {'error': 'Provider service not found'}, 404
            print(f"Provider service found: {provider_service.service_title}")
            
            if not provider_service.is_active:
                print(f"Provider service is not active: {provider_service.id}")
                return {'error': 'Provider service is not active'}, 400
            
            # Check if provider is active
            print(f"Checking provider with ID: {provider_service.provider_id}")
            provider = Provider.query.get(provider_service.provider_id)
            if not provider or not provider.is_active:
                print(f"Provider not found or not active: {provider_service.provider_id}")
                return {'error': 'Provider is not active'}, 400
            print(f"Provider found: {provider.full_name}")
            
            # Check if provider has schedule for this day
            provider_schedule = ProviderServiceSchedule.query.filter_by(
                provider_service_id=data['provider_service_id'],
                schedule_day=data['booking_day']
            ).first()
            
            if not provider_schedule:
                return {'error': f'Provider service is not available on {data["booking_day"]}'}, 400
            
            # Check if booking time falls within provider's schedule
            if booking_time < provider_schedule.start_time or booking_time >= provider_schedule.end_time:
                return {
                    'error': f'Booking time must be between {provider_schedule.start_time.strftime("%H:%M")} and {provider_schedule.end_time.strftime("%H:%M")} on {data["booking_day"]}'
                }, 400
            
            # Check for existing booking (prevent duplicates)
            existing_booking = ServiceBooking.query.filter_by(
                user_id=data['user_id'],
                provider_service_id=data['provider_service_id'],
                booking_date=booking_date,
                booking_day=data['booking_day'],
                booking_time=booking_time
            ).first()
            
            if existing_booking:
                return {'error': 'You already have a booking for this service at this time'}, 409
            
            # Create new booking
            booking = ServiceBooking(
                user_id=data['user_id'],
                provider_id=provider_service.provider_id,
                provider_service_id=data['provider_service_id'],
                booking_date=booking_date,
                booking_day=data['booking_day'],
                booking_time=booking_time,
                status=booking_status
            )
            
            db.session.add(booking)
            db.session.commit()
            
            # Get category for response
            category = ServiceCategory.query.get(provider_service.category_id)
            
            # Prepare response
            booking_details = {
                'id': booking.id,
                'user_id': booking.user_id,
                'provider_id': booking.provider_id,
                'provider_service_id': booking.provider_service_id,
                'booking_date': booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else None,
                'booking_day': booking.booking_day,
                'booking_time': booking.booking_time.strftime('%H:%M'),
                'status': booking.status,
                'created_at': booking.created_at.isoformat() if booking.created_at else None,
                'updated_at': booking.updated_at.isoformat() if booking.updated_at else None
            }
            
            service_info = {
                'id': provider_service.id,
                'service_title': provider_service.service_title,
                'service_description': provider_service.service_description,
                'price_decimal': float(provider_service.price_decimal) if provider_service.price_decimal else None,
                'duration_minutes': provider_service.duration_minutes,
                'category': {
                    'id': category.id,
                    'category_name': category.category_name,
                    'description': category.description
                } if category else None
            }
            
            provider_info = {
                'id': provider.id,
                'business_name': provider.business_name,
                'full_name': provider.full_name,
                'email': provider.email,
                'address': provider.address,
                'about': provider.about
            }
            
            return {
                'message': 'Service booking created successfully',
                'booking': booking_details,
                'service_info': service_info,
                'provider_info': provider_info
            }, 201
            
        except Exception as e:
            print(f"Service booking creation error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
            try:
                db.session.rollback()
            except Exception as rollback_error:
                print(f"Rollback error: {rollback_error}")
            
            return {'error': f'Internal server error: {str(e)}'}, 500

# Payment Status Models
payment_status_model = users_ns.model('PaymentStatus', {
    'booking_id': fields.Integer(required=True, description='Service booking ID'),
    'status': fields.String(required=True, description='Payment status', enum=['Pending', 'Paid', 'Failed', 'Cancelled', 'Refunded']),
    'description': fields.String(description='Optional description of the payment status')
})

payment_status_response_model = users_ns.model('PaymentStatusResponse', {
    'message': fields.String(description='Success message'),
    'payment_status': fields.Raw(description='Created payment status details'),
    'booking_info': fields.Raw(description='Related booking information')
})

@users_ns.route('/payment-status')
class PaymentStatusCreate(Resource):
    @users_ns.expect(payment_status_model)
    @users_ns.marshal_with(payment_status_response_model, code=201)
    @users_ns.response(400, 'Validation Error', error_model)
    @users_ns.response(404, 'Booking Not Found', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Create a payment status record for a service booking.
    
**Required Fields:**
- booking_id: ID of the service booking
- status: Payment status (Pending, Paid, Failed, Cancelled, Refunded)

**Optional Fields:**
- description: Additional description about the payment status

**Sample Payload:**
```json
{
  "booking_id": 1,
  "status": "Paid",
  "description": "Payment processed successfully via credit card"
}
```

**Sample Payload (Minimal):**
```json
{
  "booking_id": 1,
  "status": "Failed"
}
```

**Response includes:**
- Success message
- Complete payment status details
- Related booking information

**Payment Status Meanings:**
- Pending: Payment has been initiated but not yet processed
- Paid: Payment has been successfully processed and confirmed
- Failed: Payment processing failed or was declined
- Cancelled: Payment was cancelled by user or system
- Refunded: Payment was refunded back to the user

**Business Rules:**
- Booking must exist in the system
- Valid status must be provided
- Description is optional but recommended for clarity

**Validation:**
- Valid booking_id (must exist in service_booking table)
- Valid status (Pending, Paid, Failed, Cancelled, Refunded)
- Description maximum 255 characters''')
    def post(self):
        """Create a payment status record for a booking"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            data = request.get_json()
            
            # Validation
            required_fields = ['booking_id', 'status']
            if not all(k in data for k in required_fields):
                return {'error': f'Missing required fields: {", ".join(required_fields)}'}, 400
            
            # Validate status
            valid_statuses = ['Pending', 'Paid', 'Failed', 'Cancelled', 'Refunded']
            if data['status'] not in valid_statuses:
                return {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, 400
            
            # Validate description length if provided
            description = data.get('description', '')
            if description and len(description) > 255:
                return {'error': 'Description must be 255 characters or less'}, 400
            
            # Check if booking exists
            booking = ServiceBooking.query.get(data['booking_id'])
            if not booking:
                return {'error': 'Service booking not found'}, 404
            
            # Create payment status record
            payment_status = PaymentStatus(
                booking_id=data['booking_id'],
                status=data['status'],
                description=description if description else None
            )
            
            db.session.add(payment_status)
            db.session.commit()
            
            # Get related data for response
            user = User.query.get(booking.user_id)
            provider = Provider.query.get(booking.provider_id)
            provider_service = ProviderService.query.get(booking.provider_service_id)
            
            # Prepare response
            payment_status_details = {
                'id': payment_status.id,
                'booking_id': payment_status.booking_id,
                'status': payment_status.status,
                'description': payment_status.description,
                'created_at': payment_status.created_at.isoformat() if payment_status.created_at else None,
                'updated_at': payment_status.updated_at.isoformat() if payment_status.updated_at else None
            }
            
            booking_info = {
                'id': booking.id,
                'booking_date': booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else None,
                'booking_day': booking.booking_day,
                'booking_time': booking.booking_time.strftime('%H:%M'),
                'booking_status': booking.status,
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email
                } if user else None,
                'provider': {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email
                } if provider else None,
                'service': {
                    'id': provider_service.id,
                    'service_title': provider_service.service_title,
                    'price_decimal': float(provider_service.price_decimal) if provider_service.price_decimal else None
                } if provider_service else None
            }
            
            return {
                'message': 'Payment status created successfully',
                'payment_status': payment_status_details,
                'booking_info': booking_info
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# Booking Calendar Models
booking_calendar_response_model = users_ns.model('BookingCalendarResponse', {
    'date': fields.String(description='Date of the bookings'),
    'bookings': fields.List(fields.Raw(description='List of bookings for this date'))
})

@users_ns.route('/booking-calendar')
class BookingCalendar(Resource):
    @users_ns.marshal_with(booking_calendar_response_model, code=200)
    @users_ns.response(400, 'Validation Error', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Get booking services calendar filtered by date range using booking_date column.
    
**Query Parameters:**
- start_date: Start date for filtering (YYYY-MM-DD format) - optional
- end_date: End date for filtering (YYYY-MM-DD format) - optional
- user_id: Filter by specific user ID - optional
- provider_id: Filter by specific provider ID - optional

**Sample Request:**
```
GET /users/booking-calendar?start_date=2024-01-01&end_date=2024-01-31&user_id=1
```

**Response includes:**
- Bookings grouped by booking date
- Complete booking details with service and provider information
- Payment status if available
- User information

**Date Filtering:**
- If no dates provided, returns all bookings
- If only start_date provided, returns bookings from that date onwards
- If only end_date provided, returns bookings up to that date
- Uses booking_date column for date filtering

**Booking Information includes:**
- Booking ID, status, day, and time
- Service details (title, description, price)
- Provider information (name, contact)
- User information
- Payment status details
- Creation and update timestamps''')
    def get(self):
        """Get booking services calendar using booking_date for date filtering"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            from datetime import datetime
            
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            user_id = request.args.get('user_id', type=int)
            provider_id = request.args.get('provider_id', type=int)
            
            query = db.session.query(ServiceBooking)
            
            # Apply date filters based on booking_date
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                    query = query.filter(ServiceBooking.booking_date >= start_dt)
                except ValueError:
                    return {'error': 'Invalid start_date format. Use YYYY-MM-DD'}, 400
                    
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                    query = query.filter(ServiceBooking.booking_date <= end_dt)
                except ValueError:
                    return {'error': 'Invalid end_date format. Use YYYY-MM-DD'}, 400
                    
            if user_id:
                query = query.filter(ServiceBooking.user_id == user_id)
                
            if provider_id:
                query = query.filter(ServiceBooking.provider_id == provider_id)
            
            # Order by booking_date descending
            bookings = query.order_by(ServiceBooking.booking_date.desc()).all()
            
            # Group bookings by date
            calendar_data = {}
            
            for booking in bookings:
                # Get related data
                user = User.query.get(booking.user_id)
                provider = Provider.query.get(booking.provider_id)
                provider_service = ProviderService.query.get(booking.provider_service_id)
                service_category = ServiceCategory.query.get(provider_service.category_id) if provider_service else None
                payment_status = PaymentStatus.query.filter_by(booking_id=booking.id).first()
                
                # Format the date from booking_date
                booking_date_str = booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else 'unknown'
                
                if booking_date_str not in calendar_data:
                    calendar_data[booking_date_str] = []
                
                booking_details = {
                    'id': booking.id,
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else None,
                    'booking_day': booking.booking_day,
                    'booking_time': booking.booking_time.strftime('%H:%M') if booking.booking_time else None,
                    'status': booking.status,
                    'created_at': booking.created_at.isoformat() if booking.created_at else None,
                    'updated_at': booking.updated_at.isoformat() if booking.updated_at else None,
                    'user': {
                        'id': user.id,
                        'full_name': user.full_name,
                        'email': user.email
                    } if user else None,
                    'provider': {
                        'id': provider.id,
                        'business_name': provider.business_name,
                        'full_name': provider.full_name,
                        'email': provider.email,
                        'is_active': provider.is_active
                    } if provider else None,
                    'service': {
                        'id': provider_service.id,
                        'service_title': provider_service.service_title,
                        'service_description': provider_service.service_description,
                        'price_decimal': float(provider_service.price_decimal) if provider_service.price_decimal else None,
                        'duration_minutes': provider_service.duration_minutes,
                        'category': {
                            'id': service_category.id,
                            'category_name': service_category.category_name,
                            'description': service_category.description
                        } if service_category else None
                    } if provider_service else None,
                    'payment_status': {
                        'id': payment_status.id,
                        'status': payment_status.status,
                        'description': payment_status.description,
                        'created_at': payment_status.created_at.isoformat() if payment_status.created_at else None
                    } if payment_status else None
                }
                
                calendar_data[booking_date_str].append(booking_details)
            
            # Convert to list format for response
            calendar_response = []
            for date, bookings_list in sorted(calendar_data.items(), reverse=True):
                calendar_response.append({
                    'date': date,
                    'bookings': bookings_list
                })
            
            return calendar_response, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# Booking Schedule Checker Models
booking_schedule_check_model = users_ns.model('BookingScheduleCheck', {
    'provider_service_id': fields.Integer(required=True, description='Provider service ID to check schedule for'),
    'booking_day': fields.String(required=True, description='Day of the week to check', enum=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
    'date': fields.String(description='Specific date to check (YYYY-MM-DD format) - optional')
})

booking_schedule_response_model = users_ns.model('BookingScheduleResponse', {
    'provider_service': fields.Raw(description='Provider service information'),
    'schedule': fields.Raw(description='Provider schedule for the day'),
    'available_slots': fields.List(fields.String(), description='Available booking time slots'),
    'existing_bookings': fields.List(fields.Raw(), description='All existing bookings for this day/service')
})

@users_ns.route('/booking-schedule-check')
class BookingScheduleCheck(Resource):
    @users_ns.expect(booking_schedule_check_model)
    @users_ns.marshal_with(booking_schedule_response_model, code=200)
    @users_ns.response(400, 'Validation Error', error_model)
    @users_ns.response(404, 'Service Not Found', error_model)
    @users_ns.response(500, 'Internal Server Error', error_model)
    @users_ns.doc(description='''Check booking schedule availability for a specific provider service and day.
    
**Required Fields:**
- provider_service_id: ID of the provider service to check
- booking_day: Day of the week (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)

**Optional Fields:**
- date: Specific date to check (YYYY-MM-DD format)

**Sample Payload:**
```json
{
  "provider_service_id": 5,
  "booking_day": "Monday",
  "date": "2024-01-15"
}
```

**Sample Payload (without specific date):**
```json
{
  "provider_service_id": 5,
  "booking_day": "Monday"
}
```

**Response includes:**
- Provider service information (title, description, price, duration)
- Provider schedule for the specified day
- Available time slots based on schedule and existing bookings
- All existing bookings for this service/day (regardless of status)
- Service category information
- Provider details

**Available Slots Logic:**
- Based on provider's schedule for the day
- Considers service duration to calculate slots
- Shows available slots even if there are existing bookings
- Time slots are generated in 30-minute intervals by default

**Existing Bookings:**
- Returns ALL bookings (Pending, Confirmed, Completed, Cancelled)
- Includes user information for each booking
- Shows booking time and status
- Includes payment status if available

**Business Rules:**
- Provider service must exist and be active
- Provider must be active
- Schedule must exist for the specified day
- Time slots are calculated based on service duration''')
    def post(self):
        """Check booking schedule and availability for a provider service"""
        if not DB_AVAILABLE:
            return {'error': 'Database connection not available'}, 503
            
        try:
            from datetime import datetime, timedelta
            data = request.get_json()
            
            # Validation
            required_fields = ['provider_service_id', 'booking_day']
            if not all(k in data for k in required_fields):
                return {'error': f'Missing required fields: {required_fields}'}, 400
            
            provider_service_id = data['provider_service_id']
            booking_day = data['booking_day']
            check_date = data.get('date')
            
            # Validate booking day
            valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            if booking_day not in valid_days:
                return {'error': f'Invalid booking_day. Must be one of: {valid_days}'}, 400
            
            # Validate date format if provided
            if check_date:
                try:
                    datetime.strptime(check_date, '%Y-%m-%d')
                except ValueError:
                    return {'error': 'Invalid date format. Use YYYY-MM-DD'}, 400
            
            # Get provider service
            provider_service = ProviderService.query.get(provider_service_id)
            if not provider_service or not provider_service.is_active:
                return {'error': 'Provider service not found or inactive'}, 404
            
            # Get provider
            provider = Provider.query.get(provider_service.provider_id)
            if not provider or not provider.is_active:
                return {'error': 'Provider not found or inactive'}, 404
            
            # Get service category
            service_category = ServiceCategory.query.get(provider_service.category_id)
            
            # Get provider schedule for the day
            schedule = ProviderServiceSchedule.query.filter_by(
                provider_service_id=provider_service_id,
                schedule_day=booking_day
            ).first()
            
            if not schedule:
                return {
                    'provider_service': {
                        'id': provider_service.id,
                        'service_title': provider_service.service_title,
                        'service_description': provider_service.service_description,
                        'price_decimal': float(provider_service.price_decimal) if provider_service.price_decimal else None,
                        'duration_minutes': provider_service.duration_minutes,
                        'category': {
                            'id': service_category.id,
                            'category_name': service_category.category_name,
                            'description': service_category.description
                        } if service_category else None,
                        'provider': {
                            'id': provider.id,
                            'business_name': provider.business_name,
                            'full_name': provider.full_name,
                            'email': provider.email
                        }
                    },
                    'schedule': None,
                    'available_slots': [],
                    'existing_bookings': []
                }, 200
            
            # Get all existing bookings for this service and day
            bookings_query = ServiceBooking.query.filter_by(
                provider_service_id=provider_service_id,
                booking_day=booking_day
            )
            
            # Filter by specific date if provided
            if check_date:
                check_dt = datetime.strptime(check_date, '%Y-%m-%d').date()
                bookings_query = bookings_query.filter(
                    ServiceBooking.booking_date == check_dt
                )
            
            existing_bookings = bookings_query.all()
            
            # Generate available time slots
            start_time = schedule.start_time
            end_time = schedule.end_time
            service_duration = provider_service.duration_minutes or 60  # Default 60 minutes
            slot_interval = 30  # 30-minute intervals
            
            available_slots = []
            current_time = datetime.combine(datetime.today(), start_time)
            end_datetime = datetime.combine(datetime.today(), end_time)
            
            while current_time + timedelta(minutes=service_duration) <= end_datetime:
                time_slot = current_time.strftime('%H:%M')
                available_slots.append(time_slot)
                current_time += timedelta(minutes=slot_interval)
            
            # Format existing bookings with details
            booking_details = []
            for booking in existing_bookings:
                user = User.query.get(booking.user_id)
                payment_status = PaymentStatus.query.filter_by(booking_id=booking.id).first()
                
                booking_info = {
                    'id': booking.id,
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else None,
                    'booking_time': booking.booking_time.strftime('%H:%M') if booking.booking_time else None,
                    'status': booking.status,
                    'created_at': booking.created_at.isoformat() if booking.created_at else None,
                    'updated_at': booking.updated_at.isoformat() if booking.updated_at else None,
                    'user': {
                        'id': user.id,
                        'full_name': user.full_name,
                        'email': user.email
                    } if user else None,
                    'payment_status': {
                        'id': payment_status.id,
                        'status': payment_status.status,
                        'description': payment_status.description,
                        'created_at': payment_status.created_at.isoformat() if payment_status.created_at else None
                    } if payment_status else None
                }
                booking_details.append(booking_info)
            
            return {
                'provider_service': {
                    'id': provider_service.id,
                    'service_title': provider_service.service_title,
                    'service_description': provider_service.service_description,
                    'price_decimal': float(provider_service.price_decimal) if provider_service.price_decimal else None,
                    'duration_minutes': provider_service.duration_minutes,
                    'category': {
                        'id': service_category.id,
                        'category_name': service_category.category_name,
                        'description': service_category.description
                    } if service_category else None,
                    'provider': {
                        'id': provider.id,
                        'business_name': provider.business_name,
                        'full_name': provider.full_name,
                        'email': provider.email,
                        'is_active': provider.is_active
                    }
                },
                'schedule': {
                    'id': schedule.id,
                    'schedule_day': schedule.schedule_day,
                    'start_time': schedule.start_time.strftime('%H:%M'),
                    'end_time': schedule.end_time.strftime('%H:%M'),
                    'created_at': schedule.created_at.isoformat() if schedule.created_at else None
                },
                'available_slots': available_slots,
                'existing_bookings': booking_details
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500