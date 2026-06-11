from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from app import db
from app.models import Matching, Utilisateur, Conversation
from app.utils.decoration import token_required

matching_bp = Blueprint('matching', __name__)

_NIVEAUX = ['L1', 'L2', 'L3', 'M1', 'M2']


def _niveau_index(niveau: str) -> int:
    try:
        return _NIVEAUX.index(niveau)
    except ValueError:
        return -1


# ── Suggestions ───────────────────────────────────────────────
@matching_bp.get('/suggestions')
@token_required
def suggestions():
    """
    Score 0-100 :
      80 pts max  → couverture lacunes : (∩ comp_mentor & lacunes_mentore) / nb_lacunes × 80
      10 pts      → bonus même filière
      10 pts max  → bonus niveau supérieur (+5/niveau d'écart, plafonné à 10)
    """
    uid  = int(get_jwt_identity())
    user = db.session.get(Utilisateur, uid)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    lacune_ids = {c.id_competence for c in user.lacunes}
    if not lacune_ids:
        return jsonify([]), 200

    # Exclure les mentors déjà demandés (tous statuts)
    deja_matches = {
        m.mentor_id for m in Matching.query.filter_by(mentore_id=uid).all()
    }
    deja_matches.add(uid)   # s'exclure soi-même

    curr_idx = _niveau_index(user.niveau)
    results  = []

    for mentor in Utilisateur.query.filter(Utilisateur.id_user.notin_(deja_matches)).all():
        comp_ids    = {c.id_competence for c in mentor.competences}
        match_count = len(lacune_ids & comp_ids)
        if match_count == 0:
            continue

        coverage      = (match_count / len(lacune_ids)) * 80
        filiere_bonus = 10 if mentor.filiere == user.filiere else 0
        m_idx         = _niveau_index(mentor.niveau)
        diff          = m_idx - curr_idx
        niveau_bonus  = min(10, max(0, diff * 5))
        score         = round(coverage + filiere_bonus + niveau_bonus, 2)

        results.append({**mentor.to_dict(), 'score': score})

    results.sort(key=lambda x: x['score'], reverse=True)
    return jsonify(results), 200


# ── Créer un matching ─────────────────────────────────────────
@matching_bp.post('/')
@token_required
def create_matching():
    data       = request.get_json(silent=True) or {}
    mentore_id = int(get_jwt_identity())
    mentor_id  = data.get('mentor_id')

    if not mentor_id:
        return jsonify({'error': 'mentor_id requis'}), 400
    mentor_id = int(mentor_id)
    if mentor_id == mentore_id:
        return jsonify({'error': 'Impossible de se matcher avec soi-même'}), 400
    if not db.session.get(Utilisateur, mentor_id):
        return jsonify({'error': 'Mentor introuvable'}), 404

    existing = Matching.query.filter_by(mentor_id=mentor_id, mentore_id=mentore_id).first()
    if existing:
        return jsonify({
            'error':           'Matching déjà existant',
            'id_matching':     existing.id_matching,
            'id_conversation': existing.conversation.id_conversation if existing.conversation else None,
        }), 409

    score = data.get('score')
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None

    matching = Matching(mentor_id=mentor_id, mentore_id=mentore_id, score_compatibilite=score)
    db.session.add(matching)
    db.session.flush()

    conv = Conversation(id_matching=matching.id_matching)
    db.session.add(conv)
    db.session.commit()

    return jsonify({
        'id_matching':     matching.id_matching,
        'id_conversation': conv.id_conversation,
    }), 201


# ── Changer le statut (ACCEPTE / REFUSE) ─────────────────────
@matching_bp.put('/<int:id_matching>/statut')
@token_required
def update_statut(id_matching):
    matching = db.session.get(Matching, id_matching)
    if not matching:
        return jsonify({'error': 'Matching introuvable'}), 404

    uid = int(get_jwt_identity())
    # SEUL le mentor peut accepter ou refuser
    if matching.mentor_id != uid:
        return jsonify({'error': 'Seul le mentor peut répondre à une demande'}), 403

    data   = request.get_json(silent=True) or {}
    statut = (data.get('statut') or '').upper()
    if statut not in {'EN_ATTENTE', 'ACCEPTE', 'REFUSE'}:
        return jsonify({'error': 'statut invalide (EN_ATTENTE, ACCEPTE ou REFUSE)'}), 400

    matching.statut = statut
    db.session.commit()
    return jsonify({'statut': matching.statut}), 200


# ── Demandes reçues (vue mentor) ──────────────────────────────
@matching_bp.get('/mes-demandes')
@token_required
def mes_demandes():
    uid = int(get_jwt_identity())
    ms  = Matching.query.filter_by(mentor_id=uid).order_by(Matching.date_matching.desc()).all()
    results = []
    for m in ms:
        mentore = db.session.get(Utilisateur, m.mentore_id)
        if not mentore:
            continue
        results.append({
            'id_matching':         m.id_matching,
            'statut':              m.statut,
            'score_compatibilite': float(m.score_compatibilite) if m.score_compatibilite else 0,
            'date_matching':       m.date_matching.isoformat(),
            'id_conversation':     m.conversation.id_conversation if m.conversation else None,
            'mentore': {
                'id_user': mentore.id_user,
                'nom':     mentore.nom,
                'prenom':  mentore.prenom,
                'filiere': mentore.filiere,
                'niveau':  mentore.niveau,
                'photo':   mentore.photo,
            },
        })
    return jsonify(results), 200


# ── Conversations actives ─────────────────────────────────────
@matching_bp.get('/mes-conversations')
@token_required
def mes_conversations():
    uid = int(get_jwt_identity())
    ms  = Matching.query.filter(
        db.or_(Matching.mentor_id == uid, Matching.mentore_id == uid),
        Matching.statut == 'ACCEPTE',
    ).all()

    results = []
    for m in ms:
        autre_id = m.mentore_id if m.mentor_id == uid else m.mentor_id
        autre    = db.session.get(Utilisateur, autre_id)
        if not autre or not m.conversation:
            continue
        results.append({
            'id_conversation': m.conversation.id_conversation,
            'partenaire': {
                'id_user': autre.id_user,      # ← indispensable côté frontend
                'nom':     autre.nom,
                'prenom':  autre.prenom,
                'filiere': autre.filiere,
                'niveau':  autre.niveau,
                'photo':   autre.photo,
            },
        })
    return jsonify(results), 200
