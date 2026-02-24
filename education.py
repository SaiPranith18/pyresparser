import re

def extract_education_from_resume(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    education_lines = []
    capture = False

    stop_keywords = [
        "skills",
        "projects",
        "certifications",
        "experience",
        "summary",
        "about",
        "technical skills"
    ]

    for line in lines:
        lower = line.lower()

        # if "education" in lower and len(line.strip()) < 50:
        #     capture = True
        #     continue
        if line.strip().lower() in ['education','education qualification','educational qualifications','academic qualifications',
                                    'education & qualifications','education details','education background','academic background','educational profile','educational summary',
                                     'academic credentials' ]:
            capture = True
            continue

        if capture and any(k in lower for k in stop_keywords):
            break

        if capture:
            education_lines.append(line)
    cleaned = []
    for line in education_lines:
        if len(line) > 3 and line not in cleaned:
            cleaned.append(line)

    return "\n".join(cleaned)
