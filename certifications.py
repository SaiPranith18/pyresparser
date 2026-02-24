import re

def extract_certifications_from_resume(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    certifications_lines = []
    capture = False

    
    stop_keywords = [
        "skills",
        "projects",
        "education",
        "experience",
        "summary",
        "about",
        "technical skills"
    ]

    for line in lines:
        Upper = line.lower()

      
        # if re.fullmatch(r"certifications", Upper):
        #     capture = True
        #     continue
        if line.strip().lower() in["certifications","certification","certificates","professional certifications",
                        "technical certifications","certifications & training","training & certifications","licenses & certifications",
                        "credentials","professional credentials","certifications & courses","courses & certifications",
                        "online certifications","professional development","technical training","workshops & certifications",
                        "industry certifications"
]:
            capture = True
            continue

      
        if capture and any(k in Upper for k in stop_keywords):
            break

        if capture:
            certifications_lines.append(line)
            
    cleaned = []
    for line in certifications_lines:
        if len(line) > 3 and line not in cleaned:
            cleaned.append(line)

    return "\n".join(cleaned)
