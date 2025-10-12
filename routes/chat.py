from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import (
    db, ChatActor, ChatConversation, ChatConversationParticipant,
    ChatMessage, ChatMessageReceipt, User, Provider
)
from datetime import datetime
from sqlalchemy import and_, or_, desc
from utils.upload import upload_file_to_r2
import os
from PIL import Image
import tempfile

# Create namespace
chat_ns = Namespace('chat', description='Chat operations')

# Define models for API documentation
error_model = chat_ns.model('Error', {
    'error': fields.String(required=True, description='Error message')
})

actor_model = chat_ns.model('ChatActor', {
    'id': fields.Integer(description='Actor ID'),
    'actor_type': fields.String(description='Actor type (user/provider)'),
    'user_id': fields.Integer(description='User ID if actor is user'),
    'provider_id': fields.Integer(description='Provider ID if actor is provider'),
    'name': fields.String(description='Display name'),
    'email': fields.String(description='Email address')
})

message_model = chat_ns.model('ChatMessage', {
    'id': fields.Integer(description='Message ID'),
    'conversation_id': fields.Integer(description='Conversation ID'),
    'sender_id': fields.Integer(description='Sender actor ID'),
    'sender_name': fields.String(description='Sender display name'),
    'message_type': fields.String(description='Message type'),
    'body': fields.String(description='Message body'),
    'attachment_path': fields.String(description='Attachment file path'),
    'attachment_url': fields.String(description='Attachment URL'),
    'attachment_mime': fields.String(description='MIME type of attachment'),
    'attachment_size': fields.Integer(description='File size in bytes'),
    'attachment_duration_ms': fields.Integer(description='Duration in milliseconds (audio/video)'),
    'attachment_width': fields.Integer(description='Width in pixels (image/video)'),
    'attachment_height': fields.Integer(description='Height in pixels (image/video)'),
    'thumbnail_path': fields.String(description='Thumbnail file path'),
    'created_at': fields.DateTime(description='Message timestamp'),
    'is_read': fields.Boolean(description='Whether message is read by current user')
})

