from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app import db
from app.models import Annonce, Competence
from app.utils.decoration import token_required

annonces_bp = Blueprint('annonces', __name__)

TYPES_VALIDES   = {'OFFRE', 'DEMANDE'}
FORMATS_VALIDES = {'EN_LIGNE', 'PRESENTIEL', 'HYBRIDE'}


@annonces_bp.get('/')
def list_annonces():
    annonces = (
        Annonce.query
        .filter_by(statut='ACTIVE')
        .order_by(Annonce.date_creation.desc())
        .all()
    )
    return jsonify([a.to_dict() for a in annonces]), 200


@annonces_bp.post('/')
@token_required
def create_annonce():
    data  = request.get_json(silent=True) or {}
    titre = (data.get('titre') or '').strip()
    desc  = (data.get('description') or '').strip()
    type_ = (data.get('type_annonce') or '').upper()
    fmt   = (data.get('format') or 'EN_LIGNE').upper()

    if not titre or not desc:
        return jsonify({'error': 'Titre et description sont obligatoires'}), 400
    if type_ not in TYPES_VALIDES:
        return jsonify({'error': 'type_annonce doit être OFFRE ou DEMANDE'}), 400
    if fmt not in FORMATS_VALIDES:
        return jsonify({'error': 'format doit être EN_LIGNE, PRESENTIEL ou HYBRIDE'}), 400

    annonce = Annonce(
        id_user      = int(get_jwt_identity()),
        titre        = titre,
        description  = desc,
        type_annonce = type_,
        format       = fmt,
    )
    for nom in (data.get('competences') or []):
        nom = (nom or '').strip()
        if not nom:
            continue
        comp = Competence.query.filter(
            db.func.lower(Competence.nom_competence) == nom.lower()
        ).first()
        if not comp:
            comp = Competence(nom_competence=nom)
            db.session.add(comp)
        annonce.competences.append(comp)

    db.session.add(annonce)
    db.session.commit()
    return jsonify({'message': 'Annonce créée', 'id_annonce': annonce.id_annonce}), 201


@annonces_bp.delete('/<int:id_annonce>')
@token_required
def delete_annonce(id_annonce):
    annonce = db.session.get(Annonce, id_annonce)
    if not annonce:
        return jsonify({'error': 'Annonce introuvable'}), 404
    if annonce.id_user != int(get_jwt_identity()):
        return jsonify({'error': 'Non autorisé'}), 403
    annonce.statut = 'INACTIVE'
    db.session.commit()
    return jsonify({'message': 'Annonce désactivée'}), 200
