import spacy
import fitz
import re
import pdfminer


from pdfminer.high_level import extract_text

nlp = spacy.load("en_core_web_sm")

SECTION_KEYWORDS = {
    "skills": ["skills", "technical skills", "technologies"],
    "education": ["education", "academic", "qualification"],
    "projects": ["projects", "project experience"],
    "experience": ["experience", "work experience", "internship"],
    "certifications": ["certifications", "certificates"]
}

def extract_section_nlp(text, section):
    keywords = SECTION_KEYWORDS.get(section.lower(), [])
    lines = text.splitlines()

    capture = False
    result = []

    for line in lines:
        lower = line.lower()

        if any(k in lower for k in keywords):
            capture = True
            continue

        if capture and any(
            any(k in lower for k in v)
            for v in SECTION_KEYWORDS.values()
        ):
            break

        if capture:
            result.append(line)

    return "\n".join(result).strip()


def extract_name_nlp(text):
    lines = text.splitlines()[:5]  # first 5 lines only
    joined = " ".join(lines)

    doc = nlp(joined)

    candidates = []

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            words = ent.text.split()
            if 2 <= len(words) <= 3:
                candidates.append(ent.text)
    return max(candidates, key=len) if candidates else None



def extract_education(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""

    for page in doc:
        full_text += page.get_text()
    text = full_text.lower()

    edu_section_keywords = [
        "education",
        "academic qualifications",
        "educational background",
        "academics"
    ]

    
    lines = text.split("\n")

    education_block = []
    capture = False

    for line in lines:
        line = line.strip()
        if any(k in line for k in edu_section_keywords):
            capture = True
            continue

        if capture and re.match(r"(skills|experience|projects|certifications|summary|profile)", line):
            break

        if capture and len(line) > 2:
            education_block.append(line)

    return education_block




def education_block(text):
    __doc__ = fitz.open(text)
     
   















