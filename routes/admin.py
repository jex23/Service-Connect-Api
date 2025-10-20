from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from models import db, Admin, Provider, User, ProviderService, ServiceCategory, ProviderServicePhoto, ProviderServiceSchedule, ServiceBooking, PaymentStatus, CustomerReport
from datetime import datetime
from functools import wraps
from sqlalchemy import func
from utils.email import send_provider_verification_email, send_user_verification_email, send_account_status_change_email

# Create namespace
admin_ns = Namespace('admin', description='Admin operations')

# Define models for API documentation
error_model = admin_ns.model('Error', {
    'error': fields.String(required=True, description='Error message')
})

success_model = admin_ns.model('Success', {
    'message': fields.String(required=True, description='Success message')
})

admin_model = admin_ns.model('Admin', {
    'admin_id': fields.Integer(description='Admin ID'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email address'),
    'role': fields.String(description='Admin role', enum=['superadmin', 'admin', 'moderator']),
    'address': fields.String(description='Address'),
    'date_created': fields.DateTime(description='Date created'),
    'date_modified': fields.DateTime(description='Date modified'),
    'last_login': fields.DateTime(description='Last login'),
    'is_active': fields.Boolean(description='Is active'),
    'is_deleted': fields.Boolean(description='Is deleted')
})

login_model = admin_ns.model('AdminLogin', {
    'email': fields.String(required=True, description='Admin email'),
    'password': fields.String(required=True, description='Admin password')
})

login_response_model = admin_ns.model('AdminLoginResponse', {
    'access_token': fields.String(description='JWT access token'),
    'admin': fields.Nested(admin_model),
    'message': fields.String(description='Login message')
})

register_model = admin_ns.model('AdminRegister', {
    'full_name': fields.String(required=True, description='Full name'),
    'email': fields.String(required=True, description='Email address'),
    'password': fields.String(required=True, description='Password'),
    'role': fields.String(description='Admin role (superadmin, admin, moderator)', enum=['superadmin', 'admin', 'moderator'], default='admin'),
    'address': fields.String(description='Address')
})

register_response_model = admin_ns.model('AdminRegisterResponse', {
    'message': fields.String(description='Registration message'),
    'admin': fields.Nested(admin_model)
})

# Provider models
provider_model = admin_ns.model('Provider', {
    'id': fields.Integer(description='Provider ID'),
    'business_name': fields.String(description='Business name'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email address'),
    'contact_number': fields.String(description='Contact number'),
    'address': fields.String(description='Address'),
    'bir_id_front': fields.String(description='BIR ID front'),
    'bir_id_back': fields.String(description='BIR ID back'),
    'business_permit': fields.String(description='Business permit'),
    'image_logo': fields.String(description='Business logo'),
    'about': fields.String(description='About'),
    'is_active': fields.Boolean(description='Is active'),
    'status': fields.String(description='Status', enum=['active', 'inactive', 'suspended', 'for_verification']),
    'created_at': fields.DateTime(description='Created at'),
    'updated_at': fields.DateTime(description='Updated at')
})

update_status_model = admin_ns.model('UpdateProviderStatus', {
    'status': fields.String(required=True, description='Provider status', enum=['active', 'inactive', 'suspended', 'for_verification'])
})

# User models
user_model = admin_ns.model('User', {
    'id': fields.Integer(description='User ID'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email address'),
    'address': fields.String(description='Address'),
    'id_front': fields.String(description='ID front'),
    'id_back': fields.String(description='ID back'),
    'status': fields.String(description='Status', enum=['active', 'inactive', 'suspended', 'for_verification']),
    'created_at': fields.DateTime(description='Created at'),
    'updated_at': fields.DateTime(description='Updated at')
})

update_user_status_model = admin_ns.model('UpdateUserStatus', {
    'status': fields.String(required=True, description='User status', enum=['active', 'inactive', 'suspended', 'for_verification'])
})

# Service models
provider_info_model = admin_ns.model('ProviderInfo', {
    'id': fields.Integer(description='Provider ID'),
    'business_name': fields.String(description='Business name'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email'),
    'contact_number': fields.String(description='Contact number'),
    'address': fields.String(description='Address'),
    'image_logo': fields.String(description='Business logo URL'),
    'about': fields.String(description='About'),
    'is_active': fields.Boolean(description='Is active'),
    'status': fields.String(description='Status')
})

category_info_model = admin_ns.model('CategoryInfo', {
    'id': fields.Integer(description='Category ID'),
    'category_name': fields.String(description='Category name'),
    'description': fields.String(description='Category description')
})

service_photo_model = admin_ns.model('ServicePhoto', {
    'id': fields.Integer(description='Photo ID'),
    'photo_url': fields.String(description='Photo URL'),
    'sort_order': fields.Integer(description='Sort order')
})

service_schedule_model = admin_ns.model('ServiceSchedule', {
    'id': fields.Integer(description='Schedule ID'),
    'schedule_day': fields.String(description='Day of week'),
    'start_time': fields.String(description='Start time'),
    'end_time': fields.String(description='End time')
})

service_model = admin_ns.model('Service', {
    'id': fields.Integer(description='Service ID'),
    'provider_id': fields.Integer(description='Provider ID'),
    'category_id': fields.Integer(description='Category ID'),
    'service_title': fields.String(description='Service title'),
    'service_description': fields.String(description='Service description'),
    'price_decimal': fields.Float(description='Price'),
    'duration_minutes': fields.Integer(description='Duration in minutes'),
    'is_active': fields.Boolean(description='Is active'),
    'created_at': fields.DateTime(description='Created at'),
    'updated_at': fields.DateTime(description='Updated at'),
    'provider': fields.Nested(provider_info_model, description='Provider information'),
    'category': fields.Nested(category_info_model, description='Category information'),
    'photos': fields.List(fields.Nested(service_photo_model), description='Service photos'),
    'schedules': fields.List(fields.Nested(service_schedule_model), description='Service schedules')
})

update_service_status_model = admin_ns.model('UpdateServiceStatus', {
    'is_active': fields.Boolean(required=True, description='Service active status')
})

# Booking models
user_info_model = admin_ns.model('UserInfo', {
    'id': fields.Integer(description='User ID'),
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email'),
    'address': fields.String(description='Address'),
    'status': fields.String(description='Status')
})

booking_service_model = admin_ns.model('BookingService', {
    'id': fields.Integer(description='Service ID'),
    'service_title': fields.String(description='Service title'),
    'service_description': fields.String(description='Service description'),
    'price_decimal': fields.Float(description='Price'),
    'duration_minutes': fields.Integer(description='Duration in minutes')
})

booking_model = admin_ns.model('Booking', {
    'id': fields.Integer(description='Booking ID'),
    'user_id': fields.Integer(description='User ID'),
    'provider_id': fields.Integer(description='Provider ID'),
    'provider_service_id': fields.Integer(description='Service ID'),
    'booking_date': fields.String(description='Booking date (YYYY-MM-DD)'),
    'booking_day': fields.String(description='Booking day'),
    'booking_time': fields.String(description='Booking time (HH:MM:SS)'),
    'status': fields.String(description='Booking status', enum=['Pending', 'Confirmed', 'Completed', 'Cancelled']),
    'created_at': fields.DateTime(description='Created at'),
    'updated_at': fields.DateTime(description='Updated at'),
    'user': fields.Nested(user_info_model, description='User information'),
    'provider': fields.Nested(provider_info_model, description='Provider information'),
    'service': fields.Nested(booking_service_model, description='Service information')
})

update_booking_status_model = admin_ns.model('UpdateBookingStatus', {
    'status': fields.String(required=True, description='Booking status', enum=['Pending', 'Confirmed', 'Completed', 'Cancelled'])
})

# Sales Report models
sales_booking_detail_model = admin_ns.model('SalesBookingDetail', {
    'booking_id': fields.Integer(description='Booking ID'),
    'user_name': fields.String(description='User name'),
    'user_email': fields.String(description='User email'),
    'service_title': fields.String(description='Service title'),
    'booking_date': fields.String(description='Booking date'),
    'booking_time': fields.String(description='Booking time'),
    'price': fields.Float(description='Service price'),
    'payment_status': fields.String(description='Payment status'),
    'payment_date': fields.String(description='Payment date'),
    'booking_status': fields.String(description='Booking status')
})

provider_sales_summary_model = admin_ns.model('ProviderSalesSummary', {
    'provider_id': fields.Integer(description='Provider ID'),
    'business_name': fields.String(description='Business name'),
    'provider_name': fields.String(description='Provider name'),
    'email': fields.String(description='Email'),
    'total_bookings': fields.Integer(description='Total paid bookings'),
    'total_revenue': fields.Float(description='Total revenue'),
    'completed_bookings': fields.Integer(description='Completed bookings'),
    'pending_bookings': fields.Integer(description='Pending bookings'),
    'cancelled_bookings': fields.Integer(description='Cancelled bookings')
})

sales_report_model = admin_ns.model('SalesReport', {
    'provider': fields.Nested(provider_sales_summary_model, description='Provider summary'),
    'bookings': fields.List(fields.Nested(sales_booking_detail_model), description='Paid booking details')
})

overall_sales_summary_model = admin_ns.model('OverallSalesSummary', {
    'total_providers': fields.Integer(description='Total providers with sales'),
    'total_revenue': fields.Float(description='Total platform revenue'),
    'total_bookings': fields.Integer(description='Total paid bookings'),
    'providers': fields.List(fields.Nested(provider_sales_summary_model), description='Provider summaries')
})

# Customer Report/Complaint models
report_model = admin_ns.model('CustomerReport', {
    'id': fields.Integer(description='Report ID'),
    'user_id': fields.Integer(description='User ID'),
    'provider_id': fields.Integer(description='Provider ID'),
    'provider_service_id': fields.Integer(description='Service ID'),
    'booking_id': fields.Integer(description='Booking ID'),
    'report_type': fields.String(description='Report type'),
    'subject': fields.String(description='Report subject'),
    'description': fields.String(description='Report description'),
    'status': fields.String(description='Report status'),
    'admin_response': fields.String(description='Admin response'),
    'admin_id': fields.Integer(description='Admin ID who handled this'),
    'created_at': fields.DateTime(description='Created at'),
    'updated_at': fields.DateTime(description='Updated at'),
    'resolved_at': fields.DateTime(description='Resolved at'),
    'user': fields.Nested(user_info_model, description='User information'),
    'provider': fields.Nested(provider_info_model, description='Provider information'),
    'service': fields.Nested(booking_service_model, description='Service information'),
    'booking': fields.Raw(description='Booking information')
})

update_report_status_model = admin_ns.model('UpdateReportStatus', {
    'status': fields.String(required=True, description='Report status', enum=['Pending', 'Under Review', 'Resolved', 'Rejected']),
    'admin_response': fields.String(description='Admin response/notes')
})

# Dashboard summary models
dashboard_users_summary_model = admin_ns.model('DashboardUsersSummary', {
    'total_users': fields.Integer(description='Total number of users'),
    'active_users': fields.Integer(description='Active users'),
    'inactive_users': fields.Integer(description='Inactive users'),
    'suspended_users': fields.Integer(description='Suspended users'),
    'pending_verification_users': fields.Integer(description='Users pending verification')
})

dashboard_providers_summary_model = admin_ns.model('DashboardProvidersSummary', {
    'total_providers': fields.Integer(description='Total number of providers'),
    'active_providers': fields.Integer(description='Active providers'),
    'inactive_providers': fields.Integer(description='Inactive providers'),
    'suspended_providers': fields.Integer(description='Suspended providers'),
    'pending_verification_providers': fields.Integer(description='Providers pending verification')
})

dashboard_services_summary_model = admin_ns.model('DashboardServicesSummary', {
    'total_services': fields.Integer(description='Total number of services'),
    'active_services': fields.Integer(description='Active services'),
    'inactive_services': fields.Integer(description='Inactive services')
})

dashboard_bookings_summary_model = admin_ns.model('DashboardBookingsSummary', {
    'total_bookings': fields.Integer(description='Total number of bookings'),
    'pending_bookings': fields.Integer(description='Pending bookings'),
    'confirmed_bookings': fields.Integer(description='Confirmed bookings'),
    'completed_bookings': fields.Integer(description='Completed bookings'),
    'cancelled_bookings': fields.Integer(description='Cancelled bookings')
})

dashboard_sales_summary_model = admin_ns.model('DashboardSalesSummary', {
    'total_sales': fields.Float(description='Total sales revenue (from paid bookings)'),
    'total_paid_bookings': fields.Integer(description='Total number of paid bookings'),
    'pending_payments': fields.Integer(description='Number of pending payments'),
    'failed_payments': fields.Integer(description='Number of failed payments')
})

dashboard_summary_model = admin_ns.model('DashboardSummary', {
    'users': fields.Nested(dashboard_users_summary_model, description='Users summary'),
    'providers': fields.Nested(dashboard_providers_summary_model, description='Providers summary'),
    'services': fields.Nested(dashboard_services_summary_model, description='Services summary'),
    'bookings': fields.Nested(dashboard_bookings_summary_model, description='Bookings summary'),
    'sales': fields.Nested(dashboard_sales_summary_model, description='Sales summary')
})

# Helper decorator for superadmin-only access
def superadmin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import get_jwt
        current_identity = get_jwt_identity()
        claims = get_jwt()

        # Check if user is an admin
        if claims.get('user_type') != 'admin':
            return {'error': 'Access denied. Admin authentication required.'}, 403

        # Check if admin is a superadmin
        admin_id = int(current_identity)
        admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

        if not admin:
            return {'error': 'Admin not found or has been deleted'}, 404

        if not admin.is_active:
            return {'error': 'Admin account is inactive'}, 403

        if admin.role != 'superadmin':
            return {'error': 'Access denied. Superadmin privileges required.'}, 403

        return fn(*args, **kwargs)
    return wrapper

# Helper decorator for admin authentication
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import get_jwt
        current_identity = get_jwt_identity()
        claims = get_jwt()

        # Check if user is an admin
        if claims.get('user_type') != 'admin':
            return {'error': 'Access denied. Admin authentication required.'}, 403

        # Check if admin exists and is active
        admin_id = int(current_identity)
        admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

        if not admin:
            return {'error': 'Admin not found or has been deleted'}, 404

        if not admin.is_active:
            return {'error': 'Admin account is inactive'}, 403

        return fn(*args, **kwargs)
    return wrapper

# Routes
@admin_ns.route('/register')
class AdminRegister(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.expect(register_model)
    @admin_ns.response(201, 'Admin created successfully', register_response_model)
    @admin_ns.response(400, 'Bad Request', error_model)
    @admin_ns.response(403, 'Forbidden - Superadmin access required', error_model)
    @admin_ns.response(409, 'Email already exists', error_model)
    @superadmin_required
    def post(self):
        """Create a new admin account (Superadmin only)"""
        try:
            data = request.get_json()

            # Validate required fields
            if not data:
                return {'error': 'Request body is required'}, 400

            if not data.get('full_name'):
                return {'error': 'full_name is required'}, 400

            if not data.get('email'):
                return {'error': 'email is required'}, 400

            if not data.get('password'):
                return {'error': 'password is required'}, 400

            # Check if email already exists
            existing_admin = Admin.query.filter_by(email=data['email'], is_deleted=False).first()
            if existing_admin:
                return {'error': 'Email already exists'}, 409

            # Create new admin
            new_admin = Admin(
                full_name=data['full_name'],
                email=data['email'],
                role=data.get('role', 'admin'),
                address=data.get('address')
            )
            new_admin.set_password(data['password'])

            db.session.add(new_admin)
            db.session.commit()

            return {
                'message': 'Admin account created successfully',
                'admin': {
                    'admin_id': new_admin.admin_id,
                    'full_name': new_admin.full_name,
                    'email': new_admin.email,
                    'role': new_admin.role,
                    'address': new_admin.address,
                    'date_created': new_admin.date_created.isoformat() if new_admin.date_created else None,
                    'date_modified': new_admin.date_modified.isoformat() if new_admin.date_modified else None,
                    'last_login': new_admin.last_login.isoformat() if new_admin.last_login else None,
                    'is_active': new_admin.is_active,
                    'is_deleted': new_admin.is_deleted
                }
            }, 201

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to create admin account: {str(e)}'}, 500

@admin_ns.route('/login')
class AdminLogin(Resource):
    @admin_ns.expect(login_model)
    @admin_ns.response(200, 'Login successful', login_response_model)
    @admin_ns.response(400, 'Bad Request', error_model)
    @admin_ns.response(401, 'Invalid credentials', error_model)
    @admin_ns.response(403, 'Account inactive or deleted', error_model)
    def post(self):
        """Admin login"""
        try:
            data = request.get_json()

            # Validate required fields
            if not data:
                return {'error': 'Request body is required'}, 400

            if not data.get('email'):
                return {'error': 'email is required'}, 400

            if not data.get('password'):
                return {'error': 'password is required'}, 400

            # Find admin by email
            admin = Admin.query.filter_by(email=data['email'], is_deleted=False).first()

            if not admin:
                return {'error': 'Invalid email or password'}, 401

            # Check if account is active
            if not admin.is_active:
                return {'error': 'Account is inactive. Please contact a superadmin.'}, 403

            # Verify password
            if not admin.check_password(data['password']):
                return {'error': 'Invalid email or password'}, 401

            # Update last login
            admin.last_login = datetime.utcnow()
            db.session.commit()

            # Create access token with admin type
            access_token = create_access_token(
                identity=str(admin.admin_id),
                additional_claims={'user_type': 'admin', 'role': admin.role}
            )

            return {
                'access_token': access_token,
                'message': 'Login successful',
                'admin': {
                    'admin_id': admin.admin_id,
                    'full_name': admin.full_name,
                    'email': admin.email,
                    'role': admin.role,
                    'address': admin.address,
                    'date_created': admin.date_created.isoformat() if admin.date_created else None,
                    'date_modified': admin.date_modified.isoformat() if admin.date_modified else None,
                    'last_login': admin.last_login.isoformat() if admin.last_login else None,
                    'is_active': admin.is_active,
                    'is_deleted': admin.is_deleted
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Login failed: {str(e)}'}, 500

@admin_ns.route('/profile')
class AdminProfile(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_with(admin_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden', error_model)
    @admin_ns.response(404, 'Admin not found', error_model)
    @admin_required
    def get(self):
        """Get current admin profile"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            admin_id = int(current_identity)

            admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

            if not admin:
                return {'error': 'Admin not found'}, 404

            return {
                'admin_id': admin.admin_id,
                'full_name': admin.full_name,
                'email': admin.email,
                'role': admin.role,
                'address': admin.address,
                'date_created': admin.date_created.isoformat() if admin.date_created else None,
                'date_modified': admin.date_modified.isoformat() if admin.date_modified else None,
                'last_login': admin.last_login.isoformat() if admin.last_login else None,
                'is_active': admin.is_active,
                'is_deleted': admin.is_deleted
            }

        except Exception as e:
            return {'error': f'Failed to get profile: {str(e)}'}, 500

@admin_ns.route('/dashboard/summary')
class DashboardSummary(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_with(dashboard_summary_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get dashboard summary with total counts for users, providers, services, bookings, and sales"""
        try:
            # Users Summary
            total_users = User.query.count()
            active_users = User.query.filter_by(status='active').count()
            inactive_users = User.query.filter_by(status='inactive').count()
            suspended_users = User.query.filter_by(status='suspended').count()
            pending_verification_users = User.query.filter_by(status='for_verification').count()

            # Providers Summary
            total_providers = Provider.query.count()
            active_providers = Provider.query.filter_by(status='active').count()
            inactive_providers = Provider.query.filter_by(status='inactive').count()
            suspended_providers = Provider.query.filter_by(status='suspended').count()
            pending_verification_providers = Provider.query.filter_by(status='for_verification').count()

            # Services Summary
            total_services = ProviderService.query.count()
            active_services = ProviderService.query.filter_by(is_active=True).count()
            inactive_services = ProviderService.query.filter_by(is_active=False).count()

            # Bookings Summary
            total_bookings = ServiceBooking.query.count()
            pending_bookings = ServiceBooking.query.filter_by(status='Pending').count()
            confirmed_bookings = ServiceBooking.query.filter_by(status='Confirmed').count()
            completed_bookings = ServiceBooking.query.filter_by(status='Completed').count()
            cancelled_bookings = ServiceBooking.query.filter_by(status='Cancelled').count()

            # Sales Summary - Calculate from paid bookings
            paid_payments = db.session.query(
                PaymentStatus,
                ProviderService
            ).join(
                ServiceBooking, PaymentStatus.booking_id == ServiceBooking.id
            ).join(
                ProviderService, ServiceBooking.provider_service_id == ProviderService.id
            ).filter(
                PaymentStatus.status == 'Paid'
            ).all()

            total_sales = 0
            for payment, service in paid_payments:
                if service.price_decimal:
                    total_sales += float(service.price_decimal)

            total_paid_bookings = len(paid_payments)

            # Count payment statuses
            pending_payments = PaymentStatus.query.filter_by(status='Pending').count()
            failed_payments = PaymentStatus.query.filter_by(status='Failed').count()

            return {
                'users': {
                    'total_users': total_users,
                    'active_users': active_users,
                    'inactive_users': inactive_users,
                    'suspended_users': suspended_users,
                    'pending_verification_users': pending_verification_users
                },
                'providers': {
                    'total_providers': total_providers,
                    'active_providers': active_providers,
                    'inactive_providers': inactive_providers,
                    'suspended_providers': suspended_providers,
                    'pending_verification_providers': pending_verification_providers
                },
                'services': {
                    'total_services': total_services,
                    'active_services': active_services,
                    'inactive_services': inactive_services
                },
                'bookings': {
                    'total_bookings': total_bookings,
                    'pending_bookings': pending_bookings,
                    'confirmed_bookings': confirmed_bookings,
                    'completed_bookings': completed_bookings,
                    'cancelled_bookings': cancelled_bookings
                },
                'sales': {
                    'total_sales': round(total_sales, 2),
                    'total_paid_bookings': total_paid_bookings,
                    'pending_payments': pending_payments,
                    'failed_payments': failed_payments
                }
            }

        except Exception as e:
            return {'error': f'Failed to get dashboard summary: {str(e)}'}, 500

@admin_ns.route('/list')
class AdminList(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_list_with(admin_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get list of all admins (Admin access required)"""
        try:
            admins = Admin.query.filter_by(is_deleted=False).all()

            result = []
            for admin in admins:
                result.append({
                    'admin_id': admin.admin_id,
                    'full_name': admin.full_name,
                    'email': admin.email,
                    'role': admin.role,
                    'address': admin.address,
                    'date_created': admin.date_created.isoformat() if admin.date_created else None,
                    'date_modified': admin.date_modified.isoformat() if admin.date_modified else None,
                    'last_login': admin.last_login.isoformat() if admin.last_login else None,
                    'is_active': admin.is_active,
                    'is_deleted': admin.is_deleted
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get admin list: {str(e)}'}, 500

@admin_ns.route('/providers')
class ProviderList(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_list_with(provider_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get list of all providers (Admin access required)"""
        try:
            # Get query parameters for filtering
            status_filter = request.args.get('status')
            is_active_filter = request.args.get('is_active')

            query = Provider.query

            # Apply filters if provided
            if status_filter:
                query = query.filter_by(status=status_filter)
            if is_active_filter is not None:
                is_active = is_active_filter.lower() == 'true'
                query = query.filter_by(is_active=is_active)

            providers = query.all()

            result = []
            for provider in providers:
                result.append({
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
                    'status': provider.status,
                    'created_at': provider.created_at.isoformat() if provider.created_at else None,
                    'updated_at': provider.updated_at.isoformat() if provider.updated_at else None
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get provider list: {str(e)}'}, 500

@admin_ns.route('/providers/<int:provider_id>/approve')
class ProviderApprove(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.response(200, 'Provider approved successfully', success_model)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'Provider not found', error_model)
    @jwt_required(optional=True)
    def options(self, provider_id):
        """Handle preflight OPTIONS request"""
        return {}, 200

    @jwt_required()
    def post(self, provider_id):
        """Approve provider (set status to active) - Admin access required"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            claims = get_jwt()

            # Check if user is an admin
            if claims.get('user_type') != 'admin':
                return {'error': 'Access denied. Admin authentication required.'}, 403

            # Get current admin
            admin_id = int(current_identity)
            admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

            if not admin:
                return {'error': 'Admin not found or has been deleted'}, 404

            if not admin.is_active:
                return {'error': 'Admin account is inactive'}, 403

            # Find provider
            provider = Provider.query.get(provider_id)

            if not provider:
                return {'error': 'Provider not found'}, 404

            # Update status to active
            old_status = provider.status
            provider.status = 'active'
            provider.is_active = True

            db.session.commit()

            # Send email notification
            try:
                if old_status == 'for_verification':
                    email_result = send_provider_verification_email(
                        provider.email,
                        provider.full_name,
                        provider.business_name
                    )
                else:
                    email_result = send_account_status_change_email(
                        provider.email,
                        provider.full_name,
                        'active',
                        account_type='provider',
                        business_name=provider.business_name
                    )

                if email_result and not email_result['success']:
                    print(f"Warning: Failed to send email to {provider.email}: {email_result['message']}")
            except Exception as e:
                print(f"Warning: Error sending email: {str(e)}")

            return {
                'message': f'Provider approved successfully. Status updated from {old_status} to active',
                'provider': {
                    'id': provider.id,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'status': provider.status,
                    'is_active': provider.is_active
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to approve provider: {str(e)}'}, 500

@admin_ns.route('/providers/<int:provider_id>/status')
class ProviderStatus(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.expect(update_status_model)
    @admin_ns.response(200, 'Status updated successfully', success_model)
    @admin_ns.response(400, 'Bad Request', error_model)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin/Superadmin access required', error_model)
    @admin_ns.response(404, 'Provider not found', error_model)
    @jwt_required()
    def patch(self, provider_id):
        """Update provider status (Admin/Superadmin can update to any status)"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            claims = get_jwt()

            # Check if user is an admin
            if claims.get('user_type') != 'admin':
                return {'error': 'Access denied. Admin authentication required.'}, 403

            # Get current admin
            admin_id = int(current_identity)
            admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

            if not admin:
                return {'error': 'Admin not found or has been deleted'}, 404

            if not admin.is_active:
                return {'error': 'Admin account is inactive'}, 403

            # Get request data
            data = request.get_json()

            if not data:
                return {'error': 'Request body is required'}, 400

            if not data.get('status'):
                return {'error': 'status is required'}, 400

            new_status = data['status']

            # Validate status value
            if new_status not in ['active', 'inactive', 'suspended', 'for_verification']:
                return {'error': 'Invalid status. Must be: active, inactive, suspended, or for_verification'}, 400

            # Role-based permissions
            # Moderators can only set to 'inactive'
            # Admins can set to 'active' or 'inactive'
            # Superadmins can set to any status including 'suspended'
            if admin.role == 'moderator' and new_status != 'inactive':
                return {'error': 'Moderators can only set status to inactive'}, 403

            if admin.role == 'admin' and new_status == 'suspended':
                return {'error': 'Only superadmins can suspend providers'}, 403

            # Find provider
            provider = Provider.query.get(provider_id)

            if not provider:
                return {'error': 'Provider not found'}, 404

            # Update status
            old_status = provider.status
            provider.status = new_status

            # Also update is_active based on status
            if new_status in ['inactive', 'suspended']:
                provider.is_active = False
            else:
                provider.is_active = True

            db.session.commit()

            # Send email notification for status change
            try:
                # Special verification email for initial approval
                if new_status == 'active' and old_status == 'for_verification':
                    email_result = send_provider_verification_email(
                        provider.email,
                        provider.full_name,
                        provider.business_name
                    )
                # Generic status change email for other transitions
                elif new_status in ['active', 'inactive', 'suspended'] and old_status != 'for_verification':
                    email_result = send_account_status_change_email(
                        provider.email,
                        provider.full_name,
                        new_status,
                        account_type='provider',
                        business_name=provider.business_name
                    )
                else:
                    email_result = None

                if email_result and not email_result['success']:
                    print(f"Warning: Failed to send email to {provider.email}: {email_result['message']}")
            except Exception as e:
                print(f"Warning: Error sending email: {str(e)}")

            return {
                'message': f'Provider status updated from {old_status} to {new_status}',
                'provider': {
                    'id': provider.id,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'status': provider.status,
                    'is_active': provider.is_active
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update provider status: {str(e)}'}, 500

@admin_ns.route('/users')
class UserList(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_list_with(user_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get list of all users (Admin access required)"""
        try:
            # Get query parameters for filtering
            status_filter = request.args.get('status')

            query = User.query

            # Apply filters if provided
            if status_filter:
                query = query.filter_by(status=status_filter)

            users = query.all()

            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'id_front': user.id_front,
                    'id_back': user.id_back,
                    'status': user.status,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get user list: {str(e)}'}, 500

@admin_ns.route('/users/<int:user_id>/approve')
class UserApprove(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.response(200, 'User approved successfully', success_model)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'User not found', error_model)
    @jwt_required(optional=True)
    def options(self, user_id):
        """Handle preflight OPTIONS request"""
        return {}, 200

    @jwt_required()
    def post(self, user_id):
        """Approve user (set status to active) - Admin access required"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            claims = get_jwt()

            # Check if user is an admin
            if claims.get('user_type') != 'admin':
                return {'error': 'Access denied. Admin authentication required.'}, 403

            # Get current admin
            admin_id = int(current_identity)
            admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

            if not admin:
                return {'error': 'Admin not found or has been deleted'}, 404

            if not admin.is_active:
                return {'error': 'Admin account is inactive'}, 403

            # Find user
            user = User.query.get(user_id)

            if not user:
                return {'error': 'User not found'}, 404

            # Update status to active
            old_status = user.status
            user.status = 'active'

            db.session.commit()

            # Send email notification
            try:
                if old_status == 'for_verification':
                    email_result = send_user_verification_email(
                        user.email,
                        user.full_name
                    )
                else:
                    email_result = send_account_status_change_email(
                        user.email,
                        user.full_name,
                        'active',
                        account_type='user'
                    )

                if email_result and not email_result['success']:
                    print(f"Warning: Failed to send email to {user.email}: {email_result['message']}")
            except Exception as e:
                print(f"Warning: Error sending email: {str(e)}")

            return {
                'message': f'User approved successfully. Status updated from {old_status} to active',
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'status': user.status
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to approve user: {str(e)}'}, 500

@admin_ns.route('/users/<int:user_id>/status')
class UserStatus(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.expect(update_user_status_model)
    @admin_ns.response(200, 'Status updated successfully', success_model)
    @admin_ns.response(400, 'Bad Request', error_model)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin/Superadmin access required', error_model)
    @admin_ns.response(404, 'User not found', error_model)
    @jwt_required()
    def patch(self, user_id):
        """Update user status (Role-based permissions apply)"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            claims = get_jwt()

            # Check if user is an admin
            if claims.get('user_type') != 'admin':
                return {'error': 'Access denied. Admin authentication required.'}, 403

            # Get current admin
            admin_id = int(current_identity)
            admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

            if not admin:
                return {'error': 'Admin not found or has been deleted'}, 404

            if not admin.is_active:
                return {'error': 'Admin account is inactive'}, 403

            # Get request data
            data = request.get_json()

            if not data:
                return {'error': 'Request body is required'}, 400

            if not data.get('status'):
                return {'error': 'status is required'}, 400

            new_status = data['status']

            # Validate status value
            if new_status not in ['active', 'inactive', 'suspended', 'for_verification']:
                return {'error': 'Invalid status. Must be: active, inactive, suspended, or for_verification'}, 400

            # Role-based permissions
            # Moderators can only set to 'inactive'
            # Admins can set to 'active' or 'inactive'
            # Superadmins can set to any status including 'suspended'
            if admin.role == 'moderator' and new_status != 'inactive':
                return {'error': 'Moderators can only set status to inactive'}, 403

            if admin.role == 'admin' and new_status == 'suspended':
                return {'error': 'Only superadmins can suspend users'}, 403

            # Find user
            user = User.query.get(user_id)

            if not user:
                return {'error': 'User not found'}, 404

            # Update status
            old_status = user.status
            user.status = new_status

            db.session.commit()

            # Send email notification for status change
            try:
                # Special verification email for initial approval
                if new_status == 'active' and old_status == 'for_verification':
                    email_result = send_user_verification_email(
                        user.email,
                        user.full_name
                    )
                # Generic status change email for other transitions
                elif new_status in ['active', 'inactive', 'suspended'] and old_status != 'for_verification':
                    email_result = send_account_status_change_email(
                        user.email,
                        user.full_name,
                        new_status,
                        account_type='user'
                    )
                else:
                    email_result = None

                if email_result and not email_result['success']:
                    print(f"Warning: Failed to send email to {user.email}: {email_result['message']}")
            except Exception as e:
                print(f"Warning: Error sending email: {str(e)}")

            return {
                'message': f'User status updated from {old_status} to {new_status}',
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'status': user.status
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update user status: {str(e)}'}, 500

@admin_ns.route('/services')
class ServiceList(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_list_with(service_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get list of all services from all providers with full details (Admin access required)"""
        try:
            # Get query parameters for filtering
            provider_id = request.args.get('provider_id', type=int)
            category_id = request.args.get('category_id', type=int)
            is_active = request.args.get('is_active')

            query = ProviderService.query

            # Apply filters if provided
            if provider_id:
                query = query.filter_by(provider_id=provider_id)
            if category_id:
                query = query.filter_by(category_id=category_id)
            if is_active is not None:
                is_active_bool = is_active.lower() == 'true'
                query = query.filter_by(is_active=is_active_bool)

            services = query.all()

            result = []
            for service in services:
                # Get provider details
                provider = Provider.query.get(service.provider_id)
                provider_data = None
                if provider:
                    provider_data = {
                        'id': provider.id,
                        'business_name': provider.business_name,
                        'full_name': provider.full_name,
                        'email': provider.email,
                        'contact_number': provider.contact_number,
                        'address': provider.address,
                        'image_logo': provider.image_logo,
                        'about': provider.about,
                        'is_active': provider.is_active,
                        'status': provider.status
                    }

                # Get category details
                category = ServiceCategory.query.get(service.category_id)
                category_data = None
                if category:
                    category_data = {
                        'id': category.id,
                        'category_name': category.category_name,
                        'description': category.description
                    }

                # Get service photos
                photos = ProviderServicePhoto.query.filter_by(provider_service_id=service.id).order_by(ProviderServicePhoto.sort_order).all()
                photos_data = []
                for photo in photos:
                    photos_data.append({
                        'id': photo.id,
                        'photo_url': photo.photo_url,
                        'sort_order': photo.sort_order
                    })

                # Get service schedules
                schedules = ProviderServiceSchedule.query.filter_by(provider_service_id=service.id).all()
                schedules_data = []
                for schedule in schedules:
                    schedules_data.append({
                        'id': schedule.id,
                        'schedule_day': schedule.schedule_day,
                        'start_time': str(schedule.start_time) if schedule.start_time else None,
                        'end_time': str(schedule.end_time) if schedule.end_time else None
                    })

                result.append({
                    'id': service.id,
                    'provider_id': service.provider_id,
                    'category_id': service.category_id,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes,
                    'is_active': service.is_active,
                    'created_at': service.created_at.isoformat() if service.created_at else None,
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None,
                    'provider': provider_data,
                    'category': category_data,
                    'photos': photos_data,
                    'schedules': schedules_data
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get service list: {str(e)}'}, 500

@admin_ns.route('/services/<int:service_id>/status')
class ServiceStatus(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.expect(update_service_status_model)
    @admin_ns.response(200, 'Status updated successfully', success_model)
    @admin_ns.response(400, 'Bad Request', error_model)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin/Superadmin access required', error_model)
    @admin_ns.response(404, 'Service not found', error_model)
    @jwt_required()
    def patch(self, service_id):
        """Update service active status (Role-based permissions apply)"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            claims = get_jwt()

            # Check if user is an admin
            if claims.get('user_type') != 'admin':
                return {'error': 'Access denied. Admin authentication required.'}, 403

            # Get current admin
            admin_id = int(current_identity)
            admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

            if not admin:
                return {'error': 'Admin not found or has been deleted'}, 404

            if not admin.is_active:
                return {'error': 'Admin account is inactive'}, 403

            # Get request data
            data = request.get_json()

            if not data:
                return {'error': 'Request body is required'}, 400

            if 'is_active' not in data:
                return {'error': 'is_active is required'}, 400

            new_status = data['is_active']

            # Validate status value
            if not isinstance(new_status, bool):
                return {'error': 'Invalid is_active value. Must be true or false'}, 400

            # Role-based permissions
            # All admins (moderator, admin, superadmin) can toggle service status
            # But only superadmin and admin can activate services
            # Moderators can only deactivate services
            if admin.role == 'moderator' and new_status == True:
                return {'error': 'Moderators can only deactivate services'}, 403

            # Find service
            service = ProviderService.query.get(service_id)

            if not service:
                return {'error': 'Service not found'}, 404

            # Update is_active status
            old_status = service.is_active
            service.is_active = new_status

            db.session.commit()

            # Get provider details
            provider = Provider.query.get(service.provider_id)
            provider_data = None
            if provider:
                provider_data = {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'status': provider.status
                }

            # Get category details
            category = ServiceCategory.query.get(service.category_id)
            category_data = None
            if category:
                category_data = {
                    'id': category.id,
                    'category_name': category.category_name,
                    'description': category.description
                }

            # Get service photos
            photos = ProviderServicePhoto.query.filter_by(provider_service_id=service.id).order_by(ProviderServicePhoto.sort_order).all()
            photos_data = []
            for photo in photos:
                photos_data.append({
                    'id': photo.id,
                    'photo_url': photo.photo_url,
                    'sort_order': photo.sort_order
                })

            # Get service schedules
            schedules = ProviderServiceSchedule.query.filter_by(provider_service_id=service.id).all()
            schedules_data = []
            for schedule in schedules:
                schedules_data.append({
                    'id': schedule.id,
                    'schedule_day': schedule.schedule_day,
                    'start_time': str(schedule.start_time) if schedule.start_time else None,
                    'end_time': str(schedule.end_time) if schedule.end_time else None
                })

            return {
                'message': f'Service status updated from {old_status} to {new_status}',
                'service': {
                    'id': service.id,
                    'provider_id': service.provider_id,
                    'category_id': service.category_id,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes,
                    'is_active': service.is_active,
                    'created_at': service.created_at.isoformat() if service.created_at else None,
                    'updated_at': service.updated_at.isoformat() if service.updated_at else None,
                    'provider': provider_data,
                    'category': category_data,
                    'photos': photos_data,
                    'schedules': schedules_data
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update service status: {str(e)}'}, 500

@admin_ns.route('/bookings')
class BookingList(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_list_with(booking_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get list of all bookings with full details (Admin access required)"""
        try:
            # Get query parameters for filtering
            user_id = request.args.get('user_id', type=int)
            provider_id = request.args.get('provider_id', type=int)
            status_filter = request.args.get('status')
            booking_date = request.args.get('booking_date')

            query = ServiceBooking.query

            # Apply filters if provided
            if user_id:
                query = query.filter_by(user_id=user_id)
            if provider_id:
                query = query.filter_by(provider_id=provider_id)
            if status_filter:
                query = query.filter_by(status=status_filter)
            if booking_date:
                query = query.filter_by(booking_date=booking_date)

            # Order by created_at descending (newest first)
            bookings = query.order_by(ServiceBooking.created_at.desc()).all()

            result = []
            for booking in bookings:
                # Get user details
                user = User.query.get(booking.user_id)
                user_data = None
                if user:
                    user_data = {
                        'id': user.id,
                        'full_name': user.full_name,
                        'email': user.email,
                        'address': user.address,
                        'status': user.status
                    }

                # Get provider details
                provider = Provider.query.get(booking.provider_id)
                provider_data = None
                if provider:
                    provider_data = {
                        'id': provider.id,
                        'business_name': provider.business_name,
                        'full_name': provider.full_name,
                        'email': provider.email,
                        'contact_number': provider.contact_number,
                        'address': provider.address,
                        'image_logo': provider.image_logo,
                        'about': provider.about,
                        'is_active': provider.is_active,
                        'status': provider.status
                    }

                # Get service details
                service = ProviderService.query.get(booking.provider_service_id)
                service_data = None
                if service:
                    service_data = {
                        'id': service.id,
                        'service_title': service.service_title,
                        'service_description': service.service_description,
                        'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                        'duration_minutes': service.duration_minutes
                    }

                result.append({
                    'id': booking.id,
                    'user_id': booking.user_id,
                    'provider_id': booking.provider_id,
                    'provider_service_id': booking.provider_service_id,
                    'booking_date': str(booking.booking_date) if booking.booking_date else None,
                    'booking_day': booking.booking_day,
                    'booking_time': str(booking.booking_time) if booking.booking_time else None,
                    'status': booking.status,
                    'created_at': booking.created_at.isoformat() if booking.created_at else None,
                    'updated_at': booking.updated_at.isoformat() if booking.updated_at else None,
                    'user': user_data,
                    'provider': provider_data,
                    'service': service_data
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get booking list: {str(e)}'}, 500

@admin_ns.route('/bookings/<int:booking_id>')
class BookingDetail(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_with(booking_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'Booking not found', error_model)
    @admin_required
    def get(self, booking_id):
        """Get single booking details (Admin access required)"""
        try:
            booking = ServiceBooking.query.get(booking_id)

            if not booking:
                return {'error': 'Booking not found'}, 404

            # Get user details
            user = User.query.get(booking.user_id)
            user_data = None
            if user:
                user_data = {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'status': user.status
                }

            # Get provider details
            provider = Provider.query.get(booking.provider_id)
            provider_data = None
            if provider:
                provider_data = {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'status': provider.status
                }

            # Get service details
            service = ProviderService.query.get(booking.provider_service_id)
            service_data = None
            if service:
                service_data = {
                    'id': service.id,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes
                }

            return {
                'id': booking.id,
                'user_id': booking.user_id,
                'provider_id': booking.provider_id,
                'provider_service_id': booking.provider_service_id,
                'booking_date': str(booking.booking_date) if booking.booking_date else None,
                'booking_day': booking.booking_day,
                'booking_time': str(booking.booking_time) if booking.booking_time else None,
                'status': booking.status,
                'created_at': booking.created_at.isoformat() if booking.created_at else None,
                'updated_at': booking.updated_at.isoformat() if booking.updated_at else None,
                'user': user_data,
                'provider': provider_data,
                'service': service_data
            }

        except Exception as e:
            return {'error': f'Failed to get booking details: {str(e)}'}, 500

@admin_ns.route('/bookings/<int:booking_id>/status')
class BookingStatus(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.expect(update_booking_status_model)
    @admin_ns.response(200, 'Status updated successfully', success_model)
    @admin_ns.response(400, 'Bad Request', error_model)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'Booking not found', error_model)
    @jwt_required()
    def patch(self, booking_id):
        """Update booking status (Role-based permissions apply)"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            claims = get_jwt()

            # Check if user is an admin
            if claims.get('user_type') != 'admin':
                return {'error': 'Access denied. Admin authentication required.'}, 403

            # Get current admin
            admin_id = int(current_identity)
            admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

            if not admin:
                return {'error': 'Admin not found or has been deleted'}, 404

            if not admin.is_active:
                return {'error': 'Admin account is inactive'}, 403

            # Get request data
            data = request.get_json()

            if not data:
                return {'error': 'Request body is required'}, 400

            if not data.get('status'):
                return {'error': 'status is required'}, 400

            new_status = data['status']

            # Validate status value
            if new_status not in ['Pending', 'Confirmed', 'Completed', 'Cancelled']:
                return {'error': 'Invalid status. Must be: Pending, Confirmed, Completed, or Cancelled'}, 400

            # Role-based permissions
            # Moderators can update to any status
            # Admins and Superadmins have full control

            # Find booking
            booking = ServiceBooking.query.get(booking_id)

            if not booking:
                return {'error': 'Booking not found'}, 404

            # Update status
            old_status = booking.status
            booking.status = new_status

            db.session.commit()

            # Get user details
            user = User.query.get(booking.user_id)
            user_data = None
            if user:
                user_data = {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'status': user.status
                }

            # Get provider details
            provider = Provider.query.get(booking.provider_id)
            provider_data = None
            if provider:
                provider_data = {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'status': provider.status
                }

            # Get service details
            service = ProviderService.query.get(booking.provider_service_id)
            service_data = None
            if service:
                service_data = {
                    'id': service.id,
                    'service_title': service.service_title,
                    'service_description': service.service_description,
                    'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                    'duration_minutes': service.duration_minutes
                }

            return {
                'message': f'Booking status updated from {old_status} to {new_status}',
                'booking': {
                    'id': booking.id,
                    'user_id': booking.user_id,
                    'provider_id': booking.provider_id,
                    'provider_service_id': booking.provider_service_id,
                    'booking_date': str(booking.booking_date) if booking.booking_date else None,
                    'booking_day': booking.booking_day,
                    'booking_time': str(booking.booking_time) if booking.booking_time else None,
                    'status': booking.status,
                    'created_at': booking.created_at.isoformat() if booking.created_at else None,
                    'updated_at': booking.updated_at.isoformat() if booking.updated_at else None,
                    'user': user_data,
                    'provider': provider_data,
                    'service': service_data
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update booking status: {str(e)}'}, 500

@admin_ns.route('/sales-report')
class SalesReport(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_with(overall_sales_summary_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get overall sales report for all providers (Admin access required)

        Query parameters:
        - start_date: Filter from date (YYYY-MM-DD)
        - end_date: Filter to date (YYYY-MM-DD)
        """
        try:
            # Get query parameters for date filtering
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            # Base query: Get all paid bookings with service details
            query = db.session.query(
                ServiceBooking,
                PaymentStatus,
                ProviderService
            ).join(
                PaymentStatus, ServiceBooking.id == PaymentStatus.booking_id
            ).join(
                ProviderService, ServiceBooking.provider_service_id == ProviderService.id
            ).filter(
                PaymentStatus.status == 'Paid'
            )

            # Apply date filters if provided
            if start_date:
                query = query.filter(ServiceBooking.booking_date >= start_date)
            if end_date:
                query = query.filter(ServiceBooking.booking_date <= end_date)

            paid_bookings = query.all()

            # Group by provider
            provider_data = {}
            total_revenue = 0

            for booking, payment, service in paid_bookings:
                provider_id = booking.provider_id
                price = float(service.price_decimal) if service.price_decimal else 0
                total_revenue += price

                if provider_id not in provider_data:
                    provider = Provider.query.get(provider_id)
                    provider_data[provider_id] = {
                        'provider': provider,
                        'total_revenue': 0,
                        'total_bookings': 0,
                        'completed_bookings': 0,
                        'pending_bookings': 0,
                        'cancelled_bookings': 0
                    }

                provider_data[provider_id]['total_revenue'] += price
                provider_data[provider_id]['total_bookings'] += 1

                # Count by booking status
                if booking.status == 'Completed':
                    provider_data[provider_id]['completed_bookings'] += 1
                elif booking.status == 'Pending':
                    provider_data[provider_id]['pending_bookings'] += 1
                elif booking.status == 'Cancelled':
                    provider_data[provider_id]['cancelled_bookings'] += 1

            # Build provider summaries
            providers_summary = []
            for provider_id, data in provider_data.items():
                provider = data['provider']
                providers_summary.append({
                    'provider_id': provider.id,
                    'business_name': provider.business_name,
                    'provider_name': provider.full_name,
                    'email': provider.email,
                    'total_bookings': data['total_bookings'],
                    'total_revenue': round(data['total_revenue'], 2),
                    'completed_bookings': data['completed_bookings'],
                    'pending_bookings': data['pending_bookings'],
                    'cancelled_bookings': data['cancelled_bookings']
                })

            # Sort by total revenue descending
            providers_summary.sort(key=lambda x: x['total_revenue'], reverse=True)

            return {
                'total_providers': len(provider_data),
                'total_revenue': round(total_revenue, 2),
                'total_bookings': len(paid_bookings),
                'providers': providers_summary
            }

        except Exception as e:
            return {'error': f'Failed to generate sales report: {str(e)}'}, 500

@admin_ns.route('/sales-report/provider/<int:provider_id>')
class ProviderSalesReport(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_with(sales_report_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'Provider not found', error_model)
    @admin_required
    def get(self, provider_id):
        """Get detailed sales report for a specific provider (Admin access required)

        Query parameters:
        - start_date: Filter from date (YYYY-MM-DD)
        - end_date: Filter to date (YYYY-MM-DD)
        """
        try:
            # Check if provider exists
            provider = Provider.query.get(provider_id)
            if not provider:
                return {'error': 'Provider not found'}, 404

            # Get query parameters for date filtering
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            # Query paid bookings for this provider
            query = db.session.query(
                ServiceBooking,
                PaymentStatus,
                ProviderService,
                User
            ).join(
                PaymentStatus, ServiceBooking.id == PaymentStatus.booking_id
            ).join(
                ProviderService, ServiceBooking.provider_service_id == ProviderService.id
            ).join(
                User, ServiceBooking.user_id == User.id
            ).filter(
                ServiceBooking.provider_id == provider_id,
                PaymentStatus.status == 'Paid'
            )

            # Apply date filters if provided
            if start_date:
                query = query.filter(ServiceBooking.booking_date >= start_date)
            if end_date:
                query = query.filter(ServiceBooking.booking_date <= end_date)

            paid_bookings = query.all()

            # Calculate summary statistics
            total_revenue = 0
            completed_count = 0
            pending_count = 0
            cancelled_count = 0
            booking_details = []

            for booking, payment, service, user in paid_bookings:
                price = float(service.price_decimal) if service.price_decimal else 0
                total_revenue += price

                # Count by status
                if booking.status == 'Completed':
                    completed_count += 1
                elif booking.status == 'Pending':
                    pending_count += 1
                elif booking.status == 'Cancelled':
                    cancelled_count += 1

                # Add booking detail
                booking_details.append({
                    'booking_id': booking.id,
                    'user_name': user.full_name,
                    'user_email': user.email,
                    'service_title': service.service_title,
                    'booking_date': str(booking.booking_date) if booking.booking_date else None,
                    'booking_time': str(booking.booking_time) if booking.booking_time else None,
                    'price': price,
                    'payment_status': payment.status,
                    'payment_date': payment.created_at.isoformat() if payment.created_at else None,
                    'booking_status': booking.status
                })

            # Sort bookings by date descending
            booking_details.sort(key=lambda x: x['booking_date'] or '', reverse=True)

            return {
                'provider': {
                    'provider_id': provider.id,
                    'business_name': provider.business_name,
                    'provider_name': provider.full_name,
                    'email': provider.email,
                    'total_bookings': len(paid_bookings),
                    'total_revenue': round(total_revenue, 2),
                    'completed_bookings': completed_count,
                    'pending_bookings': pending_count,
                    'cancelled_bookings': cancelled_count
                },
                'bookings': booking_details
            }

        except Exception as e:
            return {'error': f'Failed to generate provider sales report: {str(e)}'}, 500

@admin_ns.route('/reports')
class CustomerReportList(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_list_with(report_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get list of all customer reports/complaints (Admin access required)

        Query parameters:
        - user_id: Filter by user
        - provider_id: Filter by provider
        - status: Filter by status (Pending, Under Review, Resolved, Rejected)
        - report_type: Filter by type (service_quality, provider_behavior, payment_issue, cancellation, other)
        """
        try:
            # Get query parameters for filtering
            user_id = request.args.get('user_id', type=int)
            provider_id = request.args.get('provider_id', type=int)
            status_filter = request.args.get('status')
            report_type = request.args.get('report_type')

            query = CustomerReport.query

            # Apply filters if provided
            if user_id:
                query = query.filter_by(user_id=user_id)
            if provider_id:
                query = query.filter_by(provider_id=provider_id)
            if status_filter:
                query = query.filter_by(status=status_filter)
            if report_type:
                query = query.filter_by(report_type=report_type)

            # Order by created_at descending (newest first)
            reports = query.order_by(CustomerReport.created_at.desc()).all()

            result = []
            for report in reports:
                # Get user details
                user = User.query.get(report.user_id)
                user_data = None
                if user:
                    user_data = {
                        'id': user.id,
                        'full_name': user.full_name,
                        'email': user.email,
                        'address': user.address,
                        'status': user.status
                    }

                # Get provider details
                provider = Provider.query.get(report.provider_id)
                provider_data = None
                if provider:
                    provider_data = {
                        'id': provider.id,
                        'business_name': provider.business_name,
                        'full_name': provider.full_name,
                        'email': provider.email,
                        'contact_number': provider.contact_number,
                        'address': provider.address,
                        'image_logo': provider.image_logo,
                        'about': provider.about,
                        'is_active': provider.is_active,
                        'status': provider.status
                    }

                # Get service details if available
                service_data = None
                if report.provider_service_id:
                    service = ProviderService.query.get(report.provider_service_id)
                    if service:
                        service_data = {
                            'id': service.id,
                            'service_title': service.service_title,
                            'service_description': service.service_description,
                            'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                            'duration_minutes': service.duration_minutes
                        }

                # Get booking details if available
                booking_data = None
                if report.booking_id:
                    booking = ServiceBooking.query.get(report.booking_id)
                    if booking:
                        booking_data = {
                            'id': booking.id,
                            'booking_date': str(booking.booking_date) if booking.booking_date else None,
                            'booking_time': str(booking.booking_time) if booking.booking_time else None,
                            'status': booking.status
                        }

                result.append({
                    'id': report.id,
                    'user_id': report.user_id,
                    'provider_id': report.provider_id,
                    'provider_service_id': report.provider_service_id,
                    'booking_id': report.booking_id,
                    'report_type': report.report_type,
                    'subject': report.subject,
                    'description': report.description,
                    'status': report.status,
                    'admin_response': report.admin_response,
                    'admin_id': report.admin_id,
                    'created_at': report.created_at.isoformat() if report.created_at else None,
                    'updated_at': report.updated_at.isoformat() if report.updated_at else None,
                    'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None,
                    'user': user_data,
                    'provider': provider_data,
                    'service': service_data,
                    'booking': booking_data
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get report list: {str(e)}'}, 500

@admin_ns.route('/reports/<int:report_id>')
class CustomerReportDetail(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_with(report_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'Report not found', error_model)
    @admin_required
    def get(self, report_id):
        """Get single customer report/complaint details (Admin access required)"""
        try:
            report = CustomerReport.query.get(report_id)

            if not report:
                return {'error': 'Report not found'}, 404

            # Get user details
            user = User.query.get(report.user_id)
            user_data = None
            if user:
                user_data = {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'status': user.status
                }

            # Get provider details
            provider = Provider.query.get(report.provider_id)
            provider_data = None
            if provider:
                provider_data = {
                    'id': provider.id,
                    'business_name': provider.business_name,
                    'full_name': provider.full_name,
                    'email': provider.email,
                    'contact_number': provider.contact_number,
                    'address': provider.address,
                    'image_logo': provider.image_logo,
                    'about': provider.about,
                    'is_active': provider.is_active,
                    'status': provider.status
                }

            # Get service details if available
            service_data = None
            if report.provider_service_id:
                service = ProviderService.query.get(report.provider_service_id)
                if service:
                    service_data = {
                        'id': service.id,
                        'service_title': service.service_title,
                        'service_description': service.service_description,
                        'price_decimal': float(service.price_decimal) if service.price_decimal else None,
                        'duration_minutes': service.duration_minutes
                    }

            # Get booking details if available
            booking_data = None
            if report.booking_id:
                booking = ServiceBooking.query.get(report.booking_id)
                if booking:
                    booking_data = {
                        'id': booking.id,
                        'booking_date': str(booking.booking_date) if booking.booking_date else None,
                        'booking_time': str(booking.booking_time) if booking.booking_time else None,
                        'status': booking.status
                    }

            return {
                'id': report.id,
                'user_id': report.user_id,
                'provider_id': report.provider_id,
                'provider_service_id': report.provider_service_id,
                'booking_id': report.booking_id,
                'report_type': report.report_type,
                'subject': report.subject,
                'description': report.description,
                'status': report.status,
                'admin_response': report.admin_response,
                'admin_id': report.admin_id,
                'created_at': report.created_at.isoformat() if report.created_at else None,
                'updated_at': report.updated_at.isoformat() if report.updated_at else None,
                'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None,
                'user': user_data,
                'provider': provider_data,
                'service': service_data,
                'booking': booking_data
            }

        except Exception as e:
            return {'error': f'Failed to get report details: {str(e)}'}, 500

@admin_ns.route('/reports/<int:report_id>/status')
class CustomerReportStatus(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.expect(update_report_status_model)
    @admin_ns.response(200, 'Status updated successfully', success_model)
    @admin_ns.response(400, 'Bad Request', error_model)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'Report not found', error_model)
    @jwt_required()
    def patch(self, report_id):
        """Update customer report status and add admin response (Admin access required)"""
        try:
            from flask_jwt_extended import get_jwt
            current_identity = get_jwt_identity()
            claims = get_jwt()

            # Check if user is an admin
            if claims.get('user_type') != 'admin':
                return {'error': 'Access denied. Admin authentication required.'}, 403

            # Get current admin
            admin_id = int(current_identity)
            admin = Admin.query.filter_by(admin_id=admin_id, is_deleted=False).first()

            if not admin:
                return {'error': 'Admin not found or has been deleted'}, 404

            if not admin.is_active:
                return {'error': 'Admin account is inactive'}, 403

            # Get request data
            data = request.get_json()

            if not data:
                return {'error': 'Request body is required'}, 400

            if not data.get('status'):
                return {'error': 'status is required'}, 400

            new_status = data['status']
            admin_response = data.get('admin_response')

            # Validate status value
            if new_status not in ['Pending', 'Under Review', 'Resolved', 'Rejected']:
                return {'error': 'Invalid status. Must be: Pending, Under Review, Resolved, or Rejected'}, 400

            # Find report
            report = CustomerReport.query.get(report_id)

            if not report:
                return {'error': 'Report not found'}, 404

            # Update status and admin response
            old_status = report.status
            report.status = new_status
            report.admin_id = admin_id

            if admin_response:
                report.admin_response = admin_response

            # Set resolved_at if status is Resolved
            if new_status == 'Resolved' and not report.resolved_at:
                report.resolved_at = datetime.utcnow()

            db.session.commit()

            return {
                'message': f'Report status updated from {old_status} to {new_status}',
                'report': {
                    'id': report.id,
                    'status': report.status,
                    'admin_response': report.admin_response,
                    'admin_id': report.admin_id,
                    'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update report status: {str(e)}'}, 500

@admin_ns.route('/users/pending-verification')
class UsersPendingVerification(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_list_with(user_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get list of all users pending verification (status='for_verification')"""
        try:
            users = User.query.filter_by(status='for_verification').order_by(User.created_at.desc()).all()

            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'address': user.address,
                    'id_front': user.id_front,
                    'id_back': user.id_back,
                    'status': user.status,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get users pending verification: {str(e)}'}, 500

@admin_ns.route('/providers/pending-verification')
class ProvidersPendingVerification(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_list_with(provider_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_required
    def get(self):
        """Get list of all providers pending verification (status='for_verification')"""
        try:
            providers = Provider.query.filter_by(status='for_verification').order_by(Provider.created_at.desc()).all()

            result = []
            for provider in providers:
                result.append({
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
                    'status': provider.status,
                    'created_at': provider.created_at.isoformat() if provider.created_at else None,
                    'updated_at': provider.updated_at.isoformat() if provider.updated_at else None
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get providers pending verification: {str(e)}'}, 500

@admin_ns.route('/users/<int:user_id>')
class UserDetail(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_with(user_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'User not found', error_model)
    @admin_required
    def get(self, user_id):
        """Get specific user details including ID document images"""
        try:
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
                'status': user.status,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }

        except Exception as e:
            return {'error': f'Failed to get user details: {str(e)}'}, 500

@admin_ns.route('/providers/<int:provider_id>')
class ProviderDetail(Resource):
    @admin_ns.doc(security='Bearer')
    @admin_ns.marshal_with(provider_model, code=200)
    @admin_ns.response(401, 'Unauthorized', error_model)
    @admin_ns.response(403, 'Forbidden - Admin access required', error_model)
    @admin_ns.response(404, 'Provider not found', error_model)
    @admin_required
    def get(self, provider_id):
        """Get specific provider details including BIR ID, business permit, and logo images"""
        try:
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
                'status': provider.status,
                'created_at': provider.created_at.isoformat() if provider.created_at else None,
                'updated_at': provider.updated_at.isoformat() if provider.updated_at else None
            }

        except Exception as e:
            return {'error': f'Failed to get provider details: {str(e)}'}, 500
