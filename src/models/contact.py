import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CONTACT_HEADERS = [
    "contact", "contact details", "contact information", "personal details",
    "personal information", "contact me", "reach me", "communication details"
]


STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "about", "interests", "hobbies", "references", "declaration",
    "languages"
]


CONTACT_PATTERNS = [
    r'[\w\.-]+@[\w\.-]+\.\w+',  
    r'\+?[\d\s\-–()]{10,}',  
    r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  
    r'[\w\s,]+,\s*[\w\s]+,\s*[\w\s]+',  
]


def calculate_contact_confidence(contact_text, original_text):
    if not contact_text or not contact_text.strip():
        return 0.0
    
    lines = [l.strip() for l in contact_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.4
    
    
    contact_matches = 0
    for pattern in CONTACT_PATTERNS:
        contact_matches += len(re.findall(pattern, contact_text, re.IGNORECASE))
    
    pattern_factor = min(contact_matches / 2, 1.0) * 0.4
    
    
    length_factor = min(len(contact_text) / 100, 1.0) * 0.2
    
    confidence = item_factor + pattern_factor + length_factor
    
    if confidence > 0.3 and len(contact_text) > 20:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(min(confidence, 1.0), 2)


def is_contact_header(line_stripped, line_lower):
    for header in CONTACT_HEADERS:
        
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


def extract_contact_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    
    contact_lines = []
    capture = False
    header_found = False
    capture_count = 0

    
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = is_contact_header(line_stripped, line_lower)

        if is_header:
            capture = True
            header_found = True
            continue

        
        if capture and header_found:
            
            if should_stop_extraction(line_lower, capture_count):
                break
            
            
            if separator_pattern.match(line_stripped):
                continue
            
            
            if len(line_stripped) < 3:
                continue
            
            contact_lines.append(line_stripped)
            capture_count += 1

    
    cleaned = []
    seen = set()
    
    for line in contact_lines:
        normalized = line.lower().strip()
        
        
        if normalized in seen:
            continue
        if separator_pattern.match(line):
            continue
            
        cleaned.append(line)
        seen.add(normalized)

    contact_text = "\n".join(cleaned)
    
    confidence = calculate_contact_confidence(contact_text, text)
    
    logger.info(f"Contact extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return contact_text, confidence


if __name__ == "__main__":
    sample_text = ""
    print("Contact:", extract_contact_from_resume(sample_text))
