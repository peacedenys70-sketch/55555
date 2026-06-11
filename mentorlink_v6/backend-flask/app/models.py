from app import db
from datetime import datetime, timezone, timedelta
import secrets
import re


def _now():
    """Heure UTC courante, timezone-aware — compatible Python 3.12+."""
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────
# TABLES D'ASSOCIATION (many-to-many sans modèle dédié)
# ──────────────────────────────────────────────────────────────

user_competence = db.Table(
    'user_competence',
    db.Column('id_user',       db.Integer, db.ForeignKey('utilisateur.id_user',      ondelete='CASCADE'), primary_key=True),
    db.Column('id_competence', db.Integer, db.ForeignKey('competence.id_competence', ondelete='CASCADE'), primary_key=True),
)

user_lacune = db.Table(
    'user_lacune',
    db.Column('id_user',       db.Integer, db.ForeignKey('utilisateur.id_user',      ondelete='CASCADE'), primary_key=True),
    db.Column('id_competence', db.Integer, db.ForeignKey('competence.id_competence', ondelete='CASCADE'), primary_key=True),
)

annonce_competence = db.Table(
    'annonce_competence',
    db.Column('id_annonce',    db.Integer, db.ForeignKey('annonce.id_annonce',        ondelete='CASCADE'), primary_key=True),
    db.Column('id_competence', db.Integer, db.ForeignKey('competence.id_competence',  ondelete='CASCADE'), primary_key=True),
)


# ──────────────────────────────────────────────────────────────
# COMPETENCE
# ──────────────────────────────────────────────────────────────

class Competence(db.Model):
    __tablename__ = 'competence'

    id_competence  = db.Column(db.Integer, primary_key=True)
    nom_competence = db.Column(db.String(100), nullable=False, unique=True)


# ──────────────────────────────────────────────────────────────
# UTILISATEUR
# ──────────────────────────────────────────────────────────────

