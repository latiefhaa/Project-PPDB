import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import datetime
from flask_mail import Mail

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

def create_app(config_class=None):
    app = Flask(__name__)

    # Konfigurasi aplikasi
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///siswa.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'mysecret'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

    # Email configuration with better security settings
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=465,  # Change to 465 for SSL
        MAIL_USE_TLS=False,  # Disable TLS
        MAIL_USE_SSL=True,   # Enable SSL
        MAIL_USERNAME='ilhameskepal@gmail.com',
        MAIL_PASSWORD='sgulignazazrtoti',  # Your App Password
        MAIL_DEFAULT_SENDER=('PPDB Online', 'ilhameskepal@gmail.com'),
        MAIL_MAX_EMAILS=50,
        MAIL_ASCII_ATTACHMENTS=False,
        MAIL_DEBUG=True,
        MAIL_SUPPRESS_SEND=False,
        MAIL_USE_CREDENTIALS=True,
        MAIL_TIMEOUT=30
    )

    # Buat folder upload jika belum ada
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Add datetime filter
    @app.template_filter('datetime')
    def format_datetime(value):
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        return value.strftime("%d %B %Y %H:%M")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth_bp.login'
    mail.init_app(app)

    # Store app reference for utils
    app.app_context().push()
    
    # Register blueprints and init database
    with app.app_context():
        @login_manager.user_loader
        def load_user(user_id):
            from app.models import User
            return User.query.get(int(user_id))

        from .routes import register_blueprints
        register_blueprints(app)

    return app