import os
import sys

# Add the parent directory to sys.path to resolve imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from library_management.app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        hashed_password = generate_password_hash("admin_password")
        admin = User(username='admin', password=hashed_password, is_admin=True)
        db.session.add(admin)
        print("Admin user created.")
    else:
        admin.is_admin = True
        print("Admin privileges updated.")

    db.session.commit()
