import os
import fitz  # PyMuPDF
import spacy
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from sentence_transformers import SentenceTransformer, util

app = Flask(__name__)
app.secret_key = 'your-very-secret-key'

# Setup upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# NLP & model
model = SentenceTransformer('all-MiniLM-L6-v2')
nlp = spacy.load('en_core_web_sm')

# Adzuna API keys
APP_ID = 'acb861bf'
APP_KEY = 'aa3b402d110d32be2cf914e5dc28d0f6'

# In-memory users: email -> user info dict
users = {}

# --- Helper functions ---

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_email' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_skills(text):
    doc = nlp(text)
    skills = [chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3]
    return list(set(skills))

def fetch_jobs(role):
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": 50,
        "what": role,
        "content-type": "application/json"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('results', [])
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return []

def match_jobs(skills, job_listings, similarity_threshold=30.0):
    matched_jobs = []
    if not skills:
        return matched_jobs
    resume_embed = model.encode(" ".join(skills), convert_to_tensor=True)

    for job in job_listings:
        job_desc = job.get('description', '')
        job_embed = model.encode(job_desc, convert_to_tensor=True)
        similarity = util.cos_sim(resume_embed, job_embed).item() * 100

        if similarity >= similarity_threshold and "india" in job.get('location', {}).get('display_name', '').lower():
            matched_jobs.append({
                'title': job.get('title'),
                'location': job.get('location', {}).get('display_name'),
                'description': job_desc[:400] + "...",
                'similarity': round(similarity, 2),
                'redirect_url': job.get('redirect_url', '#')
            })

    return sorted(matched_jobs, key=lambda x: x['similarity'], reverse=True)[:10]

# --- Routes ---

@app.route('/', endpoint='landing')
def landing():
    if 'user_email' in session:
        return redirect(url_for('index'))
    else:
        return render_template('landing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()
    country = request.form.get('country', '').strip()
    agree_terms = request.form.get('agreeTerms')

    if not username or not email or not password or not country or not agree_terms:
        flash("All fields are required and Terms must be accepted.", "error")
        return render_template('register.html')

    if email in users:
        flash("Email already registered.", "error")
        return render_template('register.html')

    users[email] = {
        "username": username,
        "email": email,
        "password": password,
        "country": country
    }
    flash("Registration successful! Please login.", "success")
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()

    user = users.get(email)
    if user and user['password'] == password:
        session['user_email'] = email
        session['username'] = user['username']
        flash(f"Welcome, {user['username']}!", "success")
        return redirect(url_for('index'))

    flash("Invalid email or password.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        job_role = request.form.get('job_role', '').strip()
        resume_file = request.files.get('resume')

        if not resume_file or resume_file.filename == '':
            flash("Please upload your resume file.", "danger")
            return render_template('index.html', username=session.get('username'))

        if not job_role:
            flash("Please enter a job role.", "danger")
            return render_template('index.html', username=session.get('username'))

        if not resume_file.filename.lower().endswith('.pdf'):
            flash("Only PDF resumes are allowed.", "danger")
            return render_template('index.html', username=session.get('username'))

        filename = resume_file.filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        resume_file.save(save_path)

        session['uploaded_resume'] = save_path
        session['job_role'] = job_role

        return redirect(url_for('results'))

    return render_template('index.html', username=session.get('username'))

@app.route('/results')
@login_required
def results():
    uploaded_resume_path = session.get('uploaded_resume')
    job_role = session.get('job_role')

    if not uploaded_resume_path or not job_role:
        flash("Please upload your resume and enter job role first.", "warning")
        return redirect(url_for('index'))

    try:
        resume_text = extract_text_from_pdf(uploaded_resume_path)
    except Exception as e:
        flash(f"Failed to extract text from resume: {e}", "danger")
        return redirect(url_for('index'))

    skills = extract_skills(resume_text)

    jobs = fetch_jobs(job_role)
    if not jobs:
        flash("No jobs found for this role.", "warning")
        return redirect(url_for('index'))

    matched_jobs = match_jobs(skills, jobs)
    if not matched_jobs:
        flash("No job matches with similarity above 30%.", "warning")
        return redirect(url_for('index'))

    return render_template('results.html', matched_jobs=matched_jobs, role=job_role, username=session.get('username'))


if __name__ == '__main__':
    app.run(debug=True)