conversation_model = chat_ns.model('ChatConversation', {
    'id': fields.Integer(description='Conversation ID'),
    'is_group': fields.Boolean(description='Is group conversation'),
    'title': fields.String(description='Conversation title'),
    'participants': fields.List(fields.Nested(actor_model)),
    'last_message': fields.Nested(message_model),
    'unread_count': fields.Integer(description='Unread message count'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'updated_at': fields.DateTime(description='Last update timestamp')
})

send_message_model = chat_ns.model('SendMessage', {
    'message_type': fields.String(required=True, description='Message type', enum=['text', 'image', 'video', 'audio', 'file', 'system']),
    'body': fields.String(description='Message body (required for text messages)'),
    'attachment_path': fields.String(description='Attachment file path'),
    'attachment_url': fields.String(description='Attachment URL'),
    'attachment_mime': fields.String(description='MIME type of attachment'),
    'attachment_size': fields.Integer(description='File size in bytes'),
    'attachment_duration_ms': fields.Integer(description='Duration in milliseconds (audio/video)'),
    'attachment_width': fields.Integer(description='Width in pixels (image/video)'),
    'attachment_height': fields.Integer(description='Height in pixels (image/video)'),
    'thumbnail_path': fields.String(description='Thumbnail file path')
})

create_conversation_model = chat_ns.model('CreateConversation', {
    'participant_id': fields.Integer(required=True, description='ID of the other participant (user or provider)'),
    'participant_type': fields.String(required=True, description='Type of participant', enum=['user', 'provider']),
    'is_group': fields.Boolean(description='Is group conversation', default=False),
    'title': fields.String(description='Conversation title (for group chats)')
})

file_upload_response_model = chat_ns.model('FileUploadResponse', {
    'success': fields.Boolean(description='Upload success status'),
    'url': fields.String(description='Public URL of uploaded file'),
    'attachment_path': fields.String(description='Server path of uploaded file'),
    'filename': fields.String(description='Generated filename'),
    'original_filename': fields.String(description='Original filename'),
    'mime_type': fields.String(description='MIME type of file'),
    'file_size': fields.Integer(description='File size in bytes'),
    'width': fields.Integer(description='Width for images/videos'),
    'height': fields.Integer(description='Height for images/videos'),
    'duration_ms': fields.Integer(description='Duration for audio/videos'),
    'thumbnail_url': fields.String(description='Thumbnail URL for media files'),
    'error': fields.String(description='Error message if upload failed')
})

# Helper functions
def get_or_create_actor(user_type, user_id, provider_id=None):
    """Get or create a chat actor for the current user"""
    actor = ChatActor.query.filter_by(
        actor_type=user_type,
        user_id=user_id if user_type == 'user' else None,
        provider_id=provider_id if user_type == 'provider' else None
    ).first()

    if not actor:
        actor = ChatActor(
            actor_type=user_type,
            user_id=user_id if user_type == 'user' else None,
            provider_id=provider_id if user_type == 'provider' else None
        )
        db.session.add(actor)
        db.session.flush()

    return actor

def get_actor_display_info(actor):
    """Get display name and email for an actor"""
    if actor.actor_type == 'user' and actor.user_id:
        user = User.query.get(actor.user_id)
        return user.full_name if user else 'Unknown User', user.email if user else ''
    elif actor.actor_type == 'provider' and actor.provider_id:
        provider = Provider.query.get(actor.provider_id)
        return provider.full_name if provider else 'Unknown Provider', provider.email if provider else ''
    return 'Unknown', ''

def check_conversation_access(conversation_id, actor_id):
    """Check if actor has access to the conversation"""
    participant = ChatConversationParticipant.query.filter_by(
        conversation_id=conversation_id,
        actor_id=actor_id
    ).first()
    return participant is not None

def get_file_mime_type(filename):
    """Get MIME type from filename extension"""
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    mime_types = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
        'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp',
        'mp4': 'video/mp4', 'avi': 'video/avi', 'mov': 'video/quicktime',
        'wmv': 'video/x-ms-wmv', 'flv': 'video/x-flv', 'webm': 'video/webm',
        'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'ogg': 'audio/ogg',
        'aac': 'audio/aac', 'm4a': 'audio/mp4', 'flac': 'audio/flac',
        'pdf': 'application/pdf', 'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain', 'zip': 'application/zip'
    }
    return mime_types.get(extension, 'application/octet-stream')

def get_message_type_from_mime(mime_type):
    """Determine message type from MIME type"""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    else:
        return 'file'

def create_thumbnail(file_path, output_path, max_size=(200, 200)):
    """Create thumbnail for image files"""
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Create thumbnail
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_path, 'JPEG', quality=85, optimize=True)
            return True
    except Exception as e:
        print(f"Thumbnail creation failed: {e}")
        return False

def get_image_dimensions(file_path):
    """Get image dimensions"""
    try:
        with Image.open(file_path) as img:
            return img.size  # (width, height)
    except:
        return None, None

