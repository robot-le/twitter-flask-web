import os
import rq
import logging
from redis import Redis
from config import Config
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask, request, current_app
from flask_mail import Mail
from flask_babel import Babel, lazy_gettext as _l
from flask_login import LoginManager
from flask_moment import Moment
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from lingua import LanguageDetectorBuilder
from elasticsearch import Elasticsearch


def get_locale():
    return request.accept_languages.best_match(current_app.config.get('LANGUAGES'))


db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')
mail = Mail()
moment = Moment()
babel = Babel()
detector = LanguageDetectorBuilder.from_all_languages().build()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    babel.init_app(app, locale_selector=get_locale)

    app.elasticsearch = Elasticsearch([app.config.get('ELASTICSEARCH_URL')]) \
        if app.config.get('ELASTICSEARCH_URL') else None
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('microblog-tasks', connection=app.redis)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.cli import bp as cli_bp
    app.register_blueprint(cli_bp)

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    if not app.debug and not app.testing:
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

    return app


from app import models, cli