class Utilisateur(db.Model):
    __tablename__ = 'utilisateur'

    id_user       = db.Column(db.Integer, primary_key=True)
    nom           = db.Column(db.String(50),  nullable=False)
    prenom        = db.Column(db.String(50),  nullable=False)
    email         = db.Column(db.String(100), nullable=False, unique=True)
    mot_de_passe  = db.Column(db.String(255), nullable=False)
    # photo : data URI base64 (data:image/…;base64,…) ou URL
    photo         = db.Column(db.Text)
    filiere       = db.Column(db.String(100), nullable=False)
    niveau        = db.Column(db.String(50),  nullable=False)
    bio           = db.Column(db.Text)
    telephone     = db.Column(db.String(20),  nullable=False, unique=True)
    date_creation = db.Column(db.DateTime(timezone=True), default=_now)

    competences = db.relationship(
        'Competence', secondary='user_competence',
        backref=db.backref('utilisateurs', lazy='dynamic'),
        overlaps='lacunes,users_lacune',
    )
    lacunes = db.relationship(
        'Competence', secondary='user_lacune',
        backref=db.backref('users_lacune', lazy='dynamic'),
        overlaps='competences,utilisateurs',
    )
    annonces       = db.relationship('Annonce',       backref='auteur',      lazy=True, cascade='all, delete-orphan')
    disponibilites = db.relationship('Disponibilite', backref='utilisateur', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        from sqlalchemy import text
        comps = db.session.execute(text(
            "SELECT c.id_competence, c.nom_competence FROM competence c "
            "JOIN user_competence uc ON uc.id_competence=c.id_competence "
            "WHERE uc.id_user=:uid ORDER BY c.nom_competence"
        ), {'uid': self.id_user}).fetchall()
        lacs = db.session.execute(text(
            "SELECT c.id_competence, c.nom_competence FROM competence c "
            "JOIN user_lacune ul ON ul.id_competence=c.id_competence "
            "WHERE ul.id_user=:uid ORDER BY c.nom_competence"
        ), {'uid': self.id_user}).fetchall()
        dispos = db.session.execute(text(
            "SELECT id_disponibilite, jour, heure_debut::text, heure_fin::text "
            "FROM disponibilite WHERE id_user=:uid ORDER BY jour, heure_debut"
        ), {'uid': self.id_user}).fetchall()
        return {
            'id_user':        self.id_user,
            'nom':            self.nom,
            'prenom':         self.prenom,
            'email':          self.email,
            'telephone':      self.telephone,
            'bio':            self.bio,
            'photo':          self.photo,
            'filiere':        self.filiere,
            'niveau':         self.niveau,
            'date_creation':  self.date_creation.isoformat(),
            'competences':    [{'id_competence': r.id_competence, 'nom_competence': r.nom_competence} for r in comps],
            'lacunes':        [{'id_competence': r.id_competence, 'nom_competence': r.nom_competence} for r in lacs],
            'disponibilites': [{'id': r.id_disponibilite, 'jour': r.jour, 'debut': r.heure_debut, 'fin': r.heure_fin} for r in dispos],
        }


# ──────────────────────────────────────────────────────────────
# DISPONIBILITE
# ──────────────────────────────────────────────────────────────

class Disponibilite(db.Model):
    __tablename__ = 'disponibilite'

    id_disponibilite = db.Column(db.Integer, primary_key=True)
    id_user          = db.Column(db.Integer, db.ForeignKey('utilisateur.id_user', ondelete='CASCADE'), nullable=False)
    jour             = db.Column(db.String(20), nullable=False)   # Lundi…Dimanche
    heure_debut      = db.Column(db.Time, nullable=False)
    heure_fin        = db.Column(db.Time, nullable=False)

    def to_dict(self):
        return {
            'id':    self.id_disponibilite,
            'jour':  self.jour,
            'debut': self.heure_debut.strftime('%H:%M'),
            'fin':   self.heure_fin.strftime('%H:%M'),
        }


# ──────────────────────────────────────────────────────────────
# ANNONCE
# ──────────────────────────────────────────────────────────────

class Annonce(db.Model):
    __tablename__ = 'annonce'

    id_annonce    = db.Column(db.Integer, primary_key=True)
    id_user       = db.Column(db.Integer, db.ForeignKey('utilisateur.id_user', ondelete='CASCADE'), nullable=False)
    titre         = db.Column(db.String(200), nullable=False)
    description   = db.Column(db.Text,        nullable=False)
    type_annonce  = db.Column(db.String(20),   nullable=False)   # OFFRE | DEMANDE
    format        = db.Column(db.String(20),   nullable=False)   # EN_LIGNE | PRESENTIEL | HYBRIDE
    statut        = db.Column(db.String(20),   default='ACTIVE')
    date_creation = db.Column(db.DateTime(timezone=True), default=_now)
    competences   = db.relationship('Competence', secondary='annonce_competence', backref='annonces')

    def to_dict(self):
        return {
            'id_annonce':    self.id_annonce,
            'id_user':       self.id_user,
            'titre':         self.titre,
            'description':   self.description,
            'type_annonce':  self.type_annonce,
            'format':        self.format,
            'statut':        self.statut,
            'date_creation': self.date_creation.isoformat(),
            'competences':   [c.nom_competence for c in self.competences],
            'auteur': {
                'id_user': self.auteur.id_user,
                'nom':     self.auteur.nom,
                'prenom':  self.auteur.prenom,
                'filiere': self.auteur.filiere,
                'niveau':  self.auteur.niveau,
                'photo':   self.auteur.photo,
            },
        }


# ──────────────────────────────────────────────────────────────
# MATCHING
# ──────────────────────────────────────────────────────────────

class Matching(db.Model):
    __tablename__ = 'matching'

    id_matching         = db.Column(db.Integer, primary_key=True)
    mentor_id           = db.Column(db.Integer, db.ForeignKey('utilisateur.id_user', ondelete='CASCADE'), nullable=False)
    mentore_id          = db.Column(db.Integer, db.ForeignKey('utilisateur.id_user', ondelete='CASCADE'), nullable=False)
    score_compatibilite = db.Column(db.Numeric(5, 2))
    statut              = db.Column(db.String(20), default='EN_ATTENTE')  # EN_ATTENTE | ACCEPTE | REFUSE
    date_matching       = db.Column(db.DateTime(timezone=True), default=_now)

    conversation = db.relationship('Conversation', backref='matching', uselist=False, cascade='all, delete-orphan')
    mentor       = db.relationship('Utilisateur', foreign_keys=[mentor_id],  backref='matchings_mentor')
    mentore      = db.relationship('Utilisateur', foreign_keys=[mentore_id], backref='matchings_mentore')


# ──────────────────────────────────────────────────────────────
# CONVERSATION
# ──────────────────────────────────────────────────────────────

class Conversation(db.Model):
    __tablename__ = 'conversation'

    id_conversation = db.Column(db.Integer, primary_key=True)
    id_matching     = db.Column(db.Integer, db.ForeignKey('matching.id_matching', ondelete='CASCADE'), nullable=False)
    date_creation   = db.Column(db.DateTime(timezone=True), default=_now)
    statut          = db.Column(db.String(20), default='ACTIVE')
    messages        = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')


# ──────────────────────────────────────────────────────────────
# MESSAGE
# ──────────────────────────────────────────────────────────────

class Message(db.Model):
    __tablename__ = 'message'

    id_message      = db.Column(db.Integer, primary_key=True)
    id_conversation = db.Column(db.Integer, db.ForeignKey('conversation.id_conversation', ondelete='CASCADE'), nullable=False)
    expediteur_id   = db.Column(db.Integer, db.ForeignKey('utilisateur.id_user',          ondelete='CASCADE'), nullable=False)
    contenu         = db.Column(db.Text, nullable=False)
    date_envoi      = db.Column(db.DateTime(timezone=True), default=_now)
    lu              = db.Column(db.Boolean, default=False)

    expediteur = db.relationship('Utilisateur', foreign_keys=[expediteur_id])


# ──────────────────────────────────────────────────────────────
# PASSWORD RESET TOKEN
# ──────────────────────────────────────────────────────────────

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'

    id          = db.Column(db.Integer, primary_key=True)
    id_user     = db.Column(db.Integer, db.ForeignKey('utilisateur.id_user', ondelete='CASCADE'), nullable=False)
    token       = db.Column(db.String(100), nullable=False, unique=True)
    expire_at   = db.Column(db.DateTime(timezone=True), nullable=False)
    utilise     = db.Column(db.Boolean, default=False)
    utilisateur = db.relationship('Utilisateur', backref='reset_tokens')

    @staticmethod
    def generer(id_user):
        return PasswordResetToken(
            id_user   = id_user,
            token     = secrets.token_urlsafe(32),
            expire_at = _now() + timedelta(minutes=30),
        )

    def est_valide(self):
        return not self.utilise and _now() < self.expire_at
