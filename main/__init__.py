from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_babel import Babel, get_locale

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
babel = Babel()

@login_manager.user_loader
def load_user(user_id):
    from main.models import User
    return User.query.get(int(user_id))

def get_locale():
    if 'lang' in request.args:
        session['lang'] = request.args.get('lang')
    if 'lang' in session:
        return session['lang']
    return request.accept_languages.best_match(['uk', 'en'])

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)

    babel.locale_selector_func = get_locale  # <-- регистрация функции выбора локали

    from flask_babel import gettext as _
    app.jinja_env.globals.update(_=_)
    app.jinja_env.globals.update(get_locale=get_locale)

    from main.routes.main_routes import main_bp
    app.register_blueprint(main_bp)

    return app