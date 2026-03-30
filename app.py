import os
import sqlite3
from flask import Flask, redirect, url_for, session, render_template, request, flash
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "LMS_SUPER_SECRET_KEY"

# --- Google OAuth Setup ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# --- Database Helper ---
def get_db():
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

# --- Initialize Database ---
def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT, is_approved INTEGER DEFAULT 0)')
        c.execute('''CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        name TEXT, 
                        resource TEXT, 
                        join_date TEXT, 
                        return_date TEXT, 
                        total_fee INTEGER, 
                        paid INTEGER)''')
        # Admin setup
        c.execute("INSERT OR IGNORE INTO users (email, name, is_approved) VALUES ('Aak803110@gmail.com', 'Admin', 1)")
        conn.commit()

# Run init_db when the app starts
init_db()

# --- Routes ---

@app.route('/')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    
    conn = get_db()
    students = conn.execute('SELECT * FROM students ORDER BY id DESC LIMIT 5').fetchall()
    stats = {
        'total_students': conn.execute('SELECT COUNT(*) FROM students').fetchone()[0],
        'total_revenue': conn.execute('SELECT SUM(paid) FROM students').fetchone()[0] or 0
    }
    conn.close()
    return render_template('dashboard.html', students=students, stats=stats)

@app.route('/students')
def students_list():
    if 'user' not in session: return redirect(url_for('login_page'))
    
    conn = get_db()
    students = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    return render_template('students.html', students=students)

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/authorize')
def authorize():
    redirect_uri = url_for('callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/callback')
def callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if user_info:
        session['user'] = user_info
        # Check if user is in our database, if not, add them (unapproved)
        conn = get_db()
        conn.execute('INSERT OR IGNORE INTO users (email, name) VALUES (?, ?)', 
                     (user_info['email'], user_info['name']))
        conn.commit()
        conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True)
