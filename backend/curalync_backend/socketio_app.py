import os
import jwt
import socketio
from django.conf import settings

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
)

# Track userId -> set of sids for multi-device support
user_socket_map: dict[str, set[str]] = {}
sid_user_map: dict[str, str] = {}


@sio.event
async def connect(sid, environ, auth):
    token = None
    if isinstance(auth, dict):
        token = auth.get('token')
    if not token:
        raise socketio.exceptions.ConnectionRefusedError('Authentication error')

    try:
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
    except Exception:
        raise socketio.exceptions.ConnectionRefusedError('Authentication error')

    user_id = str(decoded.get('id') or decoded.get('_id') or '')
    if not user_id:
        raise socketio.exceptions.ConnectionRefusedError('Authentication error')

    sid_user_map[sid] = user_id
    user_socket_map.setdefault(user_id, set()).add(sid)


@sio.on('join-room')
async def on_join_room(sid, conversation_id):
    if conversation_id:
        await sio.enter_room(sid, str(conversation_id))


@sio.on('send-message')
async def on_send_message(sid, message):
    if isinstance(message, dict) and message.get('conversationId'):
        await sio.emit('new-message', message, room=str(message['conversationId']), skip_sid=sid)


@sio.on('typing')
async def on_typing(sid, data):
    if isinstance(data, dict) and data.get('conversationId'):
        user_id = sid_user_map.get(sid)
        await sio.emit('typing', {'senderId': user_id}, room=str(data['conversationId']), skip_sid=sid)


@sio.on('stop-typing')
async def on_stop_typing(sid, data):
    if isinstance(data, dict) and data.get('conversationId'):
        user_id = sid_user_map.get(sid)
        await sio.emit('stop-typing', {'senderId': user_id}, room=str(data['conversationId']), skip_sid=sid)


@sio.on('message-read')
async def on_message_read(sid, data):
    if isinstance(data, dict) and data.get('conversationId'):
        await sio.emit('messages-read', {'conversationId': data['conversationId']}, room=str(data['conversationId']), skip_sid=sid)


@sio.event
async def disconnect(sid):
    user_id = sid_user_map.pop(sid, None)
    if user_id and user_id in user_socket_map:
        user_socket_map[user_id].discard(sid)
        if not user_socket_map[user_id]:
            user_socket_map.pop(user_id, None)
