from flask import Flask
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from config import Config

db  = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static',
    )
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)

    @app.after_request
    def add_cors(response):
        response.headers['Access-Control-Allow-Origin']  = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        return response

    from app.routes.auth          import auth_bp
    from app.routes.users         import users_bp
    from app.routes.annonces      import annonces_bp
    from app.routes.matching      import matching_bp
    from app.routes.messages      import messages_bp
    from app.routes.disponibilite import disponibilite_bp
    from app.routes.main          import main_bp

    app.register_blueprint(auth_bp,          url_prefix='/auth')
    app.register_blueprint(users_bp,         url_prefix='/users')
    app.register_blueprint(annonces_bp,      url_prefix='/annonces')
    app.register_blueprint(matching_bp,      url_prefix='/matching')
    app.register_blueprint(messages_bp,      url_prefix='/messages')
    app.register_blueprint(disponibilite_bp, url_prefix='/disponibilites')
    app.register_blueprint(main_bp)

    return app
