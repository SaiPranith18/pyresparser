import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


LINKS_HEADERS = [
    "links", "contact links", "social links", "profiles", "online profiles",
    "web links", "website", "urls", "social media", "portfolio"
]


STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "about", "interests", "hobbies", "references", "declaration",
    "languages", "awards", "achievements", "publications", "volunteer"
]


LINK_PATTERNS = {
    'github': [
        r'https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?',
        r'github\.com/[a-zA-Z0-9_-]+'
    ],
    'linkedin': [
        r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?',
        r'linkedin\.com/in/[a-zA-Z0-9_-]+'
    ],
    'portfolio': [
        r'https?://(?:www\.)?[a-zA-Z0-9_-]+\.(com|io|me|dev|info|online|site|tech)/?',
    ],
    'twitter': [
        r'https?://(?:www\.)?twitter\.com/[a-zA-Z0-9_]+/?',
        r'twitter\.com/[a-zA-Z0-9_]+'
    ],
    'facebook': [
        r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._/-]+/?',
    ],
    'instagram': [
        r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?',
    ],
    'youtube': [
        r'https?://(?:www\.)?youtube\.com/[a-zA-Z0-9_-]+/?',
    ],
    'medium': [
        r'https?://(?:www\.)?medium\.com/@[a-zA-Z0-9_-]+/?',
    ],
    'kaggle': [
        r'https?://(?:www\.)?kaggle\.com/[a-zA-Z0-9_-]+/?',
    ],
    'hackerrank': [
        r'https?://(?:www\.)?hackerrank\.com/[a-zA-Z0-9_-]+/?',
    ],
    'stackoverflow': [
        r'https?://(?:www\.)?stackoverflow\.com/users/\d+/?',
    ],
    'leetcode': [
        r'https?://(?:www\.)?leetcode\.com/[a-zA-Z0-9_-]+/?',
    ],
    'bitbucket': [
        r'https?://(?:www\.)?bitbucket\.org/[a-zA-Z0-9_-]+/?',
    ],
    'gitlab': [
        r'https?://(?:www\.)?gitlab\.com/[a-zA-Z0-9_-]+/?',
    ],
    'general': [
        r'https?://[^\s]+',
        r'www\.[^\s]+',
    ]
}


def calculate_links_confidence(links_text, original_text):
    if not links_text or not links_text.strip():
        return 0.0
    
    lines = [l.strip() for l in links_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.5
    
    
    length_factor = min(len(links_text) / 100, 1.0) * 0.5
    
    confidence = item_factor + length_factor
    
    if confidence > 0.3 and len(links_text) > 20:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(min(confidence, 1.0), 2)


def is_links_header(line_stripped, line_lower):
    for header in LINKS_HEADERS:
        
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


def extract_links_from_resume(text):
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    
    links_lines = []
    capture = False
    header_found = False
    capture_count = 0

    
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()

        
        is_header = is_links_header(line_stripped, line_lower)

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
            
            links_lines.append(line_stripped)
            capture_count += 1

    
    cleaned = []
    seen = set()
    
    for line in links_lines:
        normalized = line.lower().strip()
        
        
        if normalized in seen:
            continue
        if separator_pattern.match(line):
            continue
            
        cleaned.append(line)
        seen.add(normalized)

    links_text = "\n".join(cleaned)
    
    confidence = calculate_links_confidence(links_text, text)
    
    logger.info(f"Links extraction completed. Entries found: {len(cleaned)}, Confidence: {confidence}")
    
    return links_text, confidence


def extract_all_links_from_text(text):
    if not text:
        return [], 0.0
    
    found_links = []
    
    for link_type, patterns in LINK_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match not in found_links:
                    found_links.append(match)
    
    links_text = "\n".join(found_links)
    confidence = calculate_links_confidence(links_text, text)
    
    logger.info(f"Extracted {len(found_links)} links from text. Confidence: {confidence}")
    
    return found_links, confidence


if __name__ == "__main__":
    sample_text = ""
    print("Links:", extract_links_from_resume(sample_text))
    print("All Links:", extract_all_links_from_text(sample_text))
