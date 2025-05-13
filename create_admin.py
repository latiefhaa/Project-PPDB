from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        new_admin = User(
            username="admin",
            email="new_admin@gmail.com",
            is_admin=True
        )
        new_admin.set_password("password123")
        db.session.add(new_admin)