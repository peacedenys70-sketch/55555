from datetime import time as dt_time
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app import db
from app.models import Disponibilite
from app.utils.decoration import token_required

disponibilite_bp = Blueprint('disponibilite', __name__)

JOURS_VALIDES = {'Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'}


def _parse_time(s: str):
    """'HH:MM' → time object ou None."""
    try:
        h, m = map(int, s.strip().split(':'))
        return dt_time(h, m)
    except Exception:
        return None


# ── Liste mes disponibilités ──────────────────────────────────

@disponibilite_bp.get('/me')
@token_required
def get_mes_dispos():
    uid = int(get_jwt_identity())
    dispos = Disponibilite.query.filter_by(id_user=uid).order_by(
        Disponibilite.jour, Disponibilite.heure_debut
    ).all()
    return jsonify([d.to_dict() for d in dispos]), 200


# ── Disponibilités d'un autre utilisateur (pour les mentors) ─

@disponibilite_bp.get('/user/<int:id_user>')
@token_required
def get_user_dispos(id_user):
    dispos = Disponibilite.query.filter_by(id_user=id_user).order_by(
        Disponibilite.jour, Disponibilite.heure_debut
    ).all()
    return jsonify([d.to_dict() for d in dispos]), 200


# ── Ajouter une disponibilité ─────────────────────────────────

@disponibilite_bp.post('/me')
@token_required
def add_dispo():
    uid  = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    jour  = (data.get('jour') or '').strip().capitalize()
    debut = _parse_time(data.get('heure_debut', ''))
    fin   = _parse_time(data.get('heure_fin', ''))

    if jour not in JOURS_VALIDES:
        return jsonify({'error': f'jour invalide. Valeurs : {", ".join(sorted(JOURS_VALIDES))}'}), 400
    if debut is None or fin is None:
        return jsonify({'error': 'heure_debut et heure_fin requis (format HH:MM)'}), 400
    if fin <= debut:
        return jsonify({'error': 'heure_fin doit être après heure_debut'}), 400

    # Éviter les doublons exacts
    existing = Disponibilite.query.filter_by(
        id_user=uid, jour=jour, heure_debut=debut, heure_fin=fin
    ).first()
    if existing:
        return jsonify({'message': 'Créneau déjà existant', 'id': existing.id_disponibilite}), 200

    d = Disponibilite(id_user=uid, jour=jour, heure_debut=debut, heure_fin=fin)
    db.session.add(d)
    db.session.commit()
    return jsonify({'message': 'Disponibilité ajoutée', **d.to_dict()}), 201


# ── Ajouter plusieurs disponibilités en une fois ─────────────

@disponibilite_bp.post('/me/bulk')
@token_required
def add_dispos_bulk():
    uid   = int(get_jwt_identity())
    items = request.get_json(silent=True) or []
    if not isinstance(items, list):
        return jsonify({'error': 'Envoyez une liste de disponibilités'}), 400

    added = 0
    errors = []
    for i, item in enumerate(items):
        jour  = (item.get('jour') or '').strip().capitalize()
        debut = _parse_time(item.get('heure_debut', ''))
        fin   = _parse_time(item.get('heure_fin', ''))

        if jour not in JOURS_VALIDES or debut is None or fin is None or fin <= debut:
            errors.append(f'Item {i} invalide')
            continue

        existing = Disponibilite.query.filter_by(
            id_user=uid, jour=jour, heure_debut=debut, heure_fin=fin
        ).first()
        if not existing:
            db.session.add(Disponibilite(id_user=uid, jour=jour, heure_debut=debut, heure_fin=fin))
            added += 1

    db.session.commit()
    return jsonify({'message': f'{added} créneau(x) ajouté(s)', 'errors': errors}), 201


# ── Supprimer une disponibilité ───────────────────────────────

@disponibilite_bp.delete('/me/<int:id_dispo>')
@token_required
def delete_dispo(id_dispo):
    uid   = int(get_jwt_identity())
    dispo = db.session.get(Disponibilite, id_dispo)
    if not dispo:
        return jsonify({'error': 'Disponibilité introuvable'}), 404
    if dispo.id_user != uid:
        return jsonify({'error': 'Non autorisé'}), 403

    db.session.delete(dispo)
    db.session.commit()
    return jsonify({'message': 'Disponibilité supprimée'}), 200
