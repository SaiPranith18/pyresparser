import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


STRENGTHS_HEADERS = [
    "strengths", "strength", "key strengths", "personal strengths", 
    "core strengths", "strong suits", "key competencies", "personal qualities",
    "soft skills", "key attributes", "positive traits", "professional strengths"
]


STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "about", "interests", "hobbies", "references", "declaration",
    "languages", "awards", "achievements"
]


STRENGTHS_KEYWORDS = [
    r'\b(leadership|communication|teamwork|problem.solving|critical.thinking)\b',
    r'\b(analytical|creative|innovative|adaptable|flexible)\b',
    r'\b(organized|detail.oriented|time.management|multitasking)\b',
    r'\b(confident|self.motivated|proactive|ambitious)\b'
]


def calculate_strengths_confidence(strengths_text, original_text):
    if not strengths_text or not strengths_text.strip():
        return 0.0
    
    lines = [l.strip() for l in strengths_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.4
    
    
    strength_matches = 0
    for pattern in STRENGTHS_KEYWORDS:
        strength_matches += len(re.findall(pattern, strengths_text, re.IGNORECASE))
    
    pattern_factor = min(strength_matches / 3, 1.0) * 0.4
    
    
    length_factor = min(len(strengths_text) / 100, 1.0) * 0.2
    
    confidence = item_factor + pattern_factor + length_factor
    
    if confidence > 0.3 and len(strengths_text) > 20:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(min(confidence, 1.0), 2)


def is_strengths_header(line_stripped, line_lower):
    for header in STRENGTHS_HEADERS:
        
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


def extract_strengths_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    
    strengths_lines = []
    capture = False
    header_found = False
    capture_count = 0

    
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = is_strengths_header(line_stripped, line_lower)

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
            
            strengths_lines.append(line_stripped)
            capture_count += 1

    
    cleaned = []
    seen = set()
    
    for line in strengths_lines:
        normalized = line.lower().strip()
        
        
        if normalized in seen:
            continue
        if separator_pattern.match(line):
            continue
            
        cleaned.append(line)
        seen.add(normalized)

    strengths_text = "\n".join(cleaned)
    
    confidence = calculate_strengths_confidence(strengths_text, text)
    
    logger.info(f"Strengths extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return strengths_text, confidence


if __name__ == "__main__":
    sample_text = ""
    print("Strengths:", extract_strengths_from_resume(sample_text))
