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
from projects import extract_projects_section
from skills import extract_skills_from_resume



app = Flask(__name__)


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def home():
    name = None
    resume_text = None
    skills_section = None
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
        
        skills_section  = extract_skills_from_resume(text)

            
        extracted_education = extract_education_from_resume(text)
        selected_section = request.form.get("section")
        section = request.form.get("section")

        certifications = extract_certifications_from_resume(text)
        projects = extract_projects_section(text)
            
    return render_template(
    "index.html",
    name=name,
    resume_text=resume_text,
    skills_section = skills_section,
    extracted_education=extracted_education,
    selected_section=selected_section,
    section=section,
    certifications=certifications,
    projects=projects,
    
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
        result = extract_skills_from_resume(text)

    elif section == "education":
        result = extract_education_from_resume(text)

    elif section == "name":
        result = extract_name_from_resume(text)

    elif section == "fulltext":
        result = clean_fulltext_format(text)
    
    elif section == "certifications":
        result = extract_certifications_from_resume(text)

    elif section == "projects":
        result = extract_projects_section(text )

    else:
        result = "Unknown category"

    return jsonify({"result": result})


@app.route("/api/parse", methods=["POST","GET","DELETE"])
def api_parse_resume():
    file = request.files.get("resume")
    section = request.form.get("section")

    if not file or not section:
        return jsonify({
            "status": "error",
            "message": "resume file and section are required"
        }), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        text = extract_text(file_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Failed to extract PDF text"
        }), 500

    try:
        if section == "skills":
           result = extract_skills_from_resume(text)

        elif section == "education":
            result = extract_education_from_resume(text)

        elif section == "projects":
            result = extract_projects_section(text)

        elif section == "certifications":
            result = extract_certifications_from_resume(text)

        elif section == "name":
            result = extract_name_from_resume(text)

        elif section == "fulltext":
            result = clean_fulltext_format(text)

        else:
            return jsonify({
                "status": "error",
                "message": "Invalid section type"
            }), 400

        if not result:
            return jsonify({
                "status": "error",
                "message": f"No data found for section: {section}"
            })

        return jsonify({
            "status": "success",
            "section": section,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)







