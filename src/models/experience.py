import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


EXPERIENCE_HEADERS = [
    "experience", "work experience", "employment history", "employment",
    "professional experience", "work history", "job history", "career history",
    "internship", "internships", "practical experience", "work experience details",
    "employment details", "professional history", "career details", "job profile",
    "responsibilities", "duties", "work history", "employment record",
    "professional background", "career timeline", "job experience"
]


STOP_KEYWORDS = [
    "skills", "education", "projects", "certifications", "summary", "about",
    "technical skills", "strength", "strengths", "personal details",
    "extra-curricular activities", "languages", "interests", "hobbies",
    "references", "declaration", "objective", "career objective", "introduction",
    "contact", "achievements", "awards", "publications", "volunteer experience",
    "training", "workshops", "seminars", "awards & achievements", "declaration"
]


EXPERIENCE_PATTERNS = [
    r'\b(company|organization|employer|work|job|role|position)\b',
    r'\b(20\d{2}|19\d{2})\b',
    r'\b(developer|engineer|manager|analyst|designer|consultant|intern|trainee)\b',
    r'\b(junior|senior|lead|head|principal|staff)\b',
    r'\b(responsible|duties|achievements|developed|created|managed|implemented)\b',
    r'\b(present|current|ongoing)\b'
]


def calculate_experience_confidence(experience_text, original_text):
    if not experience_text or not experience_text.strip():
        return 0.0
    
    lines = [l.strip() for l in experience_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 5, 1.0) * 0.3  
    
    
    pattern_matches = 0
    for pattern in EXPERIENCE_PATTERNS:
        pattern_matches += len(re.findall(pattern, experience_text, re.IGNORECASE))
    
    pattern_factor = min(pattern_matches / 8, 1.0) * 0.4  
    
    
    length_factor = min(len(experience_text) / 500, 1.0) * 0.3
    
    confidence = item_factor + pattern_factor + length_factor
    
    
    if confidence > 0.7:
        confidence = min(confidence * 1.1, 1.0)
    
    return round(min(confidence, 1.0), 2)


def extract_experience_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    experience_lines = []
    capture = False
    header_found = False

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = False
        for header in EXPERIENCE_HEADERS:
            
            if line_lower == header:
                is_header = True
                break
            
            if len(line_stripped) < 60:
                
                if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—:.]+', line_lower):
                    is_header = True
                    break
                
                
                if header in line_lower and len(line_stripped) < 50:
                    header_pos = line_lower.find(header)
                    
                    if header_pos == 0:
                        is_header = True
                        break
                    
                    if header_pos > 0:
                        prefix = line_lower[:header_pos].strip()
                        remainder = line_lower[header_pos + len(header):].strip()
                        
                        if prefix and len(prefix) < 20 and len(remainder) < 5:
                            is_header = True
                            break

        if is_header:
            capture = True
            header_found = True
            continue

        
        if capture and header_found:
            should_stop = False
            for stop in STOP_KEYWORDS:
                
                if line_lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
                    should_stop = True
                    break
                
                if line_lower == stop:
                    should_stop = True
                    break
            
            if should_stop:
                break
        
        
        if capture and header_found and line_stripped and not re.fullmatch(r"-{4,}", line_stripped):
            experience_lines.append(line_stripped)

    
    cleaned = []
    seen = set()
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in experience_lines:
        
        if separator_pattern.match(line):
            continue
        
        if line not in seen:
            cleaned.append(line)
            seen.add(line)

    experience_text = "\n".join(cleaned)
    
    
    confidence = calculate_experience_confidence(experience_text, text)
    
    logger.info(f"Experience extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return experience_text, confidence


if __name__ == "__main__":
    
    sample_text = ""
