import re
from pdfminer.high_level import extract_text



def extract_skills_from_resume(text):
   
    lines = text.splitlines()
    skills_lines = []
    capture = False

    stop_keywords = [
        "education", "projects", "experience", "certifications",
        "summary", "about", "technical skills", "strength", "strengths",
        "personal details", "extra-curricular activities", "languages",
        "interests", "hobbies", "references", "declaration", "objective",
        "career objective", "introduction", "contact", "achievements",
        "awards", "publications", "volunteer experience", "internships"
    ]

    for line in lines:
        line_lower = line.strip().lower()

        
        if line.strip().lower() in ["skills","technical skills","key skills","core skills","skill set",
                     "skills summary","technical expertise","technical competencies","technical proficiencies",
                    "technical knowledge","tools & technologies","tools and technologies","technologies",
                    "software skills","programming skills","technology stack","tech stack",
                    "core competencies","competencies","professional skills","areas of expertise",
                    "strengths","skills & abilities","skills and abilities","computer skills","it skills"
]:
            capture = True
            continue

      
        if capture and line_lower in stop_keywords:
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
  
