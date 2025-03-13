import sys
import os

# Add the current directory to Python's path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app import app, db, User

with app.app_context():
    user = User.query.first()
    if user:
        print(f"is_admin column value for the first user: {user.is_admin}")
    else:
        print("No users found in the database.")
