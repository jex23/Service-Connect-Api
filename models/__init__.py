from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    address = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    id_front = db.Column(db.String(255), nullable=True)
    id_back = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum('active', 'inactive', 'suspended', name='user_status_enum'), nullable=False, default='active')
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class Provider(db.Model):
    __tablename__ = 'providers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    business_name = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    contact_number = db.Column(db.String(255), nullable=True)
    address = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bir_id_front = db.Column(db.String(255), nullable=True)
    bir_id_back = db.Column(db.String(255), nullable=True)
    business_permit = db.Column(db.String(255), nullable=True)
    image_logo = db.Column(db.String(255), nullable=True)
    about = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.Enum('active', 'inactive', 'suspended', name='provider_status_enum'), nullable=False, default='active')
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class ServiceCategory(db.Model):
    __tablename__ = 'service_categories'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProviderCategoryMembership(db.Model):
    __tablename__ = 'provider_category_membership'
    
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id'), primary_key=True)

class ProviderService(db.Model):
    __tablename__ = 'provider_services'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id'), nullable=False)
    service_title = db.Column(db.String(150), nullable=False)
    service_description = db.Column(db.Text, nullable=True)
    price_decimal = db.Column(db.DECIMAL(10, 2), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProviderServicePhoto(db.Model):
    __tablename__ = 'provider_service_photos'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    provider_service_id = db.Column(db.Integer, db.ForeignKey('provider_services.id'), nullable=False)
    photo_url = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

class UserServiceCategory(db.Model):
    __tablename__ = 'user_service_categories'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id'), nullable=False)
    service_title = db.Column(db.String(150), nullable=False)
    service_description = db.Column(db.Text, nullable=True)
    price_decimal = db.Column(db.DECIMAL(10, 2), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProviderServiceSchedule(db.Model):
    __tablename__ = 'provider_service_schedule'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    provider_service_id = db.Column(db.Integer, db.ForeignKey('provider_services.id'), nullable=False)
    schedule_day = db.Column(db.Enum('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', name='day_enum'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class ServiceBooking(db.Model):
    __tablename__ = 'service_booking'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    provider_service_id = db.Column(db.Integer, db.ForeignKey('provider_services.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    booking_day = db.Column(db.Enum('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', name='booking_day_enum'), nullable=False)
    booking_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.Enum('Pending', 'Confirmed', 'Completed', 'Cancelled', name='booking_status_enum'), nullable=False, default='Pending')
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentStatus(db.Model):
    __tablename__ = 'payment_status'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('service_booking.id'), nullable=False)
    status = db.Column(db.Enum('Pending', 'Paid', 'Failed', 'Cancelled', 'Refunded', name='payment_status_enum'), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatActor(db.Model):
    __tablename__ = 'chat_actors'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    actor_type = db.Column(db.Enum('user', 'provider', name='actor_type_enum'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

class ChatConversation(db.Model):
    __tablename__ = 'chat_conversations'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    is_group = db.Column(db.Boolean, nullable=False, default=False)
    title = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatConversationParticipant(db.Model):
    __tablename__ = 'chat_conversation_participants'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.BigInteger, db.ForeignKey('chat_conversations.id'), nullable=False)
    actor_id = db.Column(db.BigInteger, db.ForeignKey('chat_actors.id'), nullable=False)
    role = db.Column(db.Enum('member', 'admin', name='participant_role_enum'), nullable=False, default='member')
    joined_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    last_read_message_id = db.Column(db.BigInteger, nullable=True)
    notifications_muted = db.Column(db.Boolean, nullable=False, default=False)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.BigInteger, db.ForeignKey('chat_conversations.id'), nullable=False)
    sender_id = db.Column(db.BigInteger, db.ForeignKey('chat_actors.id'), nullable=False)
    message_type = db.Column(db.Enum('text', 'image', 'video', 'audio', 'file', 'system', name='message_type_enum'), nullable=False, default='text')
    body = db.Column(db.Text, nullable=True)
    attachment_path = db.Column(db.String(1024), nullable=True)
    attachment_mime = db.Column(db.String(191), nullable=True)
    attachment_size = db.Column(db.BigInteger, nullable=True)
    attachment_duration_ms = db.Column(db.Integer, nullable=True)
    attachment_width = db.Column(db.Integer, nullable=True)
    attachment_height = db.Column(db.Integer, nullable=True)
    thumbnail_path = db.Column(db.String(1024), nullable=True)
    attachment_url = db.Column(db.String(1024), nullable=True)
    meta_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, nullable=True, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.TIMESTAMP, nullable=True)

class ChatMessageReceipt(db.Model):
    __tablename__ = 'chat_message_receipts'

    message_id = db.Column(db.BigInteger, db.ForeignKey('chat_messages.id'), primary_key=True)
    actor_id = db.Column(db.BigInteger, db.ForeignKey('chat_actors.id'), primary_key=True)
    delivered_at = db.Column(db.TIMESTAMP, nullable=True)
    read_at = db.Column(db.TIMESTAMP, nullable=True)

class Admin(db.Model):
    __tablename__ = 'admin'

    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('superadmin', 'admin', 'moderator', name='admin_role_enum'), nullable=False, default='admin')
    address = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    date_modified = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.TIMESTAMP, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))