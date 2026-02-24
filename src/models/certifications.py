import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CERTIFICATION_HEADERS = [
    "certifications", "certificates", "certification", "credentials",
    "licenses", "licenses & certifications", "certifications & licenses",
    "professional certifications", "certifications earned", "certifications obtained",
    "certified", "license", "certifications and licenses",
    "professional credentials", "certification details"
]


STOP_KEYWORDS = [
    "skills", "projects", "education", "experience", "summary",
    "about", "technical skills", "work experience", "employment",
    "internships", "achievements", "awards", "languages", "interests",
    "hobbies", "references", "declaration", "contact", "personal details"
]

CERTIFICATION_KEYWORDS = [
    r'\bcertified\b', r'\bcertificate\b', r'\bcertification\b',
    r'\baws\b', r'\bazure\b', r'\bgcp\b', r'\bgoogle cloud\b',
    r'\bpmp\b', r'\bscrum\b', r'\bagile\b', r'\bpmi\b', r'\bitil\b',
    r'\bccna\b', r'\bccnp\b', r'\bmcse\b', r'\bmcsa\b',
    r'\biso\b', r'\bceh\b', r'\bcissp\b', r'\bcisa\b', r'\bcomptia\b',
    r'\bsalesforce\b', r'\boracle\b', r'\bjava\b', r'\bpython\b',
    r'\bmicrosoft certified\b', r'\bgoogle certified\b',
    r'\bcisco\b', r'\bvmware\b', r'\bredhat\b',
    r'\bprofessional\b', r'\bspecialist\b', r'\bexpert\b'
]


def calculate_certifications_confidence(cert_text, original_text):
    if not cert_text or not cert_text.strip():
        return 0.0
    
    lines = [l.strip() for l in cert_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 5, 1.0) * 0.4  
    
    
    cert_patterns = [
        r'\b(certified|certificate|certification)\b',
        r'\b(aws|azure|gcp|google|amazon|microsoft)\b',
        r'\b(pmp|scrum|agile|pmi|itil|ccna|ccnp|mcse|mcsa)\b',
        r'\b(iso|ceh|cissp|cisa|comptia)\b',
    ]
    
    cert_matches = 0
    for pattern in cert_patterns:
        cert_matches += len(re.findall(pattern, cert_text, re.IGNORECASE))
    
    cert_factor = min(cert_matches / 5, 1.0) * 0.4  
    
    
    length_factor = min(len(cert_text) / 200, 1.0) * 0.2
    
    confidence = item_factor + cert_factor + length_factor
    return round(confidence, 2)


def is_certification_header(line_stripped, line_lower):
    for header in CERTIFICATION_HEADERS:
        
        if line_lower == header:
            return True
        
        
        if len(line_stripped) < 50:
            if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—]+', line_lower):
                return True
            
            
            if header in line_lower and len(line_stripped) < 40:
                header_pos = line_lower.find(header)
                if header_pos == 0 or (header_pos > 0 and line_stripped[header_pos-1] in ' -:'):
                    return True
    
    return False


def should_stop_extraction(line_lower, capture_count):
    for stop in STOP_KEYWORDS:
        
        if line_lower == stop or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
            return True
        
        
        if stop in line_lower and len(line_lower) < 30 and capture_count > 0:
            return True
    
    return False


def extract_certifications_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    
    certifications_lines = []
    capture = False
    header_found = False
    capture_count = 0

    
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    year_pattern = re.compile(r'^(19|20)\d{2}(\s*[-–]\s*(19|20)\d{2})?$')

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = is_certification_header(line_stripped, line_lower)

        if is_header:
            capture = True
            header_found = True
            continue

        
        if capture and header_found:
            
            if should_stop_extraction(line_lower, capture_count):
                break
            
            
            if separator_pattern.match(line_stripped):
                continue
            if year_pattern.fullmatch(line_stripped):
                continue
            
            
            if len(line_stripped) < 3:
                continue
            
            certifications_lines.append(line_stripped)
            capture_count += 1

    
    
    cleaned = []
    seen = set()
    
    for line in certifications_lines:
        
        normalized = line.lower().strip()
        
        
        if normalized in seen:
            continue
        if separator_pattern.match(line):
            continue
            
        cleaned.append(line)
        seen.add(normalized)

    cert_text = "\n".join(cleaned)
    
    
    
    if not cert_text.strip():
        cert_text, cleaned = extract_certifications_by_keywords(text)
    
    
    confidence = calculate_certifications_confidence(cert_text, text)
    
    logger.info(f"Certifications extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return cert_text, confidence


def extract_certifications_by_keywords(text):
    lines = text.splitlines()
    certifications_lines = []
    
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        line_lower = line_stripped.lower()
        
        
        has_cert_keyword = False
        for pattern in CERTIFICATION_KEYWORDS:
            if re.search(pattern, line_lower, re.IGNORECASE):
                has_cert_keyword = True
                break
        
        if has_cert_keyword:
            
            if i > 0:
                prev_line = lines[i-1].strip()
                if prev_line and len(prev_line) < 50 and prev_line not in certifications_lines:
                    
                    is_stop = False
                    for stop in STOP_KEYWORDS:
                        if stop in prev_line.lower():
                            is_stop = True
                            break
                    if not is_stop:
                        certifications_lines.append(prev_line)
            
            if line_stripped not in certifications_lines:
                certifications_lines.append(line_stripped)
    
    
    cleaned = []
    seen = set()
    for line in certifications_lines:
        normalized = line.lower().strip()
        if normalized not in seen:
            cleaned.append(line)
            seen.add(normalized)
    
    return "\n".join(cleaned), cleaned
