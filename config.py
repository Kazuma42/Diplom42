import os

class Config:
    SECRET_KEY = 'секретный_ключ'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///monky.db?check_same_thread=False'  # Добавлен параметр для SQLite
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Можно явно задать опции движка SQLAlchemy
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 15}  # Время ожидания при блокировке базы (в секундах)
    }

    BABEL_DEFAULT_LOCALE = 'uk'
    BABEL_SUPPORTED_LOCALES = ['uk', 'en']
    BABEL_DEFAULT_TIMEZONE = 'Europe/Kyiv'
    
    UPLOAD_FOLDER = 'main/static/uploads/avatars'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB