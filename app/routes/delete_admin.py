from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Cari admin berdasarkan username atau email
    admin = User.query.filter_by(username="admin").first()  # Ganti "admin" dengan username admin yang ingin dihapus

    if admin and admin.is_admin:
        db.session.delete(admin)
        db.session.commit()
        print(f"Admin dengan username '{admin.username}' berhasil dihapus!")
    else:
        print("Admin tidak ditemukan atau bukan admin.")