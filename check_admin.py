import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library_management.app import app, db, User

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f"Admin user exists: {admin.username}, Is Admin: {admin.is_admin}")
    else:
        print("No admin user found.")