# Routes
@chat_ns.route('/conversations')
class ConversationList(Resource):
    @chat_ns.doc(security='Bearer')
    @chat_ns.marshal_list_with(conversation_model, code=200)
    @chat_ns.response(401, 'Unauthorized', error_model)
    @jwt_required()
    def get(self):
        """Get all conversations for the current user"""
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            user_id = current_identity['user_id']

            # Get or create actor
            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )
            db.session.commit()

            # Get conversations where user is a participant
            conversations = db.session.query(ChatConversation).join(
                ChatConversationParticipant,
                ChatConversation.id == ChatConversationParticipant.conversation_id
            ).filter(
                ChatConversationParticipant.actor_id == actor.id
            ).order_by(desc(ChatConversation.updated_at)).all()

            result = []
            for conv in conversations:
                # Get participants
                participants_query = db.session.query(
                    ChatActor, ChatConversationParticipant
                ).join(
                    ChatConversationParticipant,
                    ChatActor.id == ChatConversationParticipant.actor_id
                ).filter(
                    ChatConversationParticipant.conversation_id == conv.id
                )

                participants = []
                for participant_actor, participant_info in participants_query:
                    name, email = get_actor_display_info(participant_actor)
                    participants.append({
                        'id': participant_actor.id,
                        'actor_type': participant_actor.actor_type,
                        'user_id': participant_actor.user_id,
                        'provider_id': participant_actor.provider_id,
                        'name': name,
                        'email': email
                    })

                # Get last message
                last_message = ChatMessage.query.filter_by(
                    conversation_id=conv.id,
                    deleted_at=None
                ).order_by(desc(ChatMessage.created_at)).first()

                last_msg_data = None
                if last_message:
                    sender_actor = ChatActor.query.get(last_message.sender_id)
                    sender_name, _ = get_actor_display_info(sender_actor) if sender_actor else ('Unknown', '')

                    # Check if message is read
                    receipt = ChatMessageReceipt.query.filter_by(
                        message_id=last_message.id,
                        actor_id=actor.id
                    ).first()

                    last_msg_data = {
                        'id': last_message.id,
                        'conversation_id': last_message.conversation_id,
                        'sender_id': last_message.sender_id,
                        'sender_name': sender_name,
                        'message_type': last_message.message_type,
                        'body': last_message.body,
                        'attachment_path': last_message.attachment_path,
                        'attachment_url': last_message.attachment_url,
                        'attachment_mime': last_message.attachment_mime,
                        'attachment_size': last_message.attachment_size,
                        'attachment_duration_ms': last_message.attachment_duration_ms,
                        'attachment_width': last_message.attachment_width,
                        'attachment_height': last_message.attachment_height,
                        'thumbnail_path': last_message.thumbnail_path,
                        'created_at': last_message.created_at,
                        'is_read': receipt is not None and receipt.read_at is not None
                    }

                # Get unread count
                unread_count = db.session.query(ChatMessage).outerjoin(
                    ChatMessageReceipt,
                    and_(
                        ChatMessage.id == ChatMessageReceipt.message_id,
                        ChatMessageReceipt.actor_id == actor.id
                    )
                ).filter(
                    ChatMessage.conversation_id == conv.id,
                    ChatMessage.sender_id != actor.id,
                    ChatMessage.deleted_at.is_(None),
                    or_(
                        ChatMessageReceipt.read_at.is_(None),
                        ChatMessageReceipt.read_at == None
                    )
                ).count()

                result.append({
                    'id': conv.id,
                    'is_group': conv.is_group,
                    'title': conv.title,
                    'participants': participants,
                    'last_message': last_msg_data,
                    'unread_count': unread_count,
                    'created_at': conv.created_at,
                    'updated_at': conv.updated_at
                })

            return result

        except Exception as e:
            return {'error': f'Failed to get conversations: {str(e)}'}, 500

    @chat_ns.doc(security='Bearer')
    @chat_ns.expect(create_conversation_model)
    @chat_ns.response(201, 'Conversation created', conversation_model)
    @chat_ns.response(400, 'Bad Request', error_model)
    @chat_ns.response(401, 'Unauthorized', error_model)
    @jwt_required()
    def post(self):
        """Create a new conversation"""
        try:
            data = request.get_json()

            # Validate required fields
            if not data:
                chat_ns.abort(400, 'Request body is required')

            if 'participant_id' not in data:
                chat_ns.abort(400, 'participant_id is required')

            if 'participant_type' not in data:
                chat_ns.abort(400, 'participant_type is required')

            if data['participant_type'] not in ['user', 'provider']:
                chat_ns.abort(400, 'participant_type must be either "user" or "provider"')

            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            user_id = current_identity['user_id']

            # Get or create current user's actor
            current_actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )

            # Get or create participant's actor
            participant_actor = get_or_create_actor(
                data['participant_type'],
                data['participant_id'] if data['participant_type'] == 'user' else None,
                data['participant_id'] if data['participant_type'] == 'provider' else None
            )

            # Check if conversation already exists between these two participants
            existing_conv = db.session.query(ChatConversation).join(
                ChatConversationParticipant, ChatConversation.id == ChatConversationParticipant.conversation_id
            ).filter(
                ChatConversation.is_group == False,
                ChatConversationParticipant.actor_id.in_([current_actor.id, participant_actor.id])
            ).group_by(ChatConversation.id).having(
                db.func.count(ChatConversationParticipant.actor_id) == 2
            ).first()

            if existing_conv:
                chat_ns.abort(400, 'Conversation already exists')

            # Create new conversation
            conversation = ChatConversation(
                is_group=data.get('is_group', False),
                title=data.get('title'),
                created_by_id=current_actor.id
            )
            db.session.add(conversation)
            db.session.flush()

            # Add participants
            for actor in [current_actor, participant_actor]:
                participant = ChatConversationParticipant(
                    conversation_id=conversation.id,
                    actor_id=actor.id,
                    role='admin' if actor.id == current_actor.id else 'member'
                )
                db.session.add(participant)

            db.session.commit()

            # Return conversation data
            participants = []
            for actor in [current_actor, participant_actor]:
                name, email = get_actor_display_info(actor)
                participants.append({
                    'id': actor.id,
                    'actor_type': actor.actor_type,
                    'user_id': actor.user_id,
                    'provider_id': actor.provider_id,
                    'name': name,
                    'email': email
                })

            return {
                'id': conversation.id,
                'is_group': conversation.is_group,
                'title': conversation.title,
                'participants': participants,
                'last_message': None,
                'unread_count': 0,
                'created_at': conversation.created_at,
                'updated_at': conversation.updated_at
            }, 201

        except Exception as e:
            db.session.rollback()
            chat_ns.abort(500, f'Failed to create conversation: {str(e)}')

