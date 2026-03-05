import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'  # Change this for production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fairaid.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS ---

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='Staff')

class Beneficiary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    income = db.Column(db.Float)
    is_displaced = db.Column(db.Boolean, default=False)
    is_disabled = db.Column(db.Boolean, default=False)
    vulnerability_score = db.Column(db.Float)
    last_updated_by = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
@login_required
def index():
    search_query = request.args.get('search', '')
    
    if search_query:
        # Search for names that contain the query string (case-insensitive)
        applicants = Beneficiary.query.filter(Beneficiary.name.contains(search_query)).order_by(Beneficiary.vulnerability_score.desc()).all()
    else:
        applicants = Beneficiary.query.order_by(Beneficiary.vulnerability_score.desc()).all()
    
    # Recalculate stats for the visible list
    total = len(applicants)
    displaced_count = sum(1 for a in applicants if a.is_displaced)
    
    stats = {
        'total': total,
        'displaced_priority': f"{(displaced_count/total*100):.1f}%" if total > 0 else "0%",
    }
    
    return render_template('index.html', applicants=applicants, stats=stats, search_query=search_query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- INITIALIZATION ---

def init_db():
    with app.app_context():
        db.create_all()
        # Create a default admin user if none exists
        if not User.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin = User(username='admin', password=hashed_pw, role='Admin')
            db.session.add(admin)
            db.session.commit()
            print("Database initialized with admin:admin123")
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_beneficiary():
    if request.method == 'POST':
        # Get data from form
        name = request.form['name']
        age = int(request.form['age'])
        income = float(request.form['income'])
        is_displaced = 'is_displaced' in request.form
        is_disabled = 'is_disabled' in request.form
        
        # AUTOMATED SCORING LOGIC (AI-Assisted)
        # Higher score = Higher priority
        score = 0
        if income < 100: score += 40
        if is_displaced: score += 30
        if is_disabled: score += 20
        if age > 60 or age < 5: score += 10
        
        new_person = Beneficiary(
            name=name, age=age, income=income,
            is_displaced=is_displaced, is_disabled=is_disabled,
            vulnerability_score=score,
            last_updated_by=current_user.username
        )
        
        db.session.add(new_person)
        db.session.commit()
        flash('Beneficiary added successfully!')
        return redirect(url_for('index'))
        
    return render_template('add_beneficiary.html')
if __name__ == '__main__':
    init_db()
    app.run(debug=True)