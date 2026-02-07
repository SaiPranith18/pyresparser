import os
import re
import pdfminer

from flask import Flask, render_template, request
from pdfminer.high_level import extract_text
from name import extract_name_from_resume
from skills import extract_skills_from_resume
from education import extract_education_from_resume

app = Flask(__name__)


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def home():
    name = None
    resume_text = None
    extracted_skills = None
    extracted_education = None
    selected_section = None
    section=None

    if request.method == "POST":
        file = request.files.get("resume")

        if file and file.filename:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)

            # Extract resume text ONCE
            text = extract_text(file_path)

            # Name extraction
            name = extract_name_from_resume(text)

            # Full resume text
            resume_text = text

            # Skills extraction
            skills_list = [
                "Python", "Data Analysis", "Machine Learning",
                "Communication", "Project Management",
                "Deep Learning", "SQL", "Tableau"
            ]
            extracted_skills = extract_skills_from_resume(text, skills_list)

            # Education extraction
            extracted_education = extract_education_from_resume(text)
            selected_section = None
            selected_section = request.form.get("section")
            section = request.form.get("section")
    
  

    return render_template(
    "index.html",
    name=name,
    resume_text=resume_text,
    extracted_skills=extracted_skills,
    extracted_education=extracted_education,
    selected_section=selected_section,
    section=section,
)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8000)








