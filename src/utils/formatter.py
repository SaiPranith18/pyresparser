import re

SECTION_KEYWORDS = [
    "about me","summary", "education", "projects", "experience",
    "technical skills", "soft skills", "certifications", "certificates",
    "declaration"
]

def  clean_fulltext_format(raw_text):
    lines = raw_text.splitlines()
    formatted = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            formatted.append("")
            continue

        is_heading = any(
            stripped.lower() == keyword
            for keyword in SECTION_KEYWORDS
        )

        if is_heading:
            formatted.append(stripped.upper())
            formatted.append("-" * 15)
            continue

        if re.fullmatch(r"-{4,}", stripped):
            continue

      
        if stripped.startswith(("•", "-", "*")):
            formatted.append(stripped)
            continue

        
        formatted.append(stripped)

    return "\n".join(formatted)
