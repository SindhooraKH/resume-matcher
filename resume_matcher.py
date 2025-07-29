import os
import re
import spacy
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Dummy user data
users = {
    "SINDHOORAKH": {"email": "test@example.com", "password": "YourPassword123!"}
}

# NLP setup
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer("all-MiniLM-L6-v2")

# --- Helper functions ---

def clean_text(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()

def combined_similarity(text1, text2):
    text1 = clean_text(text1)
    text2 = clean_text(text2)

    tfidf = TfidfVectorizer().fit([text1, text2])
    tfidf_sim = cosine_similarity(tfidf.transform([text1]), tfidf.transform([text2]))[0][0]

    emb1 = model.encode(text1, convert_to_tensor=True)
    emb2 = model.encode(text2, convert_to_tensor=True)
    emb_sim = util.cos_sim(emb1, emb2).item()

    return 0.5 * tfidf_sim + 0.5 * emb_sim

def match_jobs_to_resume(resume_text, job_listings, threshold=0.3):
    resume_text_cleaned = clean_text(resume_text)
    matched_jobs = []

    for job in job_listings:
        job_desc = job.get("description", "")
        job_location = job.get("location", {}).get("display_name", "")

        if not job_desc:
            continue

        sim = combined_similarity(resume_text_cleaned, job_desc)
        if sim >= threshold and "india" in job_location.lower():
            matched_jobs.append({
                "title": job.get("title", "No title"),
                "location": job_location,
                "description": job_desc[:300] + "...",
                "redirect_url": job.get("redirect_url", "#"),
                "similarity": round(sim * 100, 2)
            })

    matched_jobs.sort(key=lambda x: x["similarity"], reverse=True)
    return matched_jobs


# Adzuna API credentials
APP_ID = 'acb861bf'
APP_KEY = 'aa3b402d110d32be2cf914e5dc28d0f6'

def fetch_jobs_from_adzuna(role):
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": role,
        "results_per_page": 50,  # increased to 50 for more jobs
        "content-type": "application/json"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return []

# --- Login required decorator ---
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_email' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped

# --- Routes ---

@app.route('/')
def landing_or_index():
    if 'user_email' in session:
        return redirect(url_for('index'))
    else:
        return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        for username, user in users.items():
            if user['email'] == email and user['password'] == password:
                session['user_email'] = email
                session['username'] = username
                flash(f"Welcome back, {username}!", "success")
                return redirect(url_for('index'))

        flash("Invalid email or password.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if username in users:
            flash("Username already exists.", "danger")
            return redirect(url_for('register'))

        for user in users.values():
            if user['email'] == email:
                flash("Email already registered.", "danger")
                return redirect(url_for('register'))

        users[username] = {"email": email, "password": password}
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        file = request.files.get('resume')
        job_role = request.form.get('job_role')

        if not file or file.filename == '':
            flash("Please upload a resume file.", "danger")
            return redirect(request.url)

        filename = file.filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        # Read resume text (assuming PDF text extraction or simple read for demo)
        # For production, extract text properly from PDF or DOCX
        with open(save_path, "rb") as f:
            resume_text = f.read().decode(errors='ignore')  # simplistic reading, replace with real extraction

        jobs = fetch_jobs_from_adzuna(job_role)
        matched_jobs = match_jobs_to_resume(resume_text, jobs, threshold=0.25)

        return render_template('results.html',
                               matched_jobs=matched_jobs,
                               role=job_role,
                               username=session.get('username'))

    return render_template('index.html', username=session.get('username'))

if __name__ == '__main__':
    app.run(debug=True)
