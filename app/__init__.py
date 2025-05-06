from flask import Flask
from app.routes import register_blueprints

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'ppdb-secret'
    
    register_blueprints(app)
    return app
