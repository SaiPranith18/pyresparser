import re
from pdfminer.high_level import extract_text


def extract_skills_from_resume(text):
   
    lines = text.splitlines()
    skills_lines = []
    capture = False

    stop_keywords = [
        "education", "projects", "experience", "certifications", 
        "summary", "about", "technical skills"
    ]

    for line in lines:
        line_lower = line.strip().lower()

        
        if re.search(r"skills|technical skills|soft skills", line_lower):
            capture = True
            continue

      
        if capture and any(k in line_lower for k in stop_keywords):
            break

        if capture:
           
            if line.strip() and not re.fullmatch(r"-{4,}", line.strip()):
                skills_lines.append(line.strip())

    return "\n".join(skills_lines)



if __name__ == "__main__":
    pdf_path = "sample_resume.pdf"
    text = extract_text(pdf_path)

    skills_section = extract_skills_from_resume(text)

    print("=== Skills Section ===")
    print(skills_section if skills_section else "No skills section found")
