from flask import Flask, request, jsonify
import os
import pdfplumber
import spacy
import re
import docx
import pytesseract  # type: ignore
from PIL import Image  # type: ignore
import logging

app = Flask(__name__)

# Load spaCy model for natural language processing
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Provide feedback if model loading fails
    logging.error("The spaCy model 'en_core_web_sm' is not installed. Install it using 'python -m spacy download en_core_web_sm'.")

# Set maximum file size to 50MB to allow for multiple resumes
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# Set up logging for debugging and performance tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Cache for frequently searched skills
cached_skills = set(["python", "java", "sql", "machine learning", "data analysis", "html", "css", "javascript"])

# Function to clean the extracted text by removing special characters
def clean_text(text):
    text = re.sub(r"[^\w\s]", "", text)  # Remove special characters
    text = re.sub(r"\s+", " ", text)  # Replace multiple spaces with a single space
    return text.strip()

# Function to extract the candidate's name from the resume
def extract_name(text):
    lines = text.split("\n")[:5]  # First 5 lines
    name_regex = re.compile(r"([A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+)")
    
    for line in lines:
        match = name_regex.search(line)
        if match:
            return match.group(0)
    
    return "Unknown"

# Function to extract text from PDF resumes
def extract_text_from_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ''.join([page.extract_text() or '' for page in pdf.pages])
        return clean_text(text) if text else extract_text_from_pdf_with_ocr(file_path)
    except Exception as e:
        logging.error(f"Error extracting PDF text: {e}")
        return extract_text_from_pdf_with_ocr(file_path)

# Function for OCR fallback
def extract_text_from_pdf_with_ocr(file_path):
    logging.info("Performing OCR fallback...")
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ''.join([pytesseract.image_to_string(Image.fromarray(page.to_image().original)) for page in pdf.pages])
        return clean_text(text)
    except Exception as e:
        logging.error(f"Error performing OCR on PDF: {e}")
        return ""

# Function to extract text from DOCX resumes
def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return clean_text('\n'.join([para.text for para in doc.paragraphs]))
    except Exception as e:
        logging.error(f"Error extracting DOCX text: {e}")
        return ""

# Function to extract skills
def extract_skills(text, required_skills):
    doc = nlp(text.lower())
    tokens = set([token.text for token in doc if not token.is_stop])
    extracted_skills = [skill for skill in required_skills if skill in tokens or skill in cached_skills]
    return extracted_skills

# Rank resumes
def rank_resume(extracted_skills, required_skills):
    matched_skills = set(required_skills).intersection(set(extracted_skills))
    match_score = len(matched_skills)
    match_percentage = (match_score / len(required_skills)) * 100 if required_skills else 0
    return list(matched_skills), match_score, match_percentage

# Route for multiple file uploads and ranking
@app.route("/upload", methods=["POST"])
def upload_resumes():
    try:
        required_skills = request.form["skills"].lower().split(",")
        required_skills = [skill.strip() for skill in required_skills]

        if "resumes" not in request.files:
            return jsonify({"error": "No resumes uploaded"}), 400

        resumes = request.files.getlist("resumes")
        if not os.path.exists("uploads"):
            os.mkdir("uploads")

        results = []

        for resume in resumes:
            file_path = os.path.join("uploads", resume.filename)
            resume.save(file_path)

            # Extract text based on file type
            if resume.filename.endswith(".pdf"):
                resume_text = extract_text_from_pdf(file_path)
            elif resume.filename.endswith(".docx"):
                resume_text = extract_text_from_docx(file_path)
            else:
                return jsonify({"error": f"Unsupported file type: {resume.filename}"}), 400
            
            # Extract name and skills
            name = extract_name(resume_text)
            extracted_skills = extract_skills(resume_text, required_skills)
            matched_skills, match_score, match_percentage = rank_resume(extracted_skills, required_skills)

            # Append results
            results.append({
                "name": name,
                "resume": resume.filename,
                "matched_skills": matched_skills,
                "match_score": match_score,
                "match_percentage": match_percentage
            })

        # Sort results by match_percentage
        sorted_results = sorted(results, key=lambda x: x["match_percentage"], reverse=True)
        return jsonify({"ranked_resumes": sorted_results})

    except Exception as e:
        logging.error(f"Error in resume processing: {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