@chat_ns.route('/conversations/<int:conversation_id>/messages')
class MessageList(Resource):
    @chat_ns.doc(security='Bearer')
    @chat_ns.marshal_list_with(message_model, code=200)
    @chat_ns.response(401, 'Unauthorized', error_model)
    @chat_ns.response(403, 'Access denied', error_model)
    @chat_ns.response(404, 'Conversation not found', error_model)
    @jwt_required()
    def get(self, conversation_id):
        """Get messages for a conversation"""
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            user_id = current_identity['user_id']

            # Get current user's actor
            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )
            db.session.commit()

            # Check access to conversation
            if not check_conversation_access(conversation_id, actor.id):
                return {'error': 'Access denied'}, 403

            # Get messages
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)

            messages = ChatMessage.query.filter_by(
                conversation_id=conversation_id,
                deleted_at=None
            ).order_by(desc(ChatMessage.created_at)).paginate(
                page=page, per_page=per_page, error_out=False
            )

            result = []
            for msg in messages.items:
                sender_actor = ChatActor.query.get(msg.sender_id)
                sender_name, _ = get_actor_display_info(sender_actor) if sender_actor else ('Unknown', '')

                # Check if message is read
                receipt = ChatMessageReceipt.query.filter_by(
                    message_id=msg.id,
                    actor_id=actor.id
                ).first()

                result.append({
                    'id': msg.id,
                    'conversation_id': msg.conversation_id,
                    'sender_id': msg.sender_id,
                    'sender_name': sender_name,
                    'message_type': msg.message_type,
                    'body': msg.body,
                    'attachment_path': msg.attachment_path,
                    'attachment_url': msg.attachment_url,
                    'attachment_mime': msg.attachment_mime,
                    'attachment_size': msg.attachment_size,
                    'attachment_duration_ms': msg.attachment_duration_ms,
                    'attachment_width': msg.attachment_width,
                    'attachment_height': msg.attachment_height,
                    'thumbnail_path': msg.thumbnail_path,
                    'created_at': msg.created_at,
                    'is_read': receipt is not None and receipt.read_at is not None
                })

            # Mark messages as delivered
            undelivered_messages = ChatMessage.query.filter_by(
                conversation_id=conversation_id,
                deleted_at=None
            ).filter(ChatMessage.sender_id != actor.id).all()

            for msg in undelivered_messages:
                receipt = ChatMessageReceipt.query.filter_by(
                    message_id=msg.id,
                    actor_id=actor.id
                ).first()

                if not receipt:
                    receipt = ChatMessageReceipt(
                        message_id=msg.id,
                        actor_id=actor.id,
                        delivered_at=datetime.utcnow()
                    )
                    db.session.add(receipt)
                elif not receipt.delivered_at:
                    receipt.delivered_at = datetime.utcnow()

            db.session.commit()

            return result[::-1]  # Reverse to show oldest first

        except Exception as e:
            return {'error': f'Failed to get messages: {str(e)}'}, 500

    @chat_ns.doc(security='Bearer')
    @chat_ns.expect(send_message_model)
    @chat_ns.marshal_with(message_model, code=201)
    @chat_ns.response(400, 'Bad Request', error_model)
    @chat_ns.response(401, 'Unauthorized', error_model)
    @chat_ns.response(403, 'Access denied', error_model)
    @jwt_required()
    def post(self, conversation_id):
        """Send a message to a conversation"""
        try:
            data = request.get_json()
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            user_id = current_identity['user_id']

            if not data.get('message_type'):
                return {'error': 'message_type is required'}, 400

            if data['message_type'] == 'text' and not data.get('body'):
                return {'error': 'body is required for text messages'}, 400

            if data['message_type'] in ['image', 'video', 'audio', 'file'] and not (data.get('attachment_url') or data.get('attachment_path')):
                return {'error': 'attachment_url or attachment_path is required for media messages'}, 400

            # Get current user's actor
            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )

            # Check access to conversation
            if not check_conversation_access(conversation_id, actor.id):
                return {'error': 'Access denied'}, 403

            # Create message
            message = ChatMessage(
                conversation_id=conversation_id,
                sender_id=actor.id,
                message_type=data['message_type'],
                body=data.get('body'),
                attachment_path=data.get('attachment_path'),
                attachment_url=data.get('attachment_url'),
                attachment_mime=data.get('attachment_mime'),
                attachment_size=data.get('attachment_size'),
                attachment_duration_ms=data.get('attachment_duration_ms'),
                attachment_width=data.get('attachment_width'),
                attachment_height=data.get('attachment_height'),
                thumbnail_path=data.get('thumbnail_path')
            )
            db.session.add(message)
            db.session.flush()

            # Update conversation timestamp
            conversation = ChatConversation.query.get(conversation_id)
            conversation.updated_at = datetime.utcnow()

            # Create delivery receipt for sender (mark as read)
            sender_receipt = ChatMessageReceipt(
                message_id=message.id,
                actor_id=actor.id,
                delivered_at=datetime.utcnow(),
                read_at=datetime.utcnow()
            )
            db.session.add(sender_receipt)

            db.session.commit()

            sender_name, _ = get_actor_display_info(actor)

            return {
                'id': message.id,
                'conversation_id': message.conversation_id,
                'sender_id': message.sender_id,
                'sender_name': sender_name,
                'message_type': message.message_type,
                'body': message.body,
                'attachment_path': message.attachment_path,
                'attachment_url': message.attachment_url,
                'attachment_mime': message.attachment_mime,
                'attachment_size': message.attachment_size,
                'attachment_duration_ms': message.attachment_duration_ms,
                'attachment_width': message.attachment_width,
                'attachment_height': message.attachment_height,
                'thumbnail_path': message.thumbnail_path,
                'created_at': message.created_at,
                'is_read': True
            }, 201

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to send message: {str(e)}'}, 500

