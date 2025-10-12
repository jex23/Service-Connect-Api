from flask import session
from flask_socketio import emit, join_room, leave_room, disconnect
from models import (
    db, ChatActor, ChatConversation, ChatConversationParticipant,
    ChatMessage, ChatMessageReceipt, User, Provider
)
from datetime import datetime
import jwt as jwt_lib


def init_socketio_events(socketio_instance):
    """Initialize and register all WebSocket event handlers"""

    # Helper function for WebSocket authentication
    def authenticate_socket_user(token):
        """Authenticate user from socket token"""
        try:
            if not token:
                return None

            # Remove Bearer prefix if present
            if token.startswith('Bearer '):
                token = token[7:]

            from flask import current_app
            decoded = jwt_lib.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            return decoded
        except:
            return None

    # Helper functions from chat.py
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

    # WebSocket event handlers
    @socketio_instance.on('connect')
    def handle_connect(auth):
        """Handle client connection"""
        try:
            # Get token from auth data
            token = auth.get('token') if auth else None
            user_data = authenticate_socket_user(token)

            if not user_data:
                disconnect()
                return False

            print(f"User {user_data.get('user_id')} connected via WebSocket")

            # Store user data in session
            session['user_data'] = user_data
            session['socket_authenticated'] = True

            emit('connected', {'message': 'Connected to chat server'})
            return True

        except Exception as e:
            print(f"Connection error: {e}")
            disconnect()
            return False

    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        user_data = session.get('user_data')
        if user_data:
            print(f"User {user_data.get('user_id')} disconnected")

    @socketio_instance.on('join_conversation')
    def handle_join_conversation(data):
        """Join a conversation room"""
        try:
            user_data = session.get('user_data')

            if not user_data or not session.get('socket_authenticated'):
                emit('error', {'message': 'Not authenticated'})
                return

            conversation_id = data.get('conversation_id')
            if not conversation_id:
                emit('error', {'message': 'conversation_id required'})
                return

            # Get or create actor
            user_type = user_data.get('user_type')
            user_id = user_data.get('user_id')

            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )
            db.session.commit()

            # Check if user has access to conversation
            if not check_conversation_access(conversation_id, actor.id):
                emit('error', {'message': 'Access denied to conversation'})
                return

            # Join the room
            room = f"conversation_{conversation_id}"
            join_room(room)
            session['current_conversation'] = conversation_id

            emit('joined_conversation', {
                'conversation_id': conversation_id,
                'message': f'Joined conversation {conversation_id}'
            })

            # Notify others in the room that user joined
            emit('user_joined', {
                'user_id': user_id,
                'user_type': user_type,
                'conversation_id': conversation_id
            }, room=room, include_self=False)

        except Exception as e:
            emit('error', {'message': f'Failed to join conversation: {str(e)}'})

    @socketio_instance.on('leave_conversation')
    def handle_leave_conversation(data):
        """Leave a conversation room"""
        try:
            user_data = session.get('user_data')

            if not user_data or not session.get('socket_authenticated'):
                emit('error', {'message': 'Not authenticated'})
                return

            conversation_id = data.get('conversation_id')
            if not conversation_id:
                emit('error', {'message': 'conversation_id required'})
                return

            room = f"conversation_{conversation_id}"
            leave_room(room)

            if session.get('current_conversation') == conversation_id:
                session['current_conversation'] = None

            emit('left_conversation', {
                'conversation_id': conversation_id,
                'message': f'Left conversation {conversation_id}'
            })

            # Notify others in the room that user left
            emit('user_left', {
                'user_id': user_data.get('user_id'),
                'user_type': user_data.get('user_type'),
                'conversation_id': conversation_id
            }, room=room)

        except Exception as e:
            emit('error', {'message': f'Failed to leave conversation: {str(e)}'})

    @socketio_instance.on('send_message')
    def handle_send_message(data):
        """Send a message via WebSocket"""
        try:
            user_data = session.get('user_data')

            if not user_data or not session.get('socket_authenticated'):
                emit('error', {'message': 'Not authenticated'})
                return

            conversation_id = data.get('conversation_id')
            message_type = data.get('message_type', 'text')
            body = data.get('body')
            attachment_path = data.get('attachment_path')
            attachment_url = data.get('attachment_url')
            attachment_mime = data.get('attachment_mime')
            attachment_size = data.get('attachment_size')
            attachment_duration_ms = data.get('attachment_duration_ms')
            attachment_width = data.get('attachment_width')
            attachment_height = data.get('attachment_height')
            thumbnail_path = data.get('thumbnail_path')

            if not conversation_id:
                emit('error', {'message': 'conversation_id required'})
                return

            if message_type == 'text' and not body:
                emit('error', {'message': 'body required for text messages'})
                return

            if message_type in ['image', 'video', 'audio', 'file'] and not (attachment_url or attachment_path):
                emit('error', {'message': 'attachment_url or attachment_path required for media messages'})
                return

            # Get or create actor
            user_type = user_data.get('user_type')
            user_id = user_data.get('user_id')

            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )

            # Check access to conversation
            if not check_conversation_access(conversation_id, actor.id):
                emit('error', {'message': 'Access denied to conversation'})
                return

            # Create message
            message = ChatMessage(
                conversation_id=conversation_id,
                sender_id=actor.id,
                message_type=message_type,
                body=body,
                attachment_path=attachment_path,
                attachment_url=attachment_url,
                attachment_mime=attachment_mime,
                attachment_size=attachment_size,
                attachment_duration_ms=attachment_duration_ms,
                attachment_width=attachment_width,
                attachment_height=attachment_height,
                thumbnail_path=thumbnail_path
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

            # Get sender info
            sender_name, sender_email = get_actor_display_info(actor)

            # Prepare message data
            message_data = {
                'id': message.id,
                'conversation_id': message.conversation_id,
                'sender_id': message.sender_id,
                'sender_name': sender_name,
                'sender_email': sender_email,
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
                'created_at': message.created_at.isoformat(),
                'is_read': True  # Always true for sender
            }

            # Emit to conversation room
            room = f"conversation_{conversation_id}"
            emit('new_message', message_data, room=room)

            # Send confirmation to sender
            emit('message_sent', {
                'message_id': message.id,
                'conversation_id': conversation_id,
                'status': 'sent'
            })

        except Exception as e:
            db.session.rollback()
            emit('error', {'message': f'Failed to send message: {str(e)}'})

    @socketio_instance.on('typing_start')
    def handle_typing_start(data):
        """Handle user started typing"""
        try:
            user_data = session.get('user_data')

            if not user_data or not session.get('socket_authenticated'):
                return

            conversation_id = data.get('conversation_id')
            if not conversation_id:
                return

            room = f"conversation_{conversation_id}"
            emit('user_typing', {
                'user_id': user_data.get('user_id'),
                'user_type': user_data.get('user_type'),
                'conversation_id': conversation_id,
                'typing': True
            }, room=room, include_self=False)

        except Exception as e:
            emit('error', {'message': f'Typing error: {str(e)}'})

    @socketio_instance.on('typing_stop')
    def handle_typing_stop(data):
        """Handle user stopped typing"""
        try:
            user_data = session.get('user_data')

            if not user_data or not session.get('socket_authenticated'):
                return

            conversation_id = data.get('conversation_id')
            if not conversation_id:
                return

            room = f"conversation_{conversation_id}"
            emit('user_typing', {
                'user_id': user_data.get('user_id'),
                'user_type': user_data.get('user_type'),
                'conversation_id': conversation_id,
                'typing': False
            }, room=room, include_self=False)

        except Exception as e:
            emit('error', {'message': f'Typing error: {str(e)}'})

    @socketio_instance.on('mark_message_read')
    def handle_mark_message_read(data):
        """Mark message as read via WebSocket"""
        try:
            user_data = session.get('user_data')

            if not user_data or not session.get('socket_authenticated'):
                emit('error', {'message': 'Not authenticated'})
                return

            conversation_id = data.get('conversation_id')
            message_id = data.get('message_id')

            if not conversation_id or not message_id:
                emit('error', {'message': 'conversation_id and message_id required'})
                return

            # Get or create actor
            user_type = user_data.get('user_type')
            user_id = user_data.get('user_id')

            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )

            # Check access to conversation
            if not check_conversation_access(conversation_id, actor.id):
                emit('error', {'message': 'Access denied to conversation'})
                return

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

            # Notify conversation room about read receipt
            room = f"conversation_{conversation_id}"
            emit('message_read', {
                'message_id': message_id,
                'conversation_id': conversation_id,
                'reader_id': user_id,
                'reader_type': user_type,
                'read_at': receipt.read_at.isoformat()
            }, room=room, include_self=False)

            emit('message_marked_read', {
                'message_id': message_id,
                'conversation_id': conversation_id
            })

        except Exception as e:
            db.session.rollback()
            emit('error', {'message': f'Failed to mark message as read: {str(e)}'})

    @socketio_instance.on('send_message_with_file')
    def handle_send_message_with_file(data):
        """Send a message with file attachment via WebSocket (using pre-uploaded file data)"""
        try:
            user_data = session.get('user_data')

            if not user_data or not session.get('socket_authenticated'):
                emit('error', {'message': 'Not authenticated'})
                return

            conversation_id = data.get('conversation_id')
            body = data.get('body', '')

            # File data from previous upload via REST API
            file_data = data.get('file_data', {})

            if not conversation_id:
                emit('error', {'message': 'conversation_id required'})
                return

            if not file_data or not file_data.get('url'):
                emit('error', {'message': 'file_data with url required'})
                return

            # Get or create actor
            user_type = user_data.get('user_type')
            user_id = user_data.get('user_id')

            actor = get_or_create_actor(
                user_type,
                user_id if user_type == 'user' else None,
                user_id if user_type == 'provider' else None
            )

            # Check access to conversation
            if not check_conversation_access(conversation_id, actor.id):
                emit('error', {'message': 'Access denied to conversation'})
                return

            # Determine message type from MIME type
            mime_type = file_data.get('mime_type', 'application/octet-stream')
            if mime_type.startswith('image/'):
                message_type = 'image'
            elif mime_type.startswith('video/'):
                message_type = 'video'
            elif mime_type.startswith('audio/'):
                message_type = 'audio'
            else:
                message_type = 'file'

            # Create message with file attachment
            message = ChatMessage(
                conversation_id=conversation_id,
                sender_id=actor.id,
                message_type=message_type,
                body=body,
                attachment_path=file_data.get('attachment_path'),
                attachment_url=file_data.get('url'),
                attachment_mime=file_data.get('mime_type'),
                attachment_size=file_data.get('file_size'),
                attachment_duration_ms=file_data.get('duration_ms'),
                attachment_width=file_data.get('width'),
                attachment_height=file_data.get('height'),
                thumbnail_path=file_data.get('thumbnail_url')
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

            # Get sender info
            sender_name, sender_email = get_actor_display_info(actor)

            # Prepare message data
            message_data = {
                'id': message.id,
                'conversation_id': message.conversation_id,
                'sender_id': message.sender_id,
                'sender_name': sender_name,
                'sender_email': sender_email,
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
                'created_at': message.created_at.isoformat(),
                'is_read': True  # Always true for sender
            }

            # Emit to conversation room
            room = f"conversation_{conversation_id}"
            emit('new_message', message_data, room=room)

            # Send confirmation to sender
            emit('message_sent', {
                'message_id': message.id,
                'conversation_id': conversation_id,
                'status': 'sent',
                'message_type': message_type
            })

        except Exception as e:
            db.session.rollback()
            emit('error', {'message': f'Failed to send file message: {str(e)}'})