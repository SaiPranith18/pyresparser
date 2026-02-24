
import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




LANGUAGE_HEADERS = [
    "languages", "language skills", "known languages", "language proficiency",
    "linguistic skills", "communication skills", "spoken languages"
]

LANGUAGE_STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "about", "interests", "hobbies", "references", "declaration"
]


COMMON_LANGUAGES = [
    "english", "hindi", "telugu", "tamil", "kannada", "malayalam", "marathi", "gujarati",
    "bengali", "punjabi", "urdu", "french", "german", "spanish", "portuguese", "italian",
    "chinese", "japanese", "korean", "arabic", "russian", "dutch", "swedish", "norwegian",
    "danish", "finnish", "polish", "turkish", "vietnamese", "thai", "indonesian", "malay",
    "tagalog", "swahili", "hebrew", "greek", "latin", "sanskrit"
]

LANGUAGE_PROFICIENCY_LEVELS = [
    "native", "fluent", "conversational", "professional", "working",
    "intermediate", "beginner", "elementary", "limited", "basic"
]


def calculate_languages_confidence(languages_text: str, original_text: str) -> float:
    if not languages_text or not languages_text.strip():
        return 0.0
    
    lines = [l.strip() for l in languages_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.4
    
    
    valid_count = 0
    for line in lines:
        line_lower = line.lower()
        if any(lang in line_lower for lang in COMMON_LANGUAGES):
            valid_count += 1
    
    valid_factor = min(valid_count / 3, 1.0) * 0.4
    
    
    length_factor = min(len(languages_text) / 100, 1.0) * 0.2
    
    confidence = item_factor + valid_factor + length_factor
    return round(min(confidence, 1.0), 2)


def extract_languages_from_resume(text: str) -> tuple:
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    languages_lines = []
    capture = False
    header_found = False
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()
        
        
        is_header = False
        for header in LANGUAGE_HEADERS:
            if line_lower == header:
                is_header = True
                break
            if len(line_stripped) < 50:
                if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—]+', line_lower):
                    is_header = True
                    break
        
        if is_header:
            capture = True
            header_found = True
            continue
        
        
        if capture and header_found:
            should_stop = False
            for stop in LANGUAGE_STOP_KEYWORDS:
                if line_lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
                    should_stop = True
                    break
                if line_lower == stop:
                    should_stop = True
                    break
            
            if should_stop:
                break
        
        if capture and header_found and line_stripped:
            
            if any(lang in line_lower for lang in COMMON_LANGUAGES):
                languages_lines.append(line_stripped)
    
    
    cleaned = []
    seen = set()
    for line in languages_lines:
        if line not in seen:
            cleaned.append(line)
            seen.add(line)
    
    languages_text = "\n".join(cleaned)
    confidence = calculate_languages_confidence(languages_text, text)
    
    logger.info(f"Languages extraction completed. Found: {len(cleaned)}, Confidence: {confidence}")
    return languages_text, confidence




INTERESTS_HEADERS = [
    "interests", "hobbies", "personal interests", "activities", "interest",
    "hobby", "leisure activities", "pastimes"
]

INTERESTS_STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "references", "declaration", "languages"
]


def calculate_interests_confidence(interests_text: str, original_text: str) -> float:
    if not interests_text or not interests_text.strip():
        return 0.0
    
    lines = [l.strip() for l in interests_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.5
    
    
    length_factor = min(len(interests_text) / 100, 1.0) * 0.5
    
    confidence = item_factor + length_factor
    return round(min(confidence, 1.0), 2)


def extract_interests_from_resume(text: str) -> tuple:
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    interests_lines = []
    capture = False
    header_found = False
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()
        
        
        is_header = False
        for header in INTERESTS_HEADERS:
            if line_lower == header:
                is_header = True
                break
            if len(line_stripped) < 50:
                if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—]+', line_lower):
                    is_header = True
                    break
        
        if is_header:
            capture = True
            header_found = True
            continue
        
        
        if capture and header_found:
            should_stop = False
            for stop in INTERESTS_STOP_KEYWORDS:
                if line_lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
                    should_stop = True
                    break
                if line_lower == stop:
                    should_stop = True
                    break
            
            if should_stop:
                break
        
        if capture and header_found and line_stripped:
            interests_lines.append(line_stripped)
    
    
    cleaned = []
    seen = set()
    for line in interests_lines:
        if line not in seen:
            cleaned.append(line)
            seen.add(line)
    
    interests_text = "\n".join(cleaned)
    confidence = calculate_interests_confidence(interests_text, text)
    
    logger.info(f"Interests extraction completed. Found: {len(cleaned)}, Confidence: {confidence}")
    return interests_text, confidence




ACHIEVEMENTS_HEADERS = [
    "achievements", "awards", "honors", "recognition", "accomplishments",
    "awards & achievements", "awards and achievements", "honors & awards"
]

ACHIEVEMENTS_STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "references", "declaration", "languages", "interests"
]


