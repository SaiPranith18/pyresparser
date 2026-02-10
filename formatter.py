import re

SECTION_KEYWORDS = [
    "about","summary", "education", "projects", "experience",
    "technical skills", "soft skills", "certifications", "certificates",
    "declaration", "skills"
]

def clean_fulltext_format(raw_text):
    lines = raw_text.splitlines()
    formatted = []
    paragraph_buffer = []

    def flush_paragraph():
        if paragraph_buffer:
            formatted.append(" ".join(paragraph_buffer))
            paragraph_buffer.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            formatted.append("")
            continue

        
        is_heading = any(stripped.lower() == keyword for keyword in SECTION_KEYWORDS)

        if is_heading:
            flush_paragraph()
            formatted.append(stripped.upper())
            formatted.append("-" * 15)
            continue

        if re.fullmatch(r"-{4,}", stripped):
            continue

        if stripped.startswith(("•", "-", "*")):
            flush_paragraph()
            formatted.append(stripped)
            continue

       
        paragraph_buffer.append(stripped)

    flush_paragraph()

    return "\n".join(formatted)