@chat_ns.route('/conversations/<int:conversation_id>/messages/<int:message_id>/read')
class MarkMessageRead(Resource):
    @chat_ns.doc(security='Bearer')
    @chat_ns.response(200, 'Message marked as read')
    @chat_ns.response(401, 'Unauthorized', error_model)
    @chat_ns.response(403, 'Access denied', error_model)
    @jwt_required()
    def post(self, conversation_id, message_id):
        """Mark a message as read"""
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            user_id = current_identity['user_id']

            # Get current user's actor
            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )

            # Check access to conversation
            if not check_conversation_access(conversation_id, actor.id):
                return {'error': 'Access denied'}, 403

            # Get or create receipt
            receipt = ChatMessageReceipt.query.filter_by(
                message_id=message_id,
                actor_id=actor.id
            ).first()

            if not receipt:
                receipt = ChatMessageReceipt(
                    message_id=message_id,
                    actor_id=actor.id,
                    delivered_at=datetime.utcnow(),
                    read_at=datetime.utcnow()
                )
                db.session.add(receipt)
            else:
                receipt.read_at = datetime.utcnow()
                if not receipt.delivered_at:
                    receipt.delivered_at = datetime.utcnow()

            db.session.commit()

            return {'message': 'Message marked as read'}, 200

        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to mark message as read: {str(e)}'}, 500

