import pdfminer
import re

from pdfminer.high_level import extract_text

def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

def extract_skills_from_resume(text, skills_list):
    skills = []

   
    for skill in skills_list:
        pattern = r"\b{}\b".format(re.escape(skill))
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            skills.append(skill)

    return skills

if __name__ == '__main__':
    text = extract_text_from_pdf(r"C:\Users\SANKET\Downloads\Untitled-resume.pdf")

   
    skills_list = ['Python', 'Data Analysis', 'Machine Learning', 'Communication', 'Project Management', 'Deep Learning', 'SQL', 'Tableau']

    extracted_skills = extract_skills_from_resume(text, skills_list)

    if extracted_skills:
        print("Skills:", extracted_skills)
    else:
        print("No skills found")