import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# ── Load environment variables ───────────────────────────────────────────────
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///fairaid.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ── DATABASE MODELS ──────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role     = db.Column(db.String(20), default='Staff')

class Beneficiary(db.Model):
    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(100), nullable=False)
    age                 = db.Column(db.Integer)
    income              = db.Column(db.Float)
    is_displaced        = db.Column(db.Boolean, default=False)
    is_disabled         = db.Column(db.Boolean, default=False)
    vulnerability_score = db.Column(db.Float)
    last_updated_by     = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    search_query = request.args.get('search', '').strip()
    if search_query:
        applicants = Beneficiary.query.filter(
            Beneficiary.name.ilike(f"%{search_query}%")
        ).order_by(Beneficiary.vulnerability_score.desc()).all()
    else:
        applicants = Beneficiary.query.order_by(
            Beneficiary.vulnerability_score.desc()
        ).all()

    total = len(applicants)
    displaced_count = sum(1 for a in applicants if a.is_displaced)
    stats = {
        'total': total,
        'displaced_priority': f"{(displaced_count/total*100):.1f}%" if total > 0 else "0%",
    }
    return render_template('index.html', applicants=applicants, stats=stats, search_query=search_query)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_beneficiary():
    if request.method == 'POST':
        from scoring import calculate_vulnerability_score
        person = {
            'age':            int(request.form.get('age', 0)),
            'disability':     'Yes' if request.form.get('is_disabled') else 'No',
            'monthly_income': float(request.form.get('income', 0)),
            'household_size': int(request.form.get('household_size', 1)),
            'displaced':      'Yes' if request.form.get('is_displaced') else 'No',
        }
        score = calculate_vulnerability_score(person)
        new_beneficiary = Beneficiary(
            name                = request.form.get('name'),
            age                 = person['age'],
            income              = person['monthly_income'],
            is_displaced        = request.form.get('is_displaced') == 'on',
            is_disabled         = request.form.get('is_disabled') == 'on',
            vulnerability_score = score,
            last_updated_by     = current_user.username
        )
        db.session.add(new_beneficiary)
        db.session.commit()
        flash(f'Beneficiary {new_beneficiary.name} added successfully! Score: {score}', 'success')
        return redirect(url_for('index'))
    return render_template('add_beneficiary.html')

@app.route('/delete/<int:id>')
@login_required
def delete_beneficiary(id):
    beneficiary = Beneficiary.query.get_or_404(id)
    db.session.delete(beneficiary)
    db.session.commit()
    flash(f'Beneficiary {beneficiary.name} deleted.', 'info')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/health')
def health():
    """Health check endpoint for deployment."""
    return {'status': 'ok', 'service': 'FairAid'}, 200

# ── INITIALIZATION ───────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin = User(username='admin', password=hashed_pw, role='Admin')
            db.session.add(admin)
            db.session.commit()
            print("✅ Database initialized with admin:admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)