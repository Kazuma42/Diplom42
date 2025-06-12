import os

class Config:
    SECRET_KEY = 'секретный_ключ'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///monky.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BABEL_DEFAULT_LOCALE = 'uk'
    BABEL_SUPPORTED_LOCALES = ['uk', 'en']
    BABEL_DEFAULT_TIMEZONE = 'Europe/Kyiv'
    
    # Добавь это:
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Ограничение на размер (16MB)