@chat_ns.route('/conversations/<int:conversation_id>')
class ConversationDetail(Resource):
    @chat_ns.doc(security='Bearer')
    @chat_ns.marshal_with(conversation_model, code=200)
    @chat_ns.response(401, 'Unauthorized', error_model)
    @chat_ns.response(403, 'Access denied', error_model)
    @chat_ns.response(404, 'Conversation not found', error_model)
    @jwt_required()
    def get(self, conversation_id):
        """Get conversation details"""
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            user_id = current_identity['user_id']

            # Get current user's actor
            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )

            # Check access to conversation
            if not check_conversation_access(conversation_id, actor.id):
                return {'error': 'Access denied'}, 403

            conversation = ChatConversation.query.get(conversation_id)
            if not conversation:
                return {'error': 'Conversation not found'}, 404

            # Get participants
            participants_query = db.session.query(
                ChatActor, ChatConversationParticipant
            ).join(
                ChatConversationParticipant,
                ChatActor.id == ChatConversationParticipant.actor_id
            ).filter(
                ChatConversationParticipant.conversation_id == conversation_id
            )

            participants = []
            for participant_actor, participant_info in participants_query:
                name, email = get_actor_display_info(participant_actor)
                participants.append({
                    'id': participant_actor.id,
                    'actor_type': participant_actor.actor_type,
                    'user_id': participant_actor.user_id,
                    'provider_id': participant_actor.provider_id,
                    'name': name,
                    'email': email
                })

            return {
                'id': conversation.id,
                'is_group': conversation.is_group,
                'title': conversation.title,
                'participants': participants,
                'last_message': None,
                'unread_count': 0,
                'created_at': conversation.created_at,
                'updated_at': conversation.updated_at
            }

        except Exception as e:
            return {'error': f'Failed to get conversation: {str(e)}'}, 500

@chat_ns.route('/upload')
class ChatFileUpload(Resource):
    @chat_ns.doc(security='Bearer')
    @chat_ns.marshal_with(file_upload_response_model, code=200)
    @chat_ns.response(400, 'Bad Request', error_model)
    @chat_ns.response(401, 'Unauthorized', error_model)
    @jwt_required()
    def post(self):
        """Upload a file for chat attachment"""
        try:
            current_identity = get_jwt_identity()
            user_type = current_identity.get('user_type')
            user_id = current_identity['user_id']

            # Check if file is present
            if 'file' not in request.files:
                return {'success': False, 'error': 'No file provided'}, 400

            file = request.files['file']
            if file.filename == '':
                return {'success': False, 'error': 'No file selected'}, 400

            # Get MIME type and message type
            mime_type = get_file_mime_type(file.filename)
            message_type = get_message_type_from_mime(mime_type)

            # Get file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            # Upload to R2 with appropriate folder
            folder = f'chat-{message_type}s'  # chat-images, chat-videos, etc.
            prefix = f'{user_type}_{user_id}'

            upload_result = upload_file_to_r2(file, folder, prefix)

            if not upload_result['success']:
                return {
                    'success': False,
                    'error': upload_result['error']
                }, 400

            response_data = {
                'success': True,
                'url': upload_result['url'],
                'attachment_path': f"{folder}/{upload_result['filename']}",
                'filename': upload_result['filename'],
                'original_filename': upload_result['original_filename'],
                'mime_type': mime_type,
                'file_size': file_size
            }

            # Process images for dimensions and thumbnails
            if message_type == 'image':
                # Reset file pointer
                file.seek(0)

                # Create temporary file to process
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file.filename.rsplit(".", 1)[-1]}') as temp_file:
                    file.save(temp_file.name)

                    # Get dimensions
                    width, height = get_image_dimensions(temp_file.name)
                    if width and height:
                        response_data['width'] = width
                        response_data['height'] = height

                    # Create thumbnail
                    thumbnail_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    if create_thumbnail(temp_file.name, thumbnail_temp.name):
                        # Upload thumbnail
                        with open(thumbnail_temp.name, 'rb') as thumb_file:
                            thumb_upload = upload_file_to_r2(
                                thumb_file,
                                'chat-thumbnails',
                                f'{prefix}_thumb'
                            )
                            if thumb_upload['success']:
                                response_data['thumbnail_url'] = thumb_upload['url']

                    # Cleanup temp files
                    os.unlink(temp_file.name)
                    os.unlink(thumbnail_temp.name)

            return response_data, 200

        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }, 500

