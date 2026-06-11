from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app import db
from app.models import Utilisateur

auth_bp = Blueprint('auth', __name__)


def _ser():
    return URLSafeTimedSerializer(current_app.config['JWT_SECRET_KEY'])


# ── Inscription ────────────────────────────────────────────────
@auth_bp.post('/register')
def register():
    data = request.get_json(silent=True) or {}
    required = ['nom', 'prenom', 'email', 'mot_de_passe', 'telephone', 'filiere', 'niveau']
    missing  = [k for k in required if not str(data.get(k, '')).strip()]
    if missing:
        return jsonify({'error': f'Champs manquants ou vides : {", ".join(missing)}'}), 400

    email = data['email'].strip().lower()
    tel   = data['telephone'].strip()

    if Utilisateur.query.filter_by(email=email).first():
        return jsonify({'error': 'Adresse e-mail déjà utilisée'}), 409
    if Utilisateur.query.filter_by(telephone=tel).first():
        return jsonify({'error': 'Numéro de téléphone déjà utilisé'}), 409

    user = Utilisateur(
        nom          = data['nom'].strip(),
        prenom       = data['prenom'].strip(),
        email        = email,
        telephone    = tel,
        mot_de_passe = generate_password_hash(data['mot_de_passe']),
        filiere      = data['filiere'],
        niveau       = data['niveau'],
        bio          = (data.get('bio') or '').strip() or None,
        photo        = data.get('photo') or None,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Compte créé', 'id_user': user.id_user}), 201


# ── Connexion ──────────────────────────────────────────────────
@auth_bp.post('/login')
def login():
    data  = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    mdp   = data.get('mot_de_passe', '')
    if not email or not mdp:
        return jsonify({'error': 'Email et mot de passe requis'}), 400

    user = Utilisateur.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.mot_de_passe, mdp):
        return jsonify({'error': 'Identifiants invalides'}), 401

    token = create_access_token(identity=str(user.id_user))
    return jsonify({'access_token': token, 'user': user.to_dict()}), 200


# ── Mot de passe oublié ────────────────────────────────────────
@auth_bp.post('/forgot-password')
def forgot_password():
    data  = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'Email requis'}), 400

    user = Utilisateur.query.filter_by(email=email).first()
    if user:
        token     = _ser().dumps({'id_user': user.id_user, 'email': user.email}, salt='reset-password')
        reset_url = f'/reset-password/{token}'
        current_app.logger.info(f'[RESET] {reset_url}')
        return jsonify({'message': 'Lien généré.', 'reset_url': reset_url}), 200

    return jsonify({'message': 'Si cet email existe, un lien a été généré.'}), 200


# ── Réinitialiser le mot de passe ─────────────────────────────
@auth_bp.post('/reset-password/<token>')
def reset_password(token):
    data = request.get_json(silent=True) or {}
    nouveau = data.get('mot_de_passe', '')
    if len(nouveau) < 8:
        return jsonify({'error': 'Le mot de passe doit contenir au moins 8 caractères'}), 400

    try:
        payload = _ser().loads(token, salt='reset-password', max_age=1800)
    except SignatureExpired:
        return jsonify({'error': 'Ce lien a expiré. Faites une nouvelle demande.'}), 410
    except BadSignature:
        return jsonify({'error': 'Lien invalide ou modifié.'}), 400

    user = db.session.get(Utilisateur, payload['id_user'])
    if not user or user.email != payload['email']:
        return jsonify({'error': 'Utilisateur introuvable.'}), 404

    user.mot_de_passe = generate_password_hash(nouveau)
    db.session.commit()
    return jsonify({'message': 'Mot de passe réinitialisé avec succès.'}), 200


# ── Vérifier un token de reset ─────────────────────────────────
@auth_bp.get('/reset-password/<token>/verify')
def verify_reset_token(token):
    try:
        _ser().loads(token, salt='reset-password', max_age=1800)
        return jsonify({'valid': True}), 200
    except (SignatureExpired, BadSignature):
        return jsonify({'valid': False, 'error': 'Token invalide ou expiré.'}), 400
