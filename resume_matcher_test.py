import pdfplumber
from sentence_transformers import SentenceTransformer, util
from keybert import KeyBERT
import re
import nltk
nltk.download('punkt')

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def clean_text(text):
    # Replace multiple spaces/newlines with single space
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters except basic punctuation
    text = re.sub(r'[^a-zA-Z0-9,. ]', '', text)
    # Lowercase
    text = text.lower()
    return text.strip()

def main():
    resume_path = "sindhoora.pdf"
    job_description_path = "job_description.txt"

    # Extract resume text
    if resume_path.lower().endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume_path)
    else:
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
    resume_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', resume_text)  # split camelCase stuck words
    resume_text = re.sub(r'[^a-zA-Z0-9\s]', ' ', resume_text)  # remove special characters but keep words and numbers
    resume_text = re.sub(r'\s+', ' ', resume_text).strip()  # normalize whitespace
    # Load job description
    with open(job_description_path, "r", encoding="utf-8") as f:
        job_text = f.read()

    # Clean texts
    resume_text = clean_text(resume_text)
    job_text = clean_text(job_text)

    # Initialize models
    model = SentenceTransformer('all-MiniLM-L6-v2')
    kw_model = KeyBERT(model)

    # Extract keywords (1-2 grams) from both texts
    resume_keywords = kw_model.extract_keywords(resume_text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=20)
    job_keywords = kw_model.extract_keywords(job_text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=20)

    print("Keywords extracted from resume:")
    for kw, score in resume_keywords:
        print(f"- {kw} (score: {score:.4f})")

    print("\nKeywords extracted from job description:")
    for kw, score in job_keywords:
        print(f"- {kw} (score: {score:.4f})")

    # Encode keywords (just the phrases) for similarity
    resume_kw_phrases = [kw[0] for kw in resume_keywords]
    job_kw_phrases = [kw[0] for kw in job_keywords]

    embeddings_resume_kw = model.encode(resume_kw_phrases, convert_to_tensor=True)
    embeddings_job_kw = model.encode(job_kw_phrases, convert_to_tensor=True)

    # Compute cosine similarity matrix between resume keywords and job keywords
    cosine_scores = util.cos_sim(embeddings_resume_kw, embeddings_job_kw)

    # To get overall similarity, average max similarity scores for each resume keyword
    max_sim_scores = cosine_scores.max(dim=1).values
    average_similarity = max_sim_scores.mean().item()

    print(f"\nSemantic similarity based on keywords: {average_similarity:.4f}")

    # Also compute full text similarity as before for comparison
    embeddings_resume = model.encode(resume_text, convert_to_tensor=True)
    embeddings_job = model.encode(job_text, convert_to_tensor=True)
    full_text_similarity = util.cos_sim(embeddings_resume, embeddings_job).item()

    print(f"Semantic similarity based on full text: {full_text_similarity:.4f}")

if __name__ == "__main__":
    main()
