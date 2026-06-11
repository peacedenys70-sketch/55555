-- ============================================================
-- IFRI MentorLink v6 — Schéma PostgreSQL 14+
-- ============================================================

DROP TABLE IF EXISTS password_reset_token CASCADE;
DROP TABLE IF EXISTS message              CASCADE;
DROP TABLE IF EXISTS conversation         CASCADE;
DROP TABLE IF EXISTS matching             CASCADE;
DROP TABLE IF EXISTS annonce_competence   CASCADE;
DROP TABLE IF EXISTS annonce              CASCADE;
DROP TABLE IF EXISTS disponibilite        CASCADE;
DROP TABLE IF EXISTS user_lacune          CASCADE;
DROP TABLE IF EXISTS user_competence      CASCADE;
DROP TABLE IF EXISTS competence           CASCADE;
DROP TABLE IF EXISTS utilisateur          CASCADE;

-- Utilisateurs
CREATE TABLE utilisateur (
    id_user       SERIAL PRIMARY KEY,
    nom           VARCHAR(50)  NOT NULL,
    prenom        VARCHAR(50)  NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE,
    telephone     VARCHAR(20)  NOT NULL UNIQUE,
    mot_de_passe  VARCHAR(255) NOT NULL,
    photo         TEXT,
    filiere       VARCHAR(100) NOT NULL,
    niveau        VARCHAR(50)  NOT NULL CHECK (niveau IN ('L1','L2','L3','M1','M2')),
    bio           TEXT,
    date_creation TIMESTAMPTZ  DEFAULT NOW()
);

-- Compétences (référentiel)
CREATE TABLE competence (
    id_competence  SERIAL PRIMARY KEY,
    nom_competence VARCHAR(100) NOT NULL UNIQUE
);

-- Liaison utilisateur ↔ compétences maîtrisées
CREATE TABLE user_competence (
    id_user       INTEGER REFERENCES utilisateur(id_user) ON DELETE CASCADE,
    id_competence INTEGER REFERENCES competence(id_competence) ON DELETE CASCADE,
    PRIMARY KEY (id_user, id_competence)
);

-- Liaison utilisateur ↔ lacunes
CREATE TABLE user_lacune (
    id_user       INTEGER REFERENCES utilisateur(id_user) ON DELETE CASCADE,
    id_competence INTEGER REFERENCES competence(id_competence) ON DELETE CASCADE,
    PRIMARY KEY (id_user, id_competence)
);

-- Disponibilités (planning)
CREATE TABLE disponibilite (
    id_disponibilite SERIAL PRIMARY KEY,
    id_user          INTEGER NOT NULL REFERENCES utilisateur(id_user) ON DELETE CASCADE,
    jour             VARCHAR(20) NOT NULL CHECK (jour IN ('Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche')),
    heure_debut      TIME NOT NULL,
    heure_fin        TIME NOT NULL,
    CONSTRAINT hf_apres_hd CHECK (heure_fin > heure_debut)
);

-- Annonces
CREATE TABLE annonce (
    id_annonce    SERIAL PRIMARY KEY,
    id_user       INTEGER NOT NULL REFERENCES utilisateur(id_user) ON DELETE CASCADE,
    titre         VARCHAR(200) NOT NULL,
    description   TEXT NOT NULL,
    type_annonce  VARCHAR(20)  NOT NULL CHECK (type_annonce IN ('OFFRE','DEMANDE')),
    format        VARCHAR(20)  NOT NULL CHECK (format IN ('EN_LIGNE','PRESENTIEL','HYBRIDE')),
    statut        VARCHAR(20)  DEFAULT 'ACTIVE',
    date_creation TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE annonce_competence (
    id_annonce    INTEGER REFERENCES annonce(id_annonce) ON DELETE CASCADE,
    id_competence INTEGER REFERENCES competence(id_competence) ON DELETE CASCADE,
    PRIMARY KEY (id_annonce, id_competence)
);

-- Matching
CREATE TABLE matching (
    id_matching         SERIAL PRIMARY KEY,
    mentor_id           INTEGER NOT NULL REFERENCES utilisateur(id_user) ON DELETE CASCADE,
    mentore_id          INTEGER NOT NULL REFERENCES utilisateur(id_user) ON DELETE CASCADE,
    score_compatibilite NUMERIC(5,2),
    statut              VARCHAR(20) DEFAULT 'EN_ATTENTE'
                            CHECK (statut IN ('EN_ATTENTE','ACCEPTE','REFUSE')),
    date_matching       TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_diff CHECK (mentor_id <> mentore_id)
);

-- Conversations (liées à un matching)
CREATE TABLE conversation (
    id_conversation SERIAL PRIMARY KEY,
    id_matching     INTEGER NOT NULL UNIQUE REFERENCES matching(id_matching) ON DELETE CASCADE,
    date_creation   TIMESTAMPTZ DEFAULT NOW(),
    statut          VARCHAR(20) DEFAULT 'ACTIVE'
);

-- Messages
CREATE TABLE message (
    id_message      SERIAL PRIMARY KEY,
    id_conversation INTEGER NOT NULL REFERENCES conversation(id_conversation) ON DELETE CASCADE,
    expediteur_id   INTEGER NOT NULL REFERENCES utilisateur(id_user) ON DELETE CASCADE,
    contenu         TEXT NOT NULL,
    date_envoi      TIMESTAMPTZ DEFAULT NOW(),
    lu              BOOLEAN DEFAULT FALSE
);

-- Tokens de réinitialisation de mot de passe
CREATE TABLE password_reset_token (
    id        SERIAL PRIMARY KEY,
    id_user   INTEGER NOT NULL REFERENCES utilisateur(id_user) ON DELETE CASCADE,
    token     VARCHAR(100) NOT NULL UNIQUE,
    expire_at TIMESTAMPTZ  NOT NULL,
    utilise   BOOLEAN DEFAULT FALSE
);

-- Index de performance
CREATE INDEX idx_uc_user  ON user_competence(id_user);
CREATE INDEX idx_ul_user  ON user_lacune(id_user);
CREATE INDEX idx_dispo    ON disponibilite(id_user, jour);
CREATE INDEX idx_ann_stat ON annonce(statut);
CREATE INDEX idx_mat_men  ON matching(mentor_id);
CREATE INDEX idx_mat_mte  ON matching(mentore_id);
CREATE INDEX idx_msg_conv ON message(id_conversation, date_envoi);
