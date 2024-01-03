import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from flask import Flask, current_app
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import json
from config import Config
from app.utilities.jinja_filters import format_sales_margin


class CustomJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super(CustomJSONEncoder, self).__init__(*args, **kwargs)
        self.datetime_format = current_app.config.get('DATETIME_FORMAT', '%Y-%m-%d %H:%M:%S')

    def default(self, obj):
        try:
            if isinstance(obj, datetime):
                return obj.strftime(self.datetime_format)   # [:22]  # Use the format from config
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return json.JSONEncoder.default(self, obj)


db = SQLAlchemy()
migration = Migrate()
csrf = CSRFProtect()  # Initialize CSRFProtect object

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please identify yourself."

def create_app(config_class=Config):
            
    app = Flask(__name__)
    app.config.from_object(Config)
    csrf.init_app(app)
    app.json_encoder = CustomJSONEncoder
    app.add_template_filter(format_sales_margin)
    db.init_app(app)
    migration.init_app(app, db)

    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User  # Import here to avoid circular dependencies
        return User.query.get(int(user_id))

    # import blueprints
    from app.main import bp_main
    from app.auth import bp_auth
    from app.users import bp_users
    from app.sync import bp_sync
    from app.api import bp_api

    # register blueprints
    app.register_blueprint(bp_main)     # management of stock items and the purchase history
    app.register_blueprint(bp_auth)     # authentication
    app.register_blueprint(bp_users)    # user management
    app.register_blueprint(bp_sync)     # sync functions, session setup
    app.register_blueprint(bp_api)      # API endpoints

    with app.app_context():
        db.create_all()

    csrf.exempt(bp_api)                 # API blueprint will be exempt from CSRF protection, it has no forms with user interaction.
  
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/storefront.log',
                                        maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Storefront launched.')

    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf())

    return app    

