import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from .models import User, Book, Reservation

from .database import db


# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure the instance folder exists
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Use an absolute path for the SQLite database
db_path = os.path.join(instance_path, 'library.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Initialize SQLAlchemy and Flask-Migrate
db.init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Flask-APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def calculate_fine(reservation):
    if reservation.status == 'approved' and datetime.utcnow() > reservation.due_date:
        overdue_days = (datetime.utcnow() - reservation.due_date).days
        fine_per_day = 1.0  # $1 per day
        return overdue_days * fine_per_day
    return 0.0

@app.route('/')
def home():
    logger.info("Route: home")
    return render_template('home.html')

@app.route('/search')
def search():
    logger.info("Route: search")
    query = request.args.get('query', '')
    logger.info(f"Search query: {query}")
    try:
        if query:
            books = Book.query.filter((Book.title.contains(query)) | (Book.author.contains(query))).all()
        else:
            books = Book.query.all()
        logger.info(f"Number of books found: {len(books)}")
        return render_template('search.html', books=books, query=query)
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        flash(f"An error occurred while searching: {str(e)}", 'error')
        return render_template('search.html', books=[], query=query)

@app.route('/api/search')
def api_search():
    logger.info("Route: api_search")
    query = request.args.get('query', '')
    try:
        if query:
            books = Book.query.filter((Book.title.contains(query)) | (Book.author.contains(query))).all()
        else:
            books = Book.query.all()
        
        book_list = []
        for book in books:
            book_info = {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'available': book.available
            }
            book_list.append(book_info)
        
        return jsonify(book_list)
    except Exception as e:
        logger.error(f"API Search Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    logger.info("Route: add_book")
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        quantity = request.form.get('quantity', type=int)
        
        existing_book = Book.query.filter_by(isbn=isbn).first()
        if existing_book:
            flash('A book with this ISBN already exists.', 'error')
            return redirect(url_for('add_book'))
        
        new_book = Book(title=title, author=author, isbn=isbn, quantity=quantity, available=quantity)
        
        try:
            db.session.add(new_book)
            db.session.commit()
            flash('Book added successfully!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            flash(f'An error occurred: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('add_book.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    logger.info("Route: signup")
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('signup'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            flash(f"An error occurred during signup: {str(e)}", 'error')
            db.session.rollback()

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.info("Route: login")
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        logger.info(f"Login attempt: Username: {username}, User found: {user is not None}")

        if user and check_password_hash(user.password, password):
            login_user(user)
            logger.info(f"User {username} logged in successfully. is_admin: {user.is_admin}")
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logger.info("Route: logout")
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    logger.info("Route: dashboard")
    if current_user.is_admin:
        logger.info(f"Admin {current_user.username} accessed admin dashboard.")
    else:
        logger.info(f"User {current_user.username} accessed user dashboard.")
    return render_template('home.html')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    logger.info("Route: admin_dashboard")
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        logger.warning(f"Non-admin user {current_user.username} tried to access admin dashboard.")
        return redirect(url_for('home'))
    
    # Fetch data for the dashboard
    total_books = Book.query.count()
    available_books = Book.query.filter_by(available=True).count()
    total_reservations = Reservation.query.count()
    
    return render_template('admin_dashboard.html', total_books=total_books, available_books=available_books, total_reservations=total_reservations)

@app.route('/reserve/<int:book_id>', methods=['POST'])
@login_required
def reserve_book(book_id):
    logger.info(f"Route: reserve_book for book_id {book_id}")
    book = Book.query.get_or_404(book_id)
    if book.available > 0:
        reservation = Reservation(user_id=current_user.id, book_id=book_id)
        reservation.due_date = datetime.utcnow() + timedelta(days=14)
        
        try:
            db.session.add(reservation)
            book.available -= 1
            db.session.commit()
            flash('Book reserved successfully!', 'success')
            logger.info(f"User {current_user.username} reserved book {book.title}.")
        except Exception as e:
            logger.error(f"Error reserving book: {e}")
            flash(f"An error occurred during reservation: {e}", 'error')
            db.session.rollback()
    else:
        flash('Sorry, this book is not available for reservation.', 'warning')
        logger.warning(f"Book {book.title} is not available for reservation.")
    
    return redirect(url_for('search'))

@app.route('/my_reservations')
@login_required
def my_reservations():
    logger.info("Route: my_reservations")
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    return render_template('my_reservations.html', reservations=reservations)

@app.route('/admin_reservations')
@login_required
def admin_reservations():
    logger.info("Route: admin_reservations")
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))
    
    reservations = Reservation.query.all()
    return render_template('admin_reservations.html', reservations=reservations)

@app.route('/update_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def update_reservation(reservation_id):
    logger.info(f"Route: update_reservation for reservation_id {reservation_id}")
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))
    
    reservation = Reservation.query.get_or_404(reservation_id)
    new_status = request.form.get('status')
    
    if new_status in ['pending', 'approved', 'cancelled', 'returned']:
        reservation.status = new_status
        if new_status == 'returned':
            reservation.date_returned = datetime.utcnow()
            book = Book.query.get(reservation.book_id)
            if book:
                book.available = min(book.quantity, book.available + 1)
                logger.info(f"Book {book.title} returned, available count incremented.")
            else:
                logger.warning(f"Book not found for reservation {reservation_id}.")
        
        try:
            db.session.commit()
            flash('Reservation updated successfully.', 'success')
            logger.info(f"Reservation {reservation_id} updated to status {new_status}.")
        except Exception as e:
            logger.error(f"Error updating reservation: {e}")
            flash(f"An error occurred updating the reservation: {e}", 'error')
            db.session.rollback()
    else:
        flash('Invalid status.', 'warning')
        logger.warning(f"Invalid status provided: {new_status}")
    
    return redirect(url_for('admin_reservations'))

@app.route('/book_circulation')
@login_required
def book_circulation():
    logger.info("Route: book_circulation")
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))
    
    issued_books = Reservation.query.filter(Reservation.status == 'approved').all()
    returned_books = Reservation.query.filter(Reservation.status == 'returned').all()
    
    return render_template('admin_book_circulation.html', 
                         issued_books=issued_books, 
                         returned_books=returned_books,
                         datetime=datetime)

