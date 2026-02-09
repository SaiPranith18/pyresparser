import re

SECTION_KEYWORDS = [
    "education", "experience", "projects", "certifications", "certificates","about", 
    "technical skills", "soft skills", "declaration", "summary"
]

def clean_fulltext_format(raw_text):
   
    lines = raw_text.splitlines()
    formatted_lines = []
    year_pattern = re.compile(r"\b(\d{4}\s*[-–]\s*\d{4})\b")

    for i, line in enumerate(lines):
        stripped = line.strip()

       
        if not stripped or stripped.startswith("-") or stripped.startswith("_"):
            continue

  
        is_heading = False
        for keyword in SECTION_KEYWORDS:
            if keyword.lower() in stripped.lower():
                is_heading = True
                break

        if is_heading:
            formatted_lines.append(stripped.upper())
            formatted_lines.append("-"*15)
            continue

        
        if stripped.startswith("•"):
            formatted_lines.append("  " + stripped)
            continue

   
        year_match = year_pattern.search(stripped)
        if year_match:
            year = year_match.group(0)
           
            for j in range(len(formatted_lines)-1, -1, -1):
                if formatted_lines[j].strip() != "":
                    prev = formatted_lines[j]
                    space = max(2, 80 - len(prev) - len(year))
                    formatted_lines[j] = f"{prev}{' '*space}{year}"
                    break
            continue

        
        formatted_lines.append(stripped)

    return "\n".join(formatted_lines)
