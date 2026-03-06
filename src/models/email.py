import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


EMAIL_HEADERS = [
    "email", "email address", "email id", "e-mail", "mail", "electronic mail",
    "contact email", "personal email", "official email", "email id:"
]


STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "about", "interests", "hobbies", "references", "declaration",
    "languages", "awards", "achievements", "publications", "volunteer", "training"
]


EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    re.IGNORECASE
)


def calculate_email_confidence(email_text, original_text):
    if not email_text or not email_text.strip():
        return 0.0
    
    emails = EMAIL_PATTERN.findall(email_text)
    
    if not emails:
        return 0.0
    
    
    valid_count = len(set(emails))
    item_factor = min(valid_count / 2, 1.0) * 0.6
    
    
    length_factor = min(len(email_text) / 50, 1.0) * 0.4
    
    confidence = item_factor + length_factor
    
    if confidence > 0.3 and len(email_text) > 10:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(min(confidence, 1.0), 2)


def is_email_header(line_stripped, line_lower):
    for header in EMAIL_HEADERS:
        
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


def extract_email_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    
    email_lines = []
    capture = False
    header_found = False
    capture_count = 0

    
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = is_email_header(line_stripped, line_lower)

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
            
            email_lines.append(line_stripped)
            capture_count += 1

    
    cleaned = []
    seen = set()
    
    for line in email_lines:
        normalized = line.lower().strip()
        
        
        if normalized in seen:
            continue
        if separator_pattern.match(line):
            continue
            
        cleaned.append(line)
        seen.add(normalized)

    email_text = "\n".join(cleaned)
    
    confidence = calculate_email_confidence(email_text, text)
    
    logger.info(f"Email extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return email_text, confidence


def extract_all_emails_from_text(text):
    if not text:
        return [], 0.0
    
    emails = EMAIL_PATTERN.findall(text)
    
    unique_emails = []
    seen = set()
    for email in emails:
        email_lower = email.lower()
        if email_lower not in seen:
            unique_emails.append(email)
            seen.add(email_lower)
    
    email_text = "\n".join(unique_emails)
    confidence = calculate_email_confidence(email_text, text)
    
    logger.info(f"Extracted {len(unique_emails)} emails from text. Confidence: {confidence}")
    
    return unique_emails, confidence


def extract_email_from_line(line):
    match = EMAIL_PATTERN.search(line)
    if match:
        return match.group(0)
    return None


if __name__ == "__main__":
    sample_text = ""
    print("Email:", extract_email_from_resume(sample_text))
    print("All Emails:", extract_all_emails_from_text(sample_text))
