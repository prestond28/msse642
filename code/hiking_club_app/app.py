import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from models import get_db, close_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-before-deployment')

app.teardown_appcontext(close_db)


@app.context_processor
def inject_user():
    return {'user': current_user()}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return get_db().execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access that page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = current_user()
        if not user or user['role'] != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        name = request.form.get('name', '').strip()

        if not username or not email or not password:
            flash('Username, email, and password are required.', 'danger')
            return render_template('register.html')

        db = get_db()
        if db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            flash('Username already taken.', 'danger')
            return render_template('register.html')
        if db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        db.execute(
            'INSERT INTO users (username, email, password_hash, name) VALUES (?, ?, ?, ?)',
            (username, email, generate_password_hash(password), name)
        )
        db.commit()
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        user = get_db().execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')
        if not user['is_active']:
            flash('Your account has been disabled. Contact an administrator.', 'danger')
            return render_template('login.html')

        session.clear()
        session['user_id'] = user['id']
        return redirect(url_for('trips'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('trips'))


# ---------------------------------------------------------------------------
# Trips (public + member)
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return redirect(url_for('trips'))


@app.route('/trips')
def trips():
    db = get_db()
    all_trips = db.execute(
        'SELECT t.*, u.name AS leader_name FROM trips t JOIN users u ON t.created_by = u.id ORDER BY t.date'
    ).fetchall()
    user = current_user()

    registered_ids = set()
    if user:
        rows = db.execute('SELECT trip_id FROM registrations WHERE user_id = ?', (user['id'],)).fetchall()
        registered_ids = {r['trip_id'] for r in rows}

    return render_template('trips.html', trips=all_trips, registered_ids=registered_ids)


@app.route('/trips/<int:trip_id>/register', methods=['POST'])
@login_required
def register_trip(trip_id):
    db = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id = ?', (trip_id,)).fetchone()
    if not trip:
        abort(404)

    uid = session['user_id']
    existing = db.execute(
        'SELECT id FROM registrations WHERE user_id = ? AND trip_id = ?', (uid, trip_id)
    ).fetchone()
    if existing:
        flash('You are already registered for this trip.', 'info')
    else:
        db.execute('INSERT INTO registrations (user_id, trip_id) VALUES (?, ?)', (uid, trip_id))
        db.commit()
        flash(f'Registered for "{trip["name"]}"!', 'success')

    return redirect(url_for('trips'))


@app.route('/trips/<int:trip_id>/unregister', methods=['POST'])
@login_required
def unregister_trip(trip_id):
    db = get_db()
    db.execute(
        'DELETE FROM registrations WHERE user_id = ? AND trip_id = ?',
        (session['user_id'], trip_id)
    )
    db.commit()
    flash('Unregistered from trip.', 'info')
    return redirect(url_for('trips'))


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@app.route('/profile')
@login_required
def profile():
    user = current_user()
    return render_template('profile.html', user=user)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    db = get_db()
    uid = session['user_id']
    user = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()

        if not email:
            flash('Email is required.', 'danger')
            return render_template('edit_profile.html', user=user)

        conflict = db.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, uid)).fetchone()
        if conflict:
            flash('That email is already in use by another account.', 'danger')
            return render_template('edit_profile.html', user=user)

        db.execute(
            'UPDATE users SET name = ?, email = ?, emergency_contact = ? WHERE id = ?',
            (name, email, emergency_contact, uid)
        )
        db.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)


# ---------------------------------------------------------------------------
# Admin — trips
# ---------------------------------------------------------------------------

@app.route('/admin/trips/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_trip():
    if request.method == 'POST':
        name = request.form['name'].strip()
        date = request.form['date'].strip()
        description = request.form['description'].strip()

        if not name or not date or not description:
            flash('All fields are required.', 'danger')
            return render_template('trip_form.html', trip=None)

        db = get_db()
        db.execute(
            'INSERT INTO trips (name, date, description, created_by) VALUES (?, ?, ?, ?)',
            (name, date, description, session['user_id'])
        )
        db.commit()
        flash('Trip created.', 'success')
        return redirect(url_for('trips'))

    return render_template('trip_form.html', trip=None)


@app.route('/admin/trips/<int:trip_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_trip(trip_id):
    db = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id = ?', (trip_id,)).fetchone()
    if not trip:
        abort(404)

    if request.method == 'POST':
        name = request.form['name'].strip()
        date = request.form['date'].strip()
        description = request.form['description'].strip()

        if not name or not date or not description:
            flash('All fields are required.', 'danger')
            return render_template('trip_form.html', trip=trip)

        db.execute(
            'UPDATE trips SET name = ?, date = ?, description = ? WHERE id = ?',
            (name, date, description, trip_id)
        )
        db.commit()
        flash('Trip updated.', 'success')
        return redirect(url_for('trips'))

    return render_template('trip_form.html', trip=trip)


@app.route('/admin/trips/<int:trip_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_trip(trip_id):
    db = get_db()
    db.execute('DELETE FROM registrations WHERE trip_id = ?', (trip_id,))
    db.execute('DELETE FROM trips WHERE id = ?', (trip_id,))
    db.commit()
    flash('Trip deleted.', 'info')
    return redirect(url_for('trips'))


@app.route('/admin/trips/<int:trip_id>/roster')
@login_required
@admin_required
def trip_roster(trip_id):
    db = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id = ?', (trip_id,)).fetchone()
    if not trip:
        abort(404)
    members = db.execute(
        '''SELECT u.name, u.username, u.email
           FROM registrations r JOIN users u ON r.user_id = u.id
           WHERE r.trip_id = ?
           ORDER BY u.name''',
        (trip_id,)
    ).fetchall()
    return render_template('roster.html', trip=trip, members=members)


# ---------------------------------------------------------------------------
# Admin — users
# ---------------------------------------------------------------------------

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = get_db().execute('SELECT * FROM users ORDER BY username').fetchall()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/<int:uid>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(uid):
    if uid == session['user_id']:
        flash('You cannot disable your own account.', 'danger')
        return redirect(url_for('admin_users'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    if not user:
        abort(404)

    new_state = 0 if user['is_active'] else 1
    db.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_state, uid))
    db.commit()
    action = 'enabled' if new_state else 'disabled'
    flash(f'Account "{user["username"]}" {action}.', 'info')
    return redirect(url_for('admin_users'))


# ---------------------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Access denied.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page not found.'), 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db(app)
    app.run(host='0.0.0.0', port=5000, debug=False)
