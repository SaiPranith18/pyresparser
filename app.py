import os
import re
import pdfminer

from flask import Flask, render_template, request,jsonify
from pdfminer.high_level import extract_text
from name import extract_name_from_resume
from skills import extract_skills_from_resume
from education import extract_education_from_resume,extract_text_from_pdf

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




@app.route("/extract", methods=["POST"])
def extract_ajax():
    file = request.files.get("resume")
    section = request.form.get("section")

    if not file or not section:
        return jsonify({"result": "Invalid input"})

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    text = extract_text(file_path)

    if section == "skills":
        skills_list = [
            "Python", "Data Analysis", "Machine Learning",
            "Communication", "Project Management",
            "Deep Learning", "SQL", "Tableau"
        ]
        result = extract_skills_from_resume(text, skills_list)

    elif section == "education":
        result = extract_education_from_resume(text)

    elif section == "name":
        result = extract_name_from_resume(text)

    elif section == "fulltext":
        result = text

    else:
        result = "Unknown category"

    return jsonify({"result": result})


@app.route("/upload", methods=["POST"])
def upload():
    return jsonify({  "degree": "B.Tech",
        "university": "Test University",
        "cgpa": "3.4",
        "year": "3434"})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8000)













