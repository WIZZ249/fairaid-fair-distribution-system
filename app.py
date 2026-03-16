import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import csv, io, json

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'fairaid-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///fairaid.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ── MODELS ────────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role     = db.Column(db.String(20), default='Staff')

class Beneficiary(db.Model):
    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(100), nullable=False)
    age                 = db.Column(db.Integer)
    income              = db.Column(db.Float, default=0.0)
    household_size      = db.Column(db.Integer, default=1)
    is_displaced        = db.Column(db.Boolean, default=False)
    is_disabled         = db.Column(db.Boolean, default=False)
    vulnerability_score = db.Column(db.Float, default=0.0)
    location            = db.Column(db.String(100))
    notes               = db.Column(db.Text)
    source              = db.Column(db.String(50), default='manual')
    status              = db.Column(db.String(20), default='active')
    last_updated_by     = db.Column(db.String(50))
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

class QueuedBeneficiary(db.Model):
    """Incoming data from external sources waiting for admin review."""
    id             = db.Column(db.Integer, primary_key=True)
    raw_data       = db.Column(db.Text, nullable=False)
    source         = db.Column(db.String(50))
    status         = db.Column(db.String(20), default='pending')
    submitted_at   = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_by    = db.Column(db.String(50))
    reviewed_at    = db.Column(db.DateTime)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── SCORING ───────────────────────────────────────────────────────────────────

def calculate_score(age, income, household_size, is_displaced, is_disabled):
    score = 0
    if age >= 65:          score += 20
    if is_disabled:        score += 25
    if income < 20:        score += 30
    elif income < 50:      score += 15
    if household_size >= 5: score += 10
    if is_displaced:       score += 20
    return score

def score_label(score):
    if score >= 70: return 'Critical'
    if score >= 40: return 'High'
    if score >= 20: return 'Medium'
    return 'Low'

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'active')
    sort = request.args.get('sort', 'score')

    query = Beneficiary.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if search_query:
        query = query.filter(Beneficiary.name.ilike(f'%{search_query}%'))
    if sort == 'score':
        query = query.order_by(Beneficiary.vulnerability_score.desc())
    elif sort == 'name':
        query = query.order_by(Beneficiary.name.asc())
    elif sort == 'date':
        query = query.order_by(Beneficiary.created_at.desc())

    applicants = query.all()
    total = Beneficiary.query.count()
    displaced = Beneficiary.query.filter_by(is_displaced=True).count()
    disabled  = Beneficiary.query.filter_by(is_disabled=True).count()
    critical  = Beneficiary.query.filter(Beneficiary.vulnerability_score >= 70).count()
    pending_queue = QueuedBeneficiary.query.filter_by(status='pending').count()

    stats = {
        'total': total,
        'displaced': displaced,
        'disabled': disabled,
        'critical': critical,
        'pending_queue': pending_queue,
        'displaced_pct': f"{(displaced/total*100):.0f}%" if total else "0%",
    }
    return render_template('index.html', applicants=applicants, stats=stats,
                           search_query=search_query, status_filter=status_filter,
                           sort=sort, score_label=score_label)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_beneficiary():
    if request.method == 'POST':
        age            = int(request.form.get('age', 0))
        income         = float(request.form.get('income', 0))
        household_size = int(request.form.get('household_size', 1))
        is_displaced   = request.form.get('is_displaced') == 'on'
        is_disabled    = request.form.get('is_disabled') == 'on'
        score = calculate_score(age, income, household_size, is_displaced, is_disabled)
        b = Beneficiary(
            name=request.form.get('name'),
            age=age, income=income, household_size=household_size,
            is_displaced=is_displaced, is_disabled=is_disabled,
            location=request.form.get('location'),
            notes=request.form.get('notes'),
            vulnerability_score=score,
            source='manual',
            last_updated_by=current_user.username
        )
        db.session.add(b)
        db.session.commit()
        flash(f'Beneficiary {b.name} added. Vulnerability score: {score}', 'success')
        return redirect(url_for('index'))
    return render_template('add_beneficiary.html')

@app.route('/delete/<int:id>')
@login_required
def delete_beneficiary(id):
    b = Beneficiary.query.get_or_404(id)
    db.session.delete(b)
    db.session.commit()
    flash(f'{b.name} removed.', 'info')
    return redirect(url_for('index'))

@app.route('/status/<int:id>/<string:new_status>')
@login_required
def update_status(id, new_status):
    b = Beneficiary.query.get_or_404(id)
    if new_status in ['active', 'served', 'inactive']:
        b.status = new_status
        b.last_updated_by = current_user.username
        db.session.commit()
    return redirect(url_for('index'))

# ── CSV UPLOAD ────────────────────────────────────────────────────────────────

@app.route('/upload-csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        mode = request.form.get('mode', 'queue')
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'danger')
            return redirect(url_for('upload_csv'))

        stream = io.StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)
        added = 0
        queued = 0
        errors = 0

        for row in reader:
            try:
                if mode == 'direct':
                    age            = int(row.get('age', 0))
                    income         = float(row.get('income', 0))
                    household_size = int(row.get('household_size', 1))
                    is_displaced   = str(row.get('is_displaced', '')).lower() in ['yes', 'true', '1']
                    is_disabled    = str(row.get('is_disabled', '')).lower() in ['yes', 'true', '1']
                    score = calculate_score(age, income, household_size, is_displaced, is_disabled)
                    b = Beneficiary(
                        name=row.get('name', 'Unknown'),
                        age=age, income=income, household_size=household_size,
                        is_displaced=is_displaced, is_disabled=is_disabled,
                        location=row.get('location', ''),
                        notes=row.get('notes', ''),
                        vulnerability_score=score,
                        source='csv_upload',
                        last_updated_by=current_user.username
                    )
                    db.session.add(b)
                    added += 1
                else:
                    q = QueuedBeneficiary(raw_data=json.dumps(row), source='csv_upload')
                    db.session.add(q)
                    queued += 1
            except Exception:
                errors += 1

        db.session.commit()
        if mode == 'direct':
            flash(f'CSV imported: {added} added, {errors} errors.', 'success')
        else:
            flash(f'CSV queued: {queued} records waiting for review, {errors} errors.', 'info')
        return redirect(url_for('index'))
    return render_template('upload_csv.html')

