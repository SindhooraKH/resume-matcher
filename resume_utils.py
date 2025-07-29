from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
from job_fetcher import fetch_jobs_from_adzuna
from resume_matcher import match_jobs_to_resume

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory user storage
users = {}

def check_user_credentials(email, password):
    user = users.get(email)
    if user and user['password'] == password:
        return user
    return None

def register_user(username, email, password, country):
    if email in users:
        return False, "Email already registered."
    users[email] = {
        'username': username,
        'email': email,
        'password': password,
        'country': country
    }
    return True, "Registration successful."

@app.route('/')
def root():
    return redirect(url_for('index'))

@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        resume = request.files.get('resume')
        role = request.form.get('job_role')

        if not resume or not role:
            error = "Please upload resume and enter a job role."
        else:
            filename = secure_filename(resume.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(filepath)

            with open(filepath, 'rb') as f:
                resume_text = f.read().decode('utf-8', errors='ignore')

            jobs = fetch_jobs_from_adzuna(role)
            matched_jobs = match_jobs_to_resume(resume_text, jobs)

            return render_template('results.html',
                                   matched_jobs=matched_jobs,
                                   role=role,
                                   username=session['username'])

    return render_template('index.html', username=session['username'], error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = check_user_credentials(email, password)
        if user:
            session['username'] = user['username']
            session['email'] = email
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password.", "error")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        country = request.form.get('country', '')

        success, message = register_user(username, email, password, country)
        if success:
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash(message, "error")

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