@app.route('/return_book/<int:reservation_id>', methods=['POST'])
@login_required
def return_book(reservation_id):
    logger.info(f"Route: return_book for reservation_id {reservation_id}")
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))
    
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.status == 'approved':
        reservation.status = 'returned'
        reservation.date_returned = datetime.utcnow()
        reservation.fine_amount = calculate_fine(reservation)
        
        book = Book.query.get(reservation.book_id)
        if book:
            book.available = min(book.quantity, book.available + 1)
            logger.info(f"Book {book.title} returned, available count incremented.")
        else:
            logger.warning(f"Book not found for reservation {reservation_id}.")
        
        try:
            db.session.commit()
            flash('Book returned successfully.', 'success')
            logger.info(f"Book returned successfully for reservation {reservation_id}.")
        except Exception as e:
            logger.error(f"Error returning book: {e}")
            flash(f"An error occurred while returning the book: {e}", 'error')
            db.session.rollback()
    else:
        flash('Invalid reservation status for return.', 'warning')
        logger.warning(f"Attempted to return book with invalid reservation status for reservation {reservation_id}.")
    
    return redirect(url_for('admin_reservations'))

@app.route('/overdue_books')
@login_required
def overdue_books():
    logger.info("Route: overdue_books")
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))
    
    overdue_reservations = Reservation.query.filter(
        Reservation.status == 'approved',
        Reservation.due_date < datetime.utcnow()
    ).all()
    
    for reservation in overdue_reservations:
        reservation.fine_amount = calculate_fine(reservation)
    
    try:
        db.session.commit()
        return render_template('admin_overdue_books.html', overdue_reservations=overdue_reservations, datetime=datetime)
    except Exception as e:
        logger.error(f"Error displaying overdue books: {e}")
        flash(f"An error occurred while displaying overdue books: {e}", 'error')
        return render_template('admin_overdue_books.html', overdue_reservations=[], datetime=datetime)

@scheduler.task('cron', id='update_fines', hour=0)
def update_fines():
    with app.app_context():
        logger.info("Running scheduled task: update_fines")
        overdue_reservations = Reservation.query.filter(
            Reservation.status == 'approved',
            Reservation.due_date < datetime.utcnow()
        ).all()
        
        for reservation in overdue_reservations:
            reservation.fine_amount = calculate_fine(reservation)
        
        try:
            db.session.commit()
            logger.info("Fines updated successfully.")
        except Exception as e:
            logger.error(f"Error updating fines: {e}")

@app.errorhandler(404)
def page_not_found(error):
    logger.warning(f"Page not found: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server Error: {error}")
    return render_template('500.html'), 500

def create_admin():
    logger.info("Checking or creating admin user...")
    with app.app_context():
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            hashed_password = generate_password_hash("admin_password")
            admin_user = User(username='admin', password=hashed_password, is_admin=True)
            db.session.add(admin_user)
            try:
                db.session.commit()
                logger.info("Admin user created successfully.")
            except Exception as e:
                logger.error(f"Error creating admin user: {e}")
                db.session.rollback()
        else:
            logger.info("Admin user already exists.")

# Initialize database and create admin user
with app.app_context():
    db.create_all()
    create_admin()

if __name__ == '__main__':
    app.run(debug=True)
