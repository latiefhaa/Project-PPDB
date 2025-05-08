import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Inisialisasi ekstensi
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_class=None):
    app = Flask(__name__)

    # Konfigurasi aplikasi
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///siswa.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'mysecret'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/profile_pics')
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max

    # Buat folder upload jika belum ada
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inisialisasi ekstensi
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth_bp.login'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Daftarkan Blueprint
    from .routes import register_blueprints
    register_blueprints(app)

    # Buat tabel database jika belum ada
    with app.app_context():
        from app import models
        db.create_all()

    return app