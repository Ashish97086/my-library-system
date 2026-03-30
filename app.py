import os
import sqlite3
from flask import Flask, redirect, url_for, session, render_template, request
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "LMS_SUPER_SECRET_KEY"

# --- Google OAuth Setup ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='YOUR_GOOGLE_CLIENT_ID', 
    client_secret='YOUR_GOOGLE_CLIENT_SECRET',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT, is_approved INTEGER DEFAULT 0)')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, resource TEXT, 
                  join_date TEXT, return_date TEXT, total_fee INTEGER, paid INTEGER)''')
    # Admin Email (Yahan apna email daalein)
    c.execute("INSERT OR IGNORE INTO users (email, name, is_approved) VALUES ('aak803110@gmail.com', 'Admin', 1)")
    conn.commit()
    conn.close()

# --- Custom Routes ---

@app.route('/')
def dashboard():
    if 'user' not in session: return render_template('login.html')
    conn = sqlite3.connect('library.db')
    students = conn.execute("SELECT * FROM students").fetchall()
    reminders = []
    today = datetime.now().date()
    for s in students:
        ret_date = datetime.strptime(s[4], '%Y-%m-%d').date()
        if ret_date < today: reminders.append(f"⚠️ {s[1]} ka time khatam!")
        if (s[5]-s[6]) > 0: reminders.append(f"💰 {s[1]} ka payment baki hai.")
    conn.close()
    return render_template('dashboard.html', students=students, reminders=reminders)

@app.route('/students')
def student_list():
    if 'user' not in session: return redirect('/')
    conn = sqlite3.connect('library.db')
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template('students.html', students=students)

@app.route('/payments')
def payment_history():
    if 'user' not in session: return redirect('/')
    conn = sqlite3.connect('library.db')
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template('payments.html', students=students)

@app.route('/add', methods=['POST'])
def add_entry():
    name, res = request.form['name'], request.form['resource']
    days, paid = int(request.form['days']), int(request.form['paid'])
    join_date = datetime.now().strftime('%Y-%m-%d')
    ret_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('library.db')
    conn.execute("INSERT INTO students (name, resource, join_date, return_date, total_fee, paid) VALUES (?,?,?,?,?,?)",
                 (name, res, join_date, ret_date, 500, paid))
    conn.commit()
    conn.close()
    return redirect('/')

# --- Auth Routes ---
@app.route('/login')
def login(): return google.authorize_redirect(url_for('auth', _external=True))

@app.route('/auth')
def auth():
    token = google.authorize_access_token()
    user_info = google.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
    email = user_info['email']
    conn = sqlite3.connect('library.db')
    user = conn.execute("SELECT is_approved FROM users WHERE email=?", (email,)).fetchone()
    if user and user[0] == 1:
        session['user'] = email
        return redirect('/')
    return "<h1>Access Denied</h1><p>Admin se approval lein.</p>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