@chat_ns.route('/websocket/docs')
class WebSocketDocs(Resource):
    def get(self):
        """WebSocket Events Documentation"""
        return {
            "websocket_url": "ws://localhost:9078",
            "connection": {
                "url": "ws://localhost:9078",
                "auth": {
                    "method": "token",
                    "description": "Include JWT token in auth parameter when connecting",
                    "example": {
                        "auth": {
                            "token": "your-jwt-token-here"
                        }
                    }
                }
            },
            "events": {
                "client_to_server": {
                    "connect": {
                        "description": "Authenticate and connect to chat server",
                        "parameters": {
                            "auth": {
                                "token": "JWT token from login"
                            }
                        },
                        "example": "socket.io('ws://localhost:9078', { auth: { token: 'your-jwt-token' } })"
                    },
                    "join_conversation": {
                        "description": "Join a conversation room to receive messages",
                        "parameters": {
                            "conversation_id": "ID of conversation to join"
                        },
                        "example": "socket.emit('join_conversation', { conversation_id: 123 })"
                    },
                    "leave_conversation": {
                        "description": "Leave a conversation room",
                        "parameters": {
                            "conversation_id": "ID of conversation to leave"
                        },
                        "example": "socket.emit('leave_conversation', { conversation_id: 123 })"
                    },
                    "send_message": {
                        "description": "Send a text message to a conversation",
                        "parameters": {
                            "conversation_id": "Target conversation ID",
                            "message_type": "Message type (text/image/video/audio/file)",
                            "body": "Message content (required for text)",
                            "attachment_path": "Server path for media files",
                            "attachment_url": "Public URL for media files",
                            "attachment_mime": "MIME type of attachment",
                            "attachment_size": "File size in bytes",
                            "attachment_width": "Image/video width",
                            "attachment_height": "Image/video height",
                            "attachment_duration_ms": "Audio/video duration",
                            "thumbnail_path": "Thumbnail URL for media"
                        },
                        "example": "socket.emit('send_message', { conversation_id: 123, message_type: 'text', body: 'Hello!' })"
                    },
                    "send_message_with_file": {
                        "description": "Send a message with file attachment (use after uploading via REST API)",
                        "parameters": {
                            "conversation_id": "Target conversation ID",
                            "body": "Optional message text",
                            "file_data": "File data object from upload endpoint"
                        },
                        "example": "socket.emit('send_message_with_file', { conversation_id: 123, body: 'Check this out!', file_data: uploadResult })"
                    },
                    "typing_start": {
                        "description": "Indicate user started typing",
                        "parameters": {
                            "conversation_id": "Target conversation ID"
                        },
                        "example": "socket.emit('typing_start', { conversation_id: 123 })"
                    },
                    "typing_stop": {
                        "description": "Indicate user stopped typing",
                        "parameters": {
                            "conversation_id": "Target conversation ID"
                        },
                        "example": "socket.emit('typing_stop', { conversation_id: 123 })"
                    },
                    "mark_message_read": {
                        "description": "Mark a specific message as read",
                        "parameters": {
                            "conversation_id": "Target conversation ID",
                            "message_id": "ID of message to mark as read"
                        },
                        "example": "socket.emit('mark_message_read', { conversation_id: 123, message_id: 456 })"
                    }
                },
                "server_to_client": {
                    "connected": {
                        "description": "Confirmation of successful connection",
                        "data": {
                            "message": "Connected to chat server"
                        }
                    },
                    "joined_conversation": {
                        "description": "Confirmation of joining conversation",
                        "data": {
                            "conversation_id": "The conversation ID",
                            "message": "Joined conversation {id}"
                        }
                    },
                    "left_conversation": {
                        "description": "Confirmation of leaving conversation",
                        "data": {
                            "conversation_id": "The conversation ID",
                            "message": "Left conversation {id}"
                        }
                    },
                    "new_message": {
                        "description": "New message received in conversation",
                        "data": {
                            "id": "Message ID",
                            "conversation_id": "Conversation ID",
                            "sender_id": "Sender actor ID",
                            "sender_name": "Sender display name",
                            "message_type": "Message type",
                            "body": "Message content",
                            "attachment_url": "Media file URL",
                            "attachment_mime": "MIME type",
                            "attachment_size": "File size",
                            "created_at": "ISO timestamp",
                            "is_read": "Read status"
                        }
                    },
                    "message_sent": {
                        "description": "Confirmation that message was sent",
                        "data": {
                            "message_id": "ID of sent message",
                            "conversation_id": "Target conversation",
                            "status": "sent",
                            "message_type": "Type of message sent"
                        }
                    },
                    "user_joined": {
                        "description": "Another user joined the conversation",
                        "data": {
                            "user_id": "User ID",
                            "user_type": "user or provider",
                            "conversation_id": "Conversation ID"
                        }
                    },
                    "user_left": {
                        "description": "Another user left the conversation",
                        "data": {
                            "user_id": "User ID",
                            "user_type": "user or provider",
                            "conversation_id": "Conversation ID"
                        }
                    },
                    "user_typing": {
                        "description": "Another user is typing or stopped typing",
                        "data": {
                            "user_id": "User ID",
                            "user_type": "user or provider",
                            "conversation_id": "Conversation ID",
                            "typing": "true/false"
                        }
                    },
                    "message_read": {
                        "description": "Someone read a message",
                        "data": {
                            "message_id": "Message ID",
                            "conversation_id": "Conversation ID",
                            "reader_id": "Reader user ID",
                            "reader_type": "user or provider",
                            "read_at": "ISO timestamp"
                        }
                    },
                    "message_marked_read": {
                        "description": "Confirmation of marking message as read",
                        "data": {
                            "message_id": "Message ID",
                            "conversation_id": "Conversation ID"
                        }
                    },
                    "error": {
                        "description": "Error occurred",
                        "data": {
                            "message": "Error description"
                        }
                    }
                }
            },
            "workflow": {
                "file_upload": {
                    "description": "Complete workflow for sending files",
                    "steps": [
                        "1. Upload file via POST /api/chat/upload",
                        "2. Get file data response with URLs and metadata",
                        "3. Send message via WebSocket using 'send_message_with_file' event",
                        "4. Include file_data from step 2 in the WebSocket payload"
                    ]
                },
                "basic_messaging": {
                    "description": "Basic messaging workflow",
                    "steps": [
                        "1. Connect to WebSocket with JWT token",
                        "2. Join conversation using 'join_conversation'",
                        "3. Send messages using 'send_message'",
                        "4. Listen for 'new_message' events",
                        "5. Mark messages as read using 'mark_message_read'"
                    ]
                }
            },
            "examples": {
                "javascript_client": """
// Connect to WebSocket
const socket = io('ws://localhost:9078', {
  auth: { token: 'your-jwt-token' }
});

// Join conversation
socket.emit('join_conversation', { conversation_id: 123 });

// Send text message
socket.emit('send_message', {
  conversation_id: 123,
  message_type: 'text',
  body: 'Hello everyone!'
});

// Listen for new messages
socket.on('new_message', (message) => {
  console.log('New message:', message);
});

// Send file message (after uploading via REST API)
socket.emit('send_message_with_file', {
  conversation_id: 123,
  body: 'Check out this image!',
  file_data: uploadResponse
});

// Typing indicators
socket.emit('typing_start', { conversation_id: 123 });
setTimeout(() => {
  socket.emit('typing_stop', { conversation_id: 123 });
}, 3000);
                """.strip()
            }
        }, 200

# ========== WEBSOCKET EVENTS ==========

def init_socketio(socket_instance):
    """Initialize socketio instance and register event handlers"""
    from routes.chat_websocket import init_socketio_events
    init_socketio_events(socket_instance)