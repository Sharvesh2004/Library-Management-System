import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from library_management.app import app
from library_management.database import db
from library_management.models import Book

with app.app_context():
    db.create_all()  # This creates the tables if they don't exist
    books = [
        Book(title="To Kill a Mockingbird", author="Harper Lee", isbn="9780061120084", quantity=5, available=5),
        Book(title="1984", author="George Orwell", isbn="9780451524935", quantity=3, available=3),
        Book(title="Pride and Prejudice", author="Jane Austen", isbn="9780141439518", quantity=4, available=4)
    ]
    db.session.bulk_save_objects(books)
    db.session.commit()
    print("Sample books added successfully!")
