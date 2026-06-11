from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request


def token_required(f):
    """Décorateur JWT : vérifie le token avant d'exécuter la vue."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({'error': 'Token invalide ou manquant'}), 401
        return f(*args, **kwargs)
    return decorated
