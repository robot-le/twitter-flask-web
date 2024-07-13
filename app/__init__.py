import os
import logging
from config import Config
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask, request
from flask_mail import Mail
from flask_babel import Babel
from flask_login import LoginManager
from flask_moment import Moment
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from lingua import LanguageDetectorBuilder


def get_locale():
    return request.accept_languages.best_match(app.config.get('LANGUAGES'))


app = Flask(__name__)

app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'auth.login'
mail = Mail(app)
moment = Moment(app)
babel = Babel(app, locale_selector=get_locale)
detector = LanguageDetectorBuilder.from_all_languages().build()

if not app.debug:
    if app.config.get('MAIL_SERVER'):
        auth = None
        if app.config.get('MAIL_USERNAME') or app.config.get('MAIL_PASSWORD'):
            auth = (app.config.get('MAIL_USERNAME'), app.config.get('MAIL_PASSWORD'))
        secure = None
        if app.config.get('MAIL_USE_TLS'):
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config.get('MAIL_SERVER'), app.config.get('MAIL_PORT')),
            fromaddr='no-reply@' + app.config.get('MAIL_SERVER'),
            toaddrs=app.config.get('ADMINS'),
            subject='Microblog Failure',
            credentials=auth,
            secure=secure,
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler(
        'logs/microblog.log',
        maxBytes=10240,
        backupCount=10,
    )
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Microblog startup')

from app import models, cli
from app.errors import bp as errors_bp
app.register_blueprint(errors_bp)
from app.auth import bp as auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')
from app.main import bp as main_bp
app.register_blueprint(main_bp)
