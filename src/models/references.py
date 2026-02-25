import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


REFERENCES_HEADERS = [
    "references", "referees", "recommendations", "professional references",
    "personal references", "character references", "reference available",
    "references furnished", "references upon request"
]


STOP_KEYWORDS = [
    "skills", "projects", "education", "experience", "certifications",
    "summary", "about", "technical skills", "work experience", "employment",
    "internships", "languages", "interests", "hobbies", "awards",
    "achievements", "declaration", "contact", "personal details",
    "publications", "volunteer", "training", "workshops", "signature"
]


REFERENCE_INDICATORS = [
    r'\b(reference|referee|recommend)\b',
    r'\b(contact|phone|email)\b',
    r'\b(mr\.|mrs\.|ms\.|dr\.)\b',
    r'\b(professor|manager|director|ceo|cto|vp|head)\b'
]


YEAR_PATTERN = re.compile(r'^(19|20)\d{2}(\s*[-–]\s*(19|20)\d{2})?$')


def calculate_references_confidence(references_text, original_text):
    if not references_text or not references_text.strip():
        return 0.0
    
    lines = [l.strip() for l in references_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.4
    
    
    ref_matches = 0
    for pattern in REFERENCE_INDICATORS:
        ref_matches += len(re.findall(pattern, references_text, re.IGNORECASE))
    
    pattern_factor = min(ref_matches / 3, 1.0) * 0.4
    
    
    length_factor = min(len(references_text) / 100, 1.0) * 0.2
    
    confidence = item_factor + pattern_factor + length_factor
    
    
    if confidence > 0.3 and len(references_text) > 30:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(min(confidence, 1.0), 2)


def is_reference_header(line_stripped, line_lower):
    for header in REFERENCES_HEADERS:
        
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


def extract_references_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    
    references_lines = []
    capture = False
    header_found = False
    capture_count = 0

    
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = is_reference_header(line_stripped, line_lower)

        if is_header:
            capture = True
            header_found = True
            continue

        
        if capture and header_found:
            
            if should_stop_extraction(line_lower, capture_count):
                break
            
            
            if separator_pattern.match(line_stripped):
                continue
            
            
            if YEAR_PATTERN.fullmatch(line_stripped):
                continue
            
            
            if len(line_stripped) < 3:
                continue
            
            references_lines.append(line_stripped)
            capture_count += 1

    
    cleaned = []
    seen = set()
    
    for line in references_lines:
        normalized = line.lower().strip()
        
        
        if normalized in seen:
            continue
        if separator_pattern.match(line):
            continue
            
        cleaned.append(line)
        seen.add(normalized)

    references_text = "\n".join(cleaned)
    
    
    if not references_text.strip():
        references_text, cleaned = extract_references_by_indicators(text)
    
    confidence = calculate_references_confidence(references_text, text)
    
    logger.info(f"References extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return references_text, confidence


def extract_references_by_indicators(text):
    lines = text.splitlines()
    references_lines = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        line_lower = line_stripped.lower()
        
        
        has_ref_indicator = False
        for pattern in REFERENCE_INDICATORS:
            if re.search(pattern, line_lower, re.IGNORECASE):
                has_ref_indicator = True
                break
        
        if has_ref_indicator:
            
            if i > 0:
                prev_line = lines[i-1].strip()
                if prev_line and len(prev_line) < 60 and prev_line not in references_lines:
                    
                    is_stop = False
                    for stop in STOP_KEYWORDS:
                        if stop in prev_line.lower():
                            is_stop = True
                            break
                    if not is_stop:
                        
                        if len(prev_line.split()) <= 5:
                            references_lines.append(prev_line)
            
            if line_stripped not in references_lines:
                references_lines.append(line_stripped)
    
    
    cleaned = []
    seen = set()
    for line in references_lines:
        normalized = line.lower().strip()
        if normalized not in seen:
            cleaned.append(line)
            seen.add(normalized)
    
    return "\n".join(cleaned), cleaned


if __name__ == "__main__":
    sample_text = ""
