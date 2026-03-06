import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PHONE_HEADERS = [
    "phone", "phone number", "contact number", "mobile", "mobile number",
    "telephone", "tel", "cell", "cell number", "phone no", "phone no.",
    "contact phone", "phone:", "mobile:", "tel:", "ph:", "ph no"
]


STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "about", "interests", "hobbies", "references", "declaration",
    "languages", "awards", "achievements", "publications", "volunteer", "training"
]


PHONE_PATTERNS = [
    r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',  
    r'\+?91[-.\s]?[6-9][0-9]{9}',  
    r'\+?44[-.\s]?[0-9]{4}[-.\s]?[0-9]{6}',  
    r'\+?61[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{4}[-.\s]?[0-9]{4}',  
    r'\+?49[-.\s]?[0-9]{2,5}[-.\s]?[0-9]{3,8}',  
    r'\+?33[-.\s]?[0-9][-.\s]?[0-9]{2}[-.\s]?[0-9]{2}[-.\s]?[0-9]{2}',  
    r'\+?81[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}',  
    r'\+?86[-.\s]?[1-9][0-9]{10}',  
    r'\b[0-9]{10}\b',  
    r'\b[0-9]{3}[-.\s][0-9]{3}[-.\s][0-9]{4}\b',  
    r'\b\([0-9]{3}\)\s*[0-9]{3}[-.\s][0-9]{4}\b',  
]


def calculate_phone_confidence(phone_text, original_text):
    if not phone_text or not phone_text.strip():
        return 0.0
    
    phone_numbers = []
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, phone_text)
        phone_numbers.extend(matches)
    
    if not phone_numbers:
        return 0.0
    
    
    valid_count = len(set(phone_numbers))
    item_factor = min(valid_count / 2, 1.0) * 0.6
    
    
    length_factor = min(len(phone_text) / 50, 1.0) * 0.4
    
    confidence = item_factor + length_factor
    
    if confidence > 0.3 and len(phone_text) > 10:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(min(confidence, 1.0), 2)


def is_phone_header(line_stripped, line_lower):
    for header in PHONE_HEADERS:
        
        if line_lower == header:
            return True
        
        
        if len(line_stripped) < 50:
            if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—]+', line_lower):
                return True
    
    return False


def should_stop_extraction(line_lower, capture_count):
    for stop in STOP_KEYWORDS:
        
        if line_lower == stop or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
            return True
        
        
        if stop in line_lower and len(line_lower) < 30 and capture_count > 0:
            return True
    
    return False


def extract_phone_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    
    phone_lines = []
    capture = False
    header_found = False
    capture_count = 0

    
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = is_phone_header(line_stripped, line_lower)

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
            
            phone_lines.append(line_stripped)
            capture_count += 1

    
    cleaned = []
    seen = set()
    
    for line in phone_lines:
        normalized = line.lower().strip()
        
        
        if normalized in seen:
            continue
        if separator_pattern.match(line):
            continue
            
        cleaned.append(line)
        seen.add(normalized)

    phone_text = "\n".join(cleaned)
    
    confidence = calculate_phone_confidence(phone_text, text)
    
    logger.info(f"Phone extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return phone_text, confidence


def extract_all_phones_from_text(text):
    if not text:
        return [], 0.0
    
    found_phones = []
    
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            if match not in found_phones:
                found_phones.append(match)
    
    unique_phones = []
    seen = set()
    for phone in found_phones:
        phone_clean = re.sub(r'[^\d+]', '', phone)
        if phone_clean not in seen:
            unique_phones.append(phone)
            seen.add(phone_clean)
    
    phone_text = "\n".join(unique_phones)
    confidence = calculate_phone_confidence(phone_text, text)
    
    logger.info(f"Extracted {len(unique_phones)} phone numbers from text. Confidence: {confidence}")
    
    return unique_phones, confidence


def extract_phone_from_line(line):
    for pattern in PHONE_PATTERNS:
        match = re.search(pattern, line)
        if match:
            return match.group(0)
    return None


if __name__ == "__main__":
    sample_text = ""
    print("Phone:", extract_phone_from_resume(sample_text))
    print("All Phones:", extract_all_phones_from_text(sample_text))
