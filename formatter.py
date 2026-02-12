import re

SECTION_KEYWORDS = [
    "about","summary", "education", "projects", "experience",
    "technical skills", "soft skills", "certifications", "certificates",
    "declaration", "skills", "introduction", "contact", "personal information",
    "professional experience", "work experience", "languages", "interests", "hobbies",
    "career objective", "objective", "education qualification", "strength", "strengths",
    "extra-curricular activities", "personal details", "projets", "achievements",
    "awards", "publications", "references", "volunteer experience", "internships"
]

SECTION_ORDER = [
    "introduction", "summary", "about", "career objective", "objective",
    "education", "education qualification",
    "projects", "projets",
    "experience", "professional experience", "work experience",
    "skills", "technical skills", "soft skills",
    "certifications", "certificates",
    "achievements", "awards", "publications",
    "strength", "strengths",
    "languages",
    "extra-curricular activities",
    "personal details", "personal information", "contact",
    "interests", "hobbies",
    "references",
    "volunteer experience", "internships",
    "declaration"
]

def clean_fulltext_format(raw_text):
    lines = raw_text.splitlines()
    sections = {}
    current_section = "header"
    sections["header"] = []
    paragraph_buffer = []

    def flush_paragraph():
        if paragraph_buffer:
            sections[current_section].append(" ".join(paragraph_buffer))
            paragraph_buffer.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            sections[current_section].append("")
            continue

        is_heading = any(keyword in stripped.lower() for keyword in SECTION_KEYWORDS)

        if is_heading:
            flush_paragraph()
            clean_heading = re.sub(r'[^a-zA-Z\s]', '', stripped).strip().lower()
            
            for sec in SECTION_ORDER:
                if sec in clean_heading or clean_heading in sec:
                    current_section = sec
                    break
            else:
                current_section = clean_heading 
            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append(stripped.upper())
            sections[current_section].append("-" * 15)
            continue

        if stripped.startswith(("•", "-", "*")):
            flush_paragraph()
            sections[current_section].append(stripped)
            continue

        paragraph_buffer.append(stripped)

    flush_paragraph()

    formatted = []
    for sec in SECTION_ORDER:
        if sec in sections and sections[sec]:
            formatted.extend(sections[sec])
            formatted.append("") 

    if "header" in sections:
        formatted = sections["header"] + [""] + formatted

    for sec, content in sections.items():
        if sec not in SECTION_ORDER and sec != "header" and content:
            formatted.extend(content)
            formatted.append("")

    return "\n".join(formatted).strip()
