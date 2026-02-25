import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


AWARD_HEADERS = [
    "awards", "achievements", "honors", "recognition", "accomplishments",
    "awards & achievements", "awards and achievements", "honors & awards",
    "achievements & awards", "awards received", "awards earned",
    "honors and awards", "professional awards", "academic honors",
    "awards and recognitions", "certifications and awards"
]


STOP_KEYWORDS = [
    "skills", "projects", "education", "experience", "certifications",
    "summary", "about", "technical skills", "work experience", "employment",
    "internships", "languages", "interests", "hobbies", "references",
    "declaration", "contact", "personal details", "publications",
    "volunteer", "training", "workshops"
]


AWARD_KEYWORDS = [
    r'\b(awarded|won|received|achieved|earned|granted)\b',
    r'\b(prize|medal|certificate|recognition|trophy|plaque)\b',
    r'\b(winner|first|second|third|top|best|honorable)\b',
    r'\b(competition|contest|event|hackathon|challenge)\b',
    r'\b(scholarship|fellowship|stipend)\b',
    r'\b(dean.*list|president.*list|honor.*roll)\b'
]


YEAR_PATTERN = re.compile(r'^(19|20)\d{2}(\s*[-–]\s*(19|20)\d{2})?$')


def calculate_awards_confidence(awards_text, original_text):
    if not awards_text or not awards_text.strip():
        return 0.0
    
    lines = [l.strip() for l in awards_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 5, 1.0) * 0.4
    
    
    award_matches = 0
    for pattern in AWARD_KEYWORDS:
        award_matches += len(re.findall(pattern, awards_text, re.IGNORECASE))
    
    pattern_factor = min(award_matches / 5, 1.0) * 0.4
    
    
    length_factor = min(len(awards_text) / 150, 1.0) * 0.2
    
    confidence = item_factor + pattern_factor + length_factor
    
    
    if confidence > 0.3 and len(awards_text) > 20:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(min(confidence, 1.0), 2)


def is_award_header(line_stripped, line_lower):
    for header in AWARD_HEADERS:
        
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


def extract_awards_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    
    awards_lines = []
    capture = False
    header_found = False
    capture_count = 0

    
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = is_award_header(line_stripped, line_lower)

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
            
            awards_lines.append(line_stripped)
            capture_count += 1

    
    cleaned = []
    seen = set()
    
    for line in awards_lines:
        normalized = line.lower().strip()
        
        
        if normalized in seen:
            continue
        if separator_pattern.match(line):
            continue
            
        cleaned.append(line)
        seen.add(normalized)

    awards_text = "\n".join(cleaned)
    
    
    if not awards_text.strip():
        awards_text, cleaned = extract_awards_by_keywords(text)
    
    confidence = calculate_awards_confidence(awards_text, text)
    
    logger.info(f"Awards extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return awards_text, confidence


def extract_awards_by_keywords(text):
    lines = text.splitlines()
    awards_lines = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        line_lower = line_stripped.lower()
        
        
        has_award_keyword = False
        for pattern in AWARD_KEYWORDS:
            if re.search(pattern, line_lower, re.IGNORECASE):
                has_award_keyword = True
                break
        
        if has_award_keyword:
            
            if i > 0:
                prev_line = lines[i-1].strip()
                if prev_line and len(prev_line) < 50 and prev_line not in awards_lines:
                    
                    is_stop = False
                    for stop in STOP_KEYWORDS:
                        if stop in prev_line.lower():
                            is_stop = True
                            break
                    if not is_stop:
                        awards_lines.append(prev_line)
            
            if line_stripped not in awards_lines:
                awards_lines.append(line_stripped)
    
    
    cleaned = []
    seen = set()
    for line in awards_lines:
        normalized = line.lower().strip()
        if normalized not in seen:
            cleaned.append(line)
            seen.add(normalized)
    
    return "\n".join(cleaned), cleaned


if __name__ == "__main__":
    sample_text = ""