def calculate_achievements_confidence(achievements_text: str, original_text: str) -> float:
    if not achievements_text or not achievements_text.strip():
        return 0.0
    
    lines = [l.strip() for l in achievements_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.4
    
    
    achievement_patterns = [
        r'\b(awarded|won|received|achieved|earned|granted)\b',
        r'\b(prize|medal|certificate|recognition|trophy)\b',
        r'\b(winner|first|second|third|top|best)\b'
    ]
    
    pattern_matches = 0
    for pattern in achievement_patterns:
        pattern_matches += len(re.findall(pattern, achievements_text, re.IGNORECASE))
    
    pattern_factor = min(pattern_matches / 3, 1.0) * 0.3
    
    
    length_factor = min(len(achievements_text) / 150, 1.0) * 0.3
    
    confidence = item_factor + pattern_factor + length_factor
    return round(min(confidence, 1.0), 2)


def extract_achievements_from_resume(text: str) -> tuple:
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    achievements_lines = []
    capture = False
    header_found = False
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()
        
        
        is_header = False
        for header in ACHIEVEMENTS_HEADERS:
            if line_lower == header:
                is_header = True
                break
            if len(line_stripped) < 50:
                if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—]+', line_lower):
                    is_header = True
                    break
        
        if is_header:
            capture = True
            header_found = True
            continue
        
        
        if capture and header_found:
            should_stop = False
            for stop in ACHIEVEMENTS_STOP_KEYWORDS:
                if line_lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
                    should_stop = True
                    break
                if line_lower == stop:
                    should_stop = True
                    break
            
            if should_stop:
                break
        
        if capture and header_found and line_stripped:
            achievements_lines.append(line_stripped)
    
    
    cleaned = []
    seen = set()
    for line in achievements_lines:
        if line not in seen:
            cleaned.append(line)
            seen.add(line)
    
    achievements_text = "\n".join(cleaned)
    confidence = calculate_achievements_confidence(achievements_text, text)
    
    logger.info(f"Achievements extraction completed. Found: {len(cleaned)}, Confidence: {confidence}")
    return achievements_text, confidence




PUBLICATIONS_HEADERS = [
    "publications", "papers", "research", "conference papers", "journal articles",
    "thesis", "dissertation", "books", "presentations"
]

PUBLICATIONS_STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "references", "declaration", "awards"
]


def calculate_publications_confidence(publications_text: str, original_text: str) -> float:
    if not publications_text or not publications_text.strip():
        return 0.0
    
    lines = [l.strip() for l in publications_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.4
    
    
    pub_patterns = [
        r'\b(published|presented|conference|journal|paper|article)\b',
        r'\b(research|study|analysis)\b',
        r'\b(isbn|doi|volume|issue)\b'
    ]
    
    pattern_matches = 0
    for pattern in pub_patterns:
        pattern_matches += len(re.findall(pattern, publications_text, re.IGNORECASE))
    
    pattern_factor = min(pattern_matches / 3, 1.0) * 0.3
    
    
    length_factor = min(len(publications_text) / 200, 1.0) * 0.3
    
    confidence = item_factor + pattern_factor + length_factor
    return round(min(confidence, 1.0), 2)


def extract_publications_from_resume(text: str) -> tuple:
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    publications_lines = []
    capture = False
    header_found = False
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()
        
        
        is_header = False
        for header in PUBLICATIONS_HEADERS:
            if line_lower == header:
                is_header = True
                break
            if len(line_stripped) < 50:
                if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—]+', line_lower):
                    is_header = True
                    break
        
        if is_header:
            capture = True
            header_found = True
            continue
        
        
        if capture and header_found:
            should_stop = False
            for stop in PUBLICATIONS_STOP_KEYWORDS:
                if line_lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
                    should_stop = True
                    break
                if line_lower == stop:
                    should_stop = True
                    break
            
            if should_stop:
                break
        
        if capture and header_found and line_stripped:
            publications_lines.append(line_stripped)
    
    
    cleaned = []
    seen = set()
    for line in publications_lines:
        if line not in seen:
            cleaned.append(line)
            seen.add(line)
    
    publications_text = "\n".join(cleaned)
    confidence = calculate_publications_confidence(publications_text, text)
    
    logger.info(f"Publications extraction completed. Found: {len(cleaned)}, Confidence: {confidence}")
    return publications_text, confidence




VOLUNTEER_HEADERS = [
    "volunteer", "volunteering", "community service", "social work",
    "charity", "community involvement", "social activities"
]

VOLUNTEER_STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "summary", "references", "declaration", "awards"
]


