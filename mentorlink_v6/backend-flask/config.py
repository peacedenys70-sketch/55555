import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / '.env')


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/mentorlink'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY             = os.getenv('JWT_SECRET_KEY', 'change-me-in-production')
    JWT_ACCESS_TOKEN_EXPIRES   = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
    DEBUG                      = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    MAX_CONTENT_LENGTH         = 5 * 1024 * 1024   # 5 Mo max (photos)
