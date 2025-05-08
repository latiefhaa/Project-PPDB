from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Cari admin yang ada berdasarkan username atau email
    admin = User.query.filter_by(username="admin").first()  # Ganti "admin" dengan username admin yang ingin diganti

    if admin and admin.is_admin:
        # Perbarui data admin
        admin.username = "admin"  # Ganti dengan username baru
        admin.email = "new_admin@gmail.com"  # Ganti dengan email baru
        admin.set_password("123")  # Ganti dengan password baru
        db.session.commit()
        print("Admin berhasil diperbarui!")
    else:
        print("Admin tidak ditemukan atau bukan admin.")