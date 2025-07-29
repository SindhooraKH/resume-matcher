# MatchMySkills - Resume to Job Matcher

MatchMySkills is a Flask web application that helps job seekers match their resumes with relevant job listings by analyzing skills and semantic similarity.

## Features

- User registration and login system with secure authentication
- Resume upload with skill extraction using NLP (SpaCy)
- Fetches job listings from the Adzuna API
- Matches jobs to resumes based on semantic similarity of skills
- Clean GitHub-style dark-themed UI

## Project Structure

- `app.py` - Main Flask app with routes for user auth, resume upload, and matching
- `templates/` - HTML templates for all pages (login, register, index, results, etc.)
- `static/` - Static files like CSS, JS, and images
- `.venv/` - Python virtual environment (not committed)
- `uploads/` - Folder where uploaded resumes are temporarily stored
- Other modules for job fetching and resume matching logic

## Getting Started

### Prerequisites

- Python 3.10 or newer installed
- pip package manager
- Git

### Setup Instructions

Clone the repository, create and activate a virtual environment, install dependencies, and run the app with the following commands:

```bash
git clone https://github.com/SindhooraKH/resume-matcher.git
cd resume-matcher

python -m venv .venv
# On Windows
.\.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

python app.py
```