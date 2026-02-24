import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PROJECT_HEADERS = [
    "projects", "project", "academic projects", "personal projects",
    "project experience", "project details", "key projects", "project work",
    "major projects", "minor projects"
]


STOP_KEYWORDS = [
    "education", "experience", "technical skills", "soft skills", "skills",
    "certifications", "certificates", "languages", "declaration", "summary",
    "about", "contact", "references", "achievements", "awards"
]

YEAR_ONLY_PATTERN = re.compile(r"^(19|20)\d{2}(\s*[-–]\s*(19|20)\d{2})?$")


def calculate_projects_confidence(project_text, original_text):
    if not project_text or not project_text.strip():
        return 0.0
    
    lines = [l.strip() for l in project_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 5, 1.0) * 0.4  
    
    
    
    project_patterns = [
        r'\b(developed|built|created|designed|implemented|led)\b',
        r'\b(python|java|javascript|react|angular|node|django|flask)\b',
        r'\b(machine learning|data science|api|database|web)\b',
        r'\b(github|gitlab|heroku|aws|azure)\b',
        r'\b(project|team|application|system)\b',
        r'\b(analysis|design|development|testing)\b',
    ]
    
    project_matches = 0
    for pattern in project_patterns:
        project_matches += len(re.findall(pattern, project_text, re.IGNORECASE))
    
    project_factor = min(project_matches / 5, 1.0) * 0.4  
    
    
    length_factor = min(len(project_text) / 200, 1.0) * 0.2
    
    confidence = item_factor + project_factor + length_factor
    
    
    if confidence > 0.3 and len(project_text) > 20:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(min(confidence, 1.0), 2)


def extract_projects_section(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()

    projects = []
    in_projects = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        lower = stripped.lower()

        
        is_header = False
        for header in PROJECT_HEADERS:
            
            if lower == header:
                is_header = True
                break
            
            if len(stripped) < 60:
                
                if lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—:.]+', lower):
                    is_header = True
                    break
                
                if header in lower and len(stripped) < 50:
                    header_pos = lower.find(header)
                    
                    if header_pos == 0:
                        is_header = True
                        break
                    
                    if header_pos > 0:
                        prefix = lower[:header_pos].strip()
                        remainder = lower[header_pos + len(header):].strip()
                        if prefix and len(prefix) < 20 and len(remainder) < 5:
                            is_header = True
                            break

        if is_header:
            in_projects = True
            continue

        
        if in_projects:
            should_stop = False
            for stop in STOP_KEYWORDS:
                
                if lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', lower):
                    should_stop = True
                    break
                
                if lower == stop:
                    should_stop = True
                    break
            
            if should_stop:
                break

        if in_projects:
            
            if re.fullmatch(r"-{3,}", stripped):
                continue

            
            if YEAR_ONLY_PATTERN.fullmatch(stripped):
                continue

            projects.append(stripped)

    project_text = "\n".join(projects)
    
    
    confidence = calculate_projects_confidence(project_text, text)
    
    logger.info(f"Projects extraction completed. Entries found: {len(projects)}, Confidence: {confidence}")
    
    return project_text, confidence
