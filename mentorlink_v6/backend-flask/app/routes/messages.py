from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app import db
from app.models import Message, Conversation, Matching
from app.utils.decoration import token_required

messages_bp = Blueprint('messages', __name__)


def _check_access(conv: Conversation, uid: int) -> bool:
    m = db.session.get(Matching, conv.id_matching)
    return m is not None and uid in (m.mentor_id, m.mentore_id)


@messages_bp.get('/<int:id_conv>')
@token_required
def get_messages(id_conv):
    uid  = int(get_jwt_identity())
    conv = db.session.get(Conversation, id_conv)
    if not conv:
        return jsonify({'error': 'Conversation introuvable'}), 404
    if not _check_access(conv, uid):
        return jsonify({'error': 'Accès refusé'}), 403

    msgs = Message.query.filter_by(id_conversation=id_conv).order_by(Message.date_envoi).all()
    return jsonify([{
        'id_message':    m.id_message,
        'expediteur_id': m.expediteur_id,
        'contenu':       m.contenu,
        'date_envoi':    m.date_envoi.isoformat(),
        'lu':            m.lu,
    } for m in msgs]), 200


@messages_bp.post('/<int:id_conv>')
@token_required
def send_message(id_conv):
    uid  = int(get_jwt_identity())
    conv = db.session.get(Conversation, id_conv)
    if not conv:
        return jsonify({'error': 'Conversation introuvable'}), 404
    if not _check_access(conv, uid):
        return jsonify({'error': 'Accès refusé'}), 403

    data    = request.get_json(silent=True) or {}
    contenu = (data.get('contenu') or '').strip()
    if not contenu:
        return jsonify({'error': 'Message vide'}), 400

    msg = Message(id_conversation=id_conv, expediteur_id=uid, contenu=contenu)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'id_message': msg.id_message}), 201
