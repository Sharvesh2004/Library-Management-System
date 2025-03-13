import sys
import os

# Add the root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from library_management.app import app, db, User
from werkzeug.security import generate_password_hash

# Push an application context
with app.app_context():
    # Hash the password
    hashed_password = generate_password_hash('password123', method='pbkdf2:sha256')

    # Create a new user instance
    new_user = User(username='testuser', password=hashed_password, role='user')

    # Add the user to the database
    db.session.add(new_user)
    db.session.commit()

    print("User added successfully!")
