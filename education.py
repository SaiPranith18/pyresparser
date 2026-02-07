import re
from pdfminer.high_level import extract_text

def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

def extract_education_from_resume(text):
    education_patterns = [
        r"B\.Tech", r"B\.E", r"B\.Sc", r"BSc", r"B\.A", 
        r"M\.Tech", r"M\.E", r"M\.Sc", r"MSc", r"MBA",
        r"Ph\.D", r"Doctor of Philosophy",
        r"Bachelor's", r"Master of.*"
    ]

    education = []
    for pattern in education_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        education.extend(matches)

    # return list(set(education))  


# def education_block(edu_lines):

    degree = ""
    university = ""
    cgpa = ""
    year = ""

    # Degree patterns
    degree_patterns = r"(B\.Tech|B\.E|B\.Sc|BSc|B\.A|BA|M\.Tech|M\.E|M\.Sc|MSc|MBA|Ph\.D|Bachelor's|Master of.*)"

    lines = text.split("\n")

    for line in lines:
        line_lower = line.lower()

        # Detect degree
        if re.search(degree_patterns, line, re.IGNORECASE):
            degree = line.strip()

        # Detect university / college
        if "university" in line_lower or "college" in line_lower or "institute" in line_lower:
            university = line.strip()

        # Detect CGPA or percentage
        if re.search(r"(cgpa|gpa|%)", line_lower):
            cgpa = line.strip()

        # Detect year
        match = re.search(r"(20\d{2})", line)
        if match:
            year = match.group()

    return {
        "degree": degree,
        "university": university,
        "cgpa": cgpa,
        "year": year
    }

      
    
     
    


