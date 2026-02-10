import re

PROJECT_HEADERS = {
    "projects",
    "project",
    "academic projects",
    "personal projects"
}

STOP_HEADERS = {
    "education",
    "experience",
    "technical skills",
    "soft skills",
    "skills",
    "certifications",
    "certificates",
    "languages",
    "declaration",
    "summary",
    "about"
}

YEAR_ONLY_PATTERN = re.compile(r"^(19|20)\d{2}(\s*[-–]\s*(19|20)\d{2})?$")

def extract_projects_section(text):
    lines = text.splitlines()

    projects = []
    in_projects = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        lower = stripped.lower()

        if lower in PROJECT_HEADERS:
            in_projects = True
            continue

        if in_projects and lower in STOP_HEADERS:
            break

        if in_projects:
            
            if re.fullmatch(r"-{3,}", stripped):
                continue

            if YEAR_ONLY_PATTERN.fullmatch(stripped):
                continue

            projects.append(stripped)

    return "\n".join(projects)