def calculate_volunteer_confidence(volunteer_text: str, original_text: str) -> float:
    if not volunteer_text or not volunteer_text.strip():
        return 0.0
    
    lines = [l.strip() for l in volunteer_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    
    
    item_count = len(lines)
    item_factor = min(item_count / 3, 1.0) * 0.4
    
    
    volunteer_patterns = [
        r'\b(volunteer|community|charity|non-profit|social)\b',
        r'\b(organization|foundation|trust|society)\b'
    ]
    
    pattern_matches = 0
    for pattern in volunteer_patterns:
        pattern_matches += len(re.findall(pattern, volunteer_text, re.IGNORECASE))
    
    pattern_factor = min(pattern_matches / 2, 1.0) * 0.3
    
    
    length_factor = min(len(volunteer_text) / 150, 1.0) * 0.3
    
    confidence = item_factor + pattern_factor + length_factor
    return round(min(confidence, 1.0), 2)


def extract_volunteer_from_resume(text: str) -> tuple:
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    volunteer_lines = []
    capture = False
    header_found = False
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()
        
        
        is_header = False
        for header in VOLUNTEER_HEADERS:
            if line_lower == header:
                is_header = True
                break
            if len(line_stripped) < 50:
                if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—]+', line_lower):
                    is_header = True
                    break
        
        if is_header:
            capture = True
            header_found = True
            continue
        
        
        if capture and header_found:
            should_stop = False
            for stop in VOLUNTEER_STOP_KEYWORDS:
                if line_lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
                    should_stop = True
                    break
                if line_lower == stop:
                    should_stop = True
                    break
            
            if should_stop:
                break
        
        if capture and header_found and line_stripped:
            volunteer_lines.append(line_stripped)
    
    
    cleaned = []
    seen = set()
    for line in volunteer_lines:
        if line not in seen:
            cleaned.append(line)
            seen.add(line)
    
    volunteer_text = "\n".join(cleaned)
    confidence = calculate_volunteer_confidence(volunteer_text, text)
    
    logger.info(f"Volunteer extraction completed. Found: {len(cleaned)}, Confidence: {confidence}")
    return volunteer_text, confidence




SUMMARY_HEADERS = [
    "summary", "career summary", "professional summary", "objective",
    "career objective", "profile", "about me", "about", "introduction"
]

SUMMARY_STOP_KEYWORDS = [
    "skills", "education", "experience", "projects", "certifications",
    "references", "declaration"
]


def calculate_summary_confidence(summary_text: str, original_text: str) -> float:
    if not summary_text or not summary_text.strip():
        return 0.0
    
    
    length = len(summary_text)
    if 50 <= length <= 500:
        length_factor = 0.6
    elif length < 50:
        length_factor = 0.3
    else:
        length_factor = max(0.5, 1.0 - (length - 500) / 1000)
    
    
    professional_patterns = [
        r'\b(experienced|skilled|professional|dedicated|motivated)\b',
        r'\b(years|experience|expertise|proficient)\b'
    ]
    
    pattern_matches = 0
    for pattern in professional_patterns:
        pattern_matches += len(re.findall(pattern, summary_text, re.IGNORECASE))
    
    pattern_factor = min(pattern_matches / 3, 1.0) * 0.4
    
    confidence = length_factor + pattern_factor
    return round(min(confidence, 1.0), 2)


def extract_summary_from_resume(text: str) -> tuple:
    if not text:
        return "", 0.0
    
    lines = text.splitlines()
    summary_lines = []
    capture = False
    header_found = False
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()
        
        
        is_header = False
        for header in SUMMARY_HEADERS:
            if line_lower == header:
                is_header = True
                break
            if len(line_stripped) < 50:
                if line_lower.startswith(header) or re.match(rf'^{re.escape(header)}[\s:\-–—]+', line_lower):
                    is_header = True
                    break
        
        if is_header:
            capture = True
            header_found = True
            continue
        
        
        if capture and header_found:
            should_stop = False
            for stop in SUMMARY_STOP_KEYWORDS:
                if line_lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
                    should_stop = True
                    break
                if line_lower == stop:
                    should_stop = True
                    break
            
            if should_stop:
                break
        
        if capture and header_found and line_stripped:
            summary_lines.append(line_stripped)
    
    
    summary_text = " ".join(summary_lines)
    confidence = calculate_summary_confidence(summary_text, text)
    
    logger.info(f"Summary extraction completed. Confidence: {confidence}")
    return summary_text, confidence


if __name__ == "__main__":
    
    sample_text = """
    JOHN DOE
    
    Summary
    Experienced software engineer with 5+ years of experience in Python and JavaScript
    
    Skills
    Python, JavaScript, React
    
    Languages
    English (Fluent), Hindi (Native), Spanish (Basic)
    
    Interests
    Photography, Reading, Hiking
    
    Achievements
    - Best Employee Award 2022
    - Won Hackathon First Prize
    
    Publications
    Research Paper on AI - 2021
    
    Volunteer
    Teaching underprivileged children
    
    Education
    Bachelor of Science
    
    Experience
    Software Engineer at ABC Corp
    """
    
    print("Languages:", extract_languages_from_resume(sample_text))
    print("Interests:", extract_interests_from_resume(sample_text))
    print("Achievements:", extract_achievements_from_resume(sample_text))
    print("Publications:", extract_publications_from_resume(sample_text))
    print("Volunteer:", extract_volunteer_from_resume(sample_text))
    print("Summary:", extract_summary_from_resume(sample_text))