# ── EXPORT ────────────────────────────────────────────────────────────────────

@app.route('/export')
@login_required
def export_csv():
    beneficiaries = Beneficiary.query.order_by(Beneficiary.vulnerability_score.desc()).all()
    def generate():
        yield 'id,name,age,income,household_size,is_displaced,is_disabled,vulnerability_score,location,status,source,created_at\n'
        for b in beneficiaries:
            yield f'{b.id},{b.name},{b.age},{b.income},{b.household_size},{b.is_displaced},{b.is_disabled},{b.vulnerability_score},{b.location or ""},{b.status},{b.source},{b.created_at}\n'
    return Response(generate(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=fairaid_export.csv'})

# ── QUEUE ─────────────────────────────────────────────────────────────────────

@app.route('/queue')
@login_required
def view_queue():
    items = QueuedBeneficiary.query.order_by(QueuedBeneficiary.submitted_at.desc()).all()
    parsed = []
    for item in items:
        try:
            parsed.append({'item': item, 'data': json.loads(item.raw_data)})
        except:
            parsed.append({'item': item, 'data': {}})
    return render_template('queue.html', items=parsed)

@app.route('/queue/approve/<int:id>')
@login_required
def approve_queue(id):
    q = QueuedBeneficiary.query.get_or_404(id)
    try:
        row = json.loads(q.raw_data)
        age            = int(row.get('age', 0))
        income         = float(row.get('income', 0))
        household_size = int(row.get('household_size', 1))
        is_displaced   = str(row.get('is_displaced', '')).lower() in ['yes', 'true', '1']
        is_disabled    = str(row.get('is_disabled', '')).lower() in ['yes', 'true', '1']
        score = calculate_score(age, income, household_size, is_displaced, is_disabled)
        b = Beneficiary(
            name=row.get('name', 'Unknown'),
            age=age, income=income, household_size=household_size,
            is_displaced=is_displaced, is_disabled=is_disabled,
            location=row.get('location', ''),
            notes=row.get('notes', ''),
            vulnerability_score=score,
            source=q.source,
            last_updated_by=current_user.username
        )
        db.session.add(b)
        q.status = 'approved'
        q.reviewed_by = current_user.username
        q.reviewed_at = datetime.utcnow()
        db.session.commit()
        flash(f'{b.name} approved and added.', 'success')
    except Exception as e:
        flash(f'Error approving: {e}', 'danger')
    return redirect(url_for('view_queue'))

@app.route('/queue/reject/<int:id>')
@login_required
def reject_queue(id):
    q = QueuedBeneficiary.query.get_or_404(id)
    q.status = 'rejected'
    q.reviewed_by = current_user.username
    q.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash('Record rejected.', 'info')
    return redirect(url_for('view_queue'))

# ── API ENDPOINTS ─────────────────────────────────────────────────────────────

@app.route('/api/ingest', methods=['POST'])
def api_ingest():
    """External systems can POST beneficiary data here."""
    api_key = request.headers.get('X-API-Key')
    if api_key != os.getenv('API_KEY', 'fairaid-api-key-2026'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    records = data if isinstance(data, list) else [data]
    queued = 0
    for record in records:
        q = QueuedBeneficiary(raw_data=json.dumps(record), source='api')
        db.session.add(q)
        queued += 1
    db.session.commit()
    return jsonify({'status': 'queued', 'records': queued}), 201

@app.route('/api/beneficiaries')
def api_beneficiaries():
    """Public read endpoint for beneficiary data."""
    api_key = request.headers.get('X-API-Key')
    if api_key != os.getenv('API_KEY', 'fairaid-api-key-2026'):
        return jsonify({'error': 'Unauthorized'}), 401
    beneficiaries = Beneficiary.query.order_by(Beneficiary.vulnerability_score.desc()).all()
    return jsonify([{
        'id': b.id, 'name': b.name, 'age': b.age,
        'vulnerability_score': b.vulnerability_score,
        'severity': score_label(b.vulnerability_score),
        'is_displaced': b.is_displaced, 'is_disabled': b.is_disabled,
        'status': b.status, 'source': b.source
    } for b in beneficiaries])

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'FairAid'}), 200

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

# ── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            hashed = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin = User(username='admin', password=hashed, role='Admin')
            db.session.add(admin)
            db.session.commit()
            print('Database initialized. Login: admin / admin123')
# ── USER MANAGEMENT ───────────────────────────────────────────────────────────

@app.route('/users')
@login_required
def manage_users():
    if current_user.role != 'Admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/users/create', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'Admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('index'))
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'Staff')
    if User.query.filter_by(username=username).first():
        flash(f'Username {username} already exists.', 'danger')
        return redirect(url_for('manage_users'))
    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('manage_users'))
    u = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'), role=role)
    db.session.add(u)
    db.session.commit()
    flash(f'User {username} created successfully!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/users/delete/<int:id>')
@login_required
def delete_user(id):
    if current_user.role != 'Admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('index'))
    u = User.query.get_or_404(id)
    if u.username == current_user.username:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('manage_users'))
    db.session.delete(u)
    db.session.commit()
    flash(f'User {u.username} deleted.', 'info')
    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
