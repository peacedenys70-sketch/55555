import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import insert, delete
from app import db
from app.models import Utilisateur, Competence, user_competence, user_lacune
from app.utils.decoration import token_required

users_bp = Blueprint('users', __name__)


def _me():
    return db.session.get(Utilisateur, int(get_jwt_identity()))


def _is_valid_photo(val: str) -> bool:
    if not val:
        return True   # None / vide = supprimer la photo
    if val.startswith('http://') or val.startswith('https://'):
        return True
    return bool(re.match(r'^data:image/(jpeg|jpg|png|gif|webp);base64,', val))


def _get_or_create_comp(nom: str) -> Competence:
    nom  = nom.strip()
    comp = Competence.query.filter(
        db.func.lower(Competence.nom_competence) == nom.lower()
    ).first()
    if not comp:
        comp = Competence(nom_competence=nom)
        db.session.add(comp)
        db.session.flush()
    return comp


def _add_skill(user_id: int, table, nom: str):
    comp = _get_or_create_comp(nom)
    exists = db.session.execute(
        db.select(table).where(
            table.c.id_user       == user_id,
            table.c.id_competence == comp.id_competence,
        )
    ).first()
    if not exists:
        db.session.execute(insert(table).values(id_user=user_id, id_competence=comp.id_competence))
    return comp


# ── Profil ────────────────────────────────────────────────────

@users_bp.get('/me')
@token_required
def get_me():
    user = _me()
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    return jsonify(user.to_dict()), 200


@users_bp.put('/me')
@token_required
def update_me():
    user = _me()
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    data = request.get_json(silent=True) or {}

    for field in ['nom', 'prenom', 'telephone', 'bio', 'filiere', 'niveau']:
        if field in data and data[field] is not None:
            setattr(user, field, data[field])

    if 'photo' in data:
        if data['photo'] and not _is_valid_photo(data['photo']):
            return jsonify({'error': 'Format de photo invalide (base64 ou URL attendu)'}), 400
        user.photo = data['photo'] or None

    db.session.commit()
    return jsonify(user.to_dict()), 200


@users_bp.get('/<int:id_user>')
@token_required
def get_user(id_user):
    user = db.session.get(Utilisateur, id_user)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    return jsonify(user.to_dict()), 200


# ── Compétences ───────────────────────────────────────────────

@users_bp.post('/me/competences')
@token_required
def add_competence():
    user = _me()
    data = request.get_json(silent=True) or {}
    # Accepte { nom_competence } OU { noms: [...] }
    noms = data.get('noms') or []
    if not noms:
        n = (data.get('nom_competence') or '').strip()
        if not n:
            return jsonify({'error': 'nom_competence requis'}), 400
        noms = [n]

    for nom in noms:
        if nom.strip():
            _add_skill(user.id_user, user_competence, nom)
    db.session.commit()
    return jsonify({'message': f'{len(noms)} compétence(s) ajoutée(s)'}), 201


@users_bp.delete('/me/competences/<int:id_competence>')
@token_required
def remove_competence(id_competence):
    user = _me()
    db.session.execute(
        delete(user_competence).where(
            user_competence.c.id_user       == user.id_user,
            user_competence.c.id_competence == id_competence,
        )
    )
    db.session.commit()
    return jsonify({'message': 'Compétence supprimée'}), 200


# ── Lacunes ───────────────────────────────────────────────────

@users_bp.post('/me/lacunes')
@token_required
def add_lacune():
    user = _me()
    data = request.get_json(silent=True) or {}
    noms = data.get('noms') or []
    if not noms:
        n = (data.get('nom_competence') or '').strip()
        if not n:
            return jsonify({'error': 'nom_competence requis'}), 400
        noms = [n]

    for nom in noms:
        if nom.strip():
            _add_skill(user.id_user, user_lacune, nom)
    db.session.commit()
    return jsonify({'message': f'{len(noms)} lacune(s) ajoutée(s)'}), 201


@users_bp.delete('/me/lacunes/<int:id_competence>')
@token_required
def remove_lacune(id_competence):
    user = _me()
    db.session.execute(
        delete(user_lacune).where(
            user_lacune.c.id_user       == user.id_user,
            user_lacune.c.id_competence == id_competence,
        )
    )
    db.session.commit()
    return jsonify({'message': 'Lacune supprimée'}), 200
