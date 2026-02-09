import os
import re
import pdfminer

from flask import Flask, render_template, request,jsonify
from pdfminer.high_level import extract_text
from name import extract_name_from_resume
from skills import extract_skills_from_resume
from education import extract_education_from_resume
from certifications import extract_certifications_from_resume
from formatter import clean_fulltext_format



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
    certifications =None
    projects=None

    if request.method == "POST":
        file = request.files.get("resume")

        if file and file.filename:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
 
            text = extract_text(file_path)
            name = extract_name_from_resume(text)
            resume_text = clean_fulltext_format(text)
            skills_list = [
                "Python", "Data Analysis", "Machine Learning",
                "Communication", "Project Management",
                "Deep Learning", "MySQL", "Tableau"
            ]
            extracted_skills = extract_skills_from_resume(text, skills_list)

            
            extracted_education = extract_education_from_resume(text)
            selected_section = request.form.get("section")
            section = request.form.get("section")

            certifications = extract_certifications_from_resume(text)
            
    return render_template(
    "index.html",
    name=name,
    resume_text=resume_text,
    extracted_skills=extracted_skills,
    extracted_education=extracted_education,
    selected_section=selected_section,
    section=section,
    certifications=certifications,
    projects=projects
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
            "Deep Learning", "MySQL", "Tableau"
        ]
        result = extract_skills_from_resume(text, skills_list)

    elif section == "education":
        result = extract_education_from_resume(text)

    elif section == "name":
        result = extract_name_from_resume(text)

    elif section == "fulltext":
        result = clean_fulltext_format(text)
    
    elif section == "certifications":
        result = extract_certifications_from_resume(text)

    else:
        result = "Unknown category"

    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)







