from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import (
    db, ChatActor, ChatConversation, ChatConversationParticipant,
    ChatMessage, ChatMessageReceipt, User, Provider
)
from datetime import datetime
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import aliased

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
    'attachment_url': fields.String(description='Attachment URL'),
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
    'message_type': fields.String(required=True, description='Message type (text/image/file)', enum=['text', 'image', 'file']),
    'body': fields.String(description='Message body (required for text messages)'),
    'attachment_url': fields.String(description='Attachment URL (for image/file messages)')
})

create_conversation_model = chat_ns.model('CreateConversation', {
    'participant_id': fields.Integer(required=True, description='ID of the other participant (user or provider)'),
    'participant_type': fields.String(required=True, description='Type of participant', enum=['user', 'provider']),
    'is_group': fields.Boolean(description='Is group conversation', default=False),
    'title': fields.String(description='Conversation title (for group chats)')
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
                        'attachment_url': last_message.attachment_url,
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
    @chat_ns.marshal_with(conversation_model, code=201)
    @chat_ns.response(400, 'Bad Request', error_model)
    @chat_ns.response(401, 'Unauthorized', error_model)
    @jwt_required()
    def post(self):
        """Create a new conversation"""
        try:
            data = request.get_json()
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
                return {'error': 'Conversation already exists'}, 400

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
            return {'error': f'Failed to create conversation: {str(e)}'}, 500

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
                    'attachment_url': msg.attachment_url,
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

            if data['message_type'] in ['image', 'file'] and not data.get('attachment_url'):
                return {'error': 'attachment_url is required for image/file messages'}, 400

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
                attachment_url=data.get('attachment_url')
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
                'attachment_url': message.attachment_url,
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