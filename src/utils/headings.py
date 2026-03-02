import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_section_mapping():
    return {
        "Name": "name",
        "Summary": "summary",
        "Skills": "skills",
        "Technical Skills": "technical skills",
        "Soft Skills": "soft skills",
        "Education": "education",
        "Experience": "experience",
        "Projects": "projects",
        "Certifications": "certifications",
        "Awards": "awards",
        "Languages": "languages",
        "Interests": "interests",
        "References": "references",
        "Publications": "publications",
        "Volunteer": "volunteer",
        "Training": "training",
        "Patents": "patents",
        "Presentations": "presentations",
        "Affiliations": "affiliations",
        "Service": "service",
        "Strengths": "strengths",
        "Declaration": "declaration",
        "Full Resume": "fulltext"
    }



SECTION_HEADINGS = list(get_section_mapping().values())

MAIN_SECTION_HEADINGS = [
    'name', 'summary', 'career objective','objective', 'profile', 'about', 'introduction',
    "skills","technical skills","key skills","core skills","skill set",
    "skills summary","technical expertise","technical competencies","technical proficiencies",
    "technical knowledge","tools & technologies","tools and technologies","technologies",
    "software skills","programming skills","technology stack","tech stack",
    "core competencies","competencies","professional skills","areas of expertise",
    "strengths","skills & abilities","skills and abilities","computer skills","it skills",
    'education','education qualification','educational qualifications','academic qualifications',
    'education & qualifications','education details','education background','academic background','educational profile','educational summary',
    'academic credentials','education and training',
    'academic', 'qualification', 'degree',
    'experience', 'employment', 'work history', 'professional experience',
    'projects', 'project work',
    "certifications","certification","certificates","professional certifications",
    "technical certifications","certifications & training","training & certifications","licenses & certifications",
    "credentials","professional credentials","certifications & courses","courses & certifications",
    "online certifications","professional development","technical training","workshops & certifications",
    "industry certifications",
    "awards", "achievements", "honors", "recognition", "accomplishments",
    "awards & achievements", "awards and achievements", "honors & awards",
    "achievements & awards", "awards received", "awards earned",
    "honors and awards", "professional awards", "academic honors",
    "awards and recognitions", "certifications and awards",
    'languages', 'language skills',
    'interests', 'hobbies',
    "references", "referees", "recommendations", "professional references",
    "personal references", "character references", "reference available",
    "references furnished", "references upon request",
    'publications', 'papers', 'research',
    'volunteer', 'community', 'social work',
    'training', 'workshops', 'seminars', 'courses',
    'patents', 'inventions',
    'presentations', 'talks', 'lectures',
    'affiliations', 'memberships',
    'strengths', 'core strengths',
    'declaration', 'statement'
]


def calculate_headings_confidence(detected_headings, text):
    if not detected_headings or len(detected_headings) == 0:
        return 0.0
    
    
    heading_count = len(detected_headings)
    count_factor = min(heading_count / 8, 1.0) * 0.4
    
    
    text_length = len(text)
    length_factor = min(text_length / 5000, 1.0) * 0.3
    
    
    avg_heading_length = sum(len(h) for h in detected_headings) / len(detected_headings)
    length_quality = 1.0 if 3 <= avg_heading_length <= 40 else 0.5
    
    confidence = count_factor + length_factor + (length_quality * 0.3)
    
    return round(min(confidence, 1.0), 2)


def detect_headings(text):
    detected_headings = []  
    lines = text.splitlines()
    
    
    sub_heading_indices = set()
    
    
    main_heading_positions = []
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        
        if not line_stripped:
            continue
        
        
        is_main_heading = False
        for main_heading in MAIN_SECTION_HEADINGS:
            if line_lower == main_heading or line_lower.startswith(main_heading + ':') or line_lower.startswith(main_heading + ' -'):
                is_main_heading = True
                main_heading_positions.append(i)
                break
        
        
        if not is_main_heading and len(main_heading_positions) > 0:
            
            next_main_pos = None
            for pos in main_heading_positions:
                if pos > i:
                    next_main_pos = pos
                    break
            
            if next_main_pos and (next_main_pos - i) <= 3:
                
                sub_heading_indices.add(i)
    
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        
        
        if i in sub_heading_indices:
            continue
        
        if not line_stripped:
            continue
        
        
        if len(line_stripped) > 40:
            continue
        
        
        if re.match(r'^[\d\s\-–—.:,;]+$', line_stripped):
            continue
        
        if re.match(r'^(19|20)\d{2}[\s\-–]*[a-zA-Z]*[\s\-–]*(present|current|19|20)?\d{0,4}$', line_lower):
            continue
        if re.match(r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-–]*(19|20)\d{2}$', line_lower):
            continue
        
        if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', line_lower):
            continue
        if re.match(r'^\+?[\d\s\-–()]+$', line_stripped) and len(line_stripped) > 7:
            continue
        if re.match(r'^(https?://|www\.)', line_lower):
            continue
        
        
        if re.match(r'^[A-Z][a-z]+,\s+[A-Z]\.', line_stripped):
            continue
        
        
        if re.match(r'^[\•\-\*\◦\▪\▸]', line_stripped):
            continue
        
        
        if 'advisor:' in line_lower or 'committee:' in line_lower or 'thesis:' in line_lower:
            continue
        
        
        if 'name of' in line_lower:
            continue
        
        
        is_valid_main_heading = False
        for main_heading in MAIN_SECTION_HEADINGS:
            
            if line_lower == main_heading:
                is_valid_main_heading = True
                break
            
            if line_lower.startswith(main_heading + ':') or line_lower.startswith(main_heading + ' -') or line_lower.startswith(main_heading + ' —'):
                is_valid_main_heading = True
                break
            
            if line_lower.startswith(main_heading) and len(line_stripped) <= len(main_heading) + 5:
                is_valid_main_heading = True
                break
        
        if not is_valid_main_heading:
            continue
        
        
        is_followed_by_content = False
        content_indicators = ['developed', 'worked', 'managed', 'created', 'responsible', 
                             'bachelor', 'master', 'phd', 'python', 'java', 'javascript',
                             'university', 'college', 'graduated', 'degree', 'experience',
                             'year', 'skill', 'education', 'project', 'company', 'inc', 'llc',
                             'technologies', 'tools', 'framework', 'database', 'server']
        
        for j in range(i + 1, min(i + 4, len(lines))):
            next_line = lines[j].strip()
            if next_line:
                next_lower = next_line.lower()
                
                
                is_next_heading = False
                for main_heading in MAIN_SECTION_HEADINGS:
                    if next_lower == main_heading or next_lower.startswith(main_heading + ':'):
                        is_next_heading = True
                        break
                
                if is_next_heading:
                    break
                
                
                if any(indicator in next_lower for indicator in content_indicators):
                    is_followed_by_content = True
                    break
                
                elif len(next_line) > 15:
                    is_followed_by_content = True
                    break
        
        
        is_after_empty_line = (i == 0) or (lines[i-1].strip() == '')
        
        
        if is_followed_by_content and (is_after_empty_line or len(line_stripped) <= 25):
            
            words = line_lower.split()
            
            
            if len(words) > 5:
                continue
            
            
            content_words = ['developed', 'worked', 'managed', 'responsible', 'created', 'led']
            if any(word in line_lower for word in content_words):
                continue
            
            category = normalize_heading(line_stripped)
            detected_headings.append((category, line_stripped))
    
    
    seen_headings = set()
    unique_headings = []
    for heading in detected_headings:
        if heading[1] not in seen_headings:
            seen_headings.add(heading[1])
            unique_headings.append(heading)
    
    detected_headings = unique_headings
    
    
    max_headings = 15
    if len(detected_headings) > max_headings:
        
        detected_headings = detected_headings[:max_headings]
    
    
    confidence = calculate_headings_confidence(detected_headings, text)
    
    logger.info(f"Detected headings: {detected_headings}, Confidence: {confidence}")
    return detected_headings, confidence


def normalize_heading(heading_text):
    heading_lower = heading_text.lower().strip()
    
    
    if any(kw in heading_lower for kw in ['name', 'personal', 'contact', 'profile']):
        return 'name'
    elif any(kw in heading_lower for kw in ['summary', 'career objective','objective', 'about', 'introduction', 'profile']):
        return 'summary'
    elif any(kw in heading_lower for kw in ["skills","technical skills","key skills","core skills","skill set",
                     "skills summary","technical expertise","technical competencies","technical proficiencies",
                    "technical knowledge","tools & technologies","tools and technologies","technologies",
                    "software skills","programming skills","technology stack","tech stack",
                    "core competencies","competencies","professional skills","areas of expertise",
                    "strengths","skills & abilities","skills and abilities","computer skills","it skills"]):
        return 'skills'
    elif any(kw in heading_lower for kw in ['education','education qualification','educational qualifications','academic qualifications',
                                    'education & qualifications','education details','education background','academic background','educational profile','educational summary',
                                     'academic credentials','education and training']):
        return 'education'
    elif any(kw in heading_lower for kw in ['experience', 'work', 'employment', 'job', 'career', 'internship']):
        return 'experience'
    elif any(kw in heading_lower for kw in ['project']):
        return 'projects'
    elif any(kw in heading_lower for kw in ["certifications","certification","certificates","professional certifications",
                        "technical certifications","certifications & training","training & certifications","licenses & certifications",
                        "credentials","professional credentials","certifications & courses","courses & certifications",
                        "online certifications","professional development","technical training","workshops & certifications",
                        "industry certifications"]):
        return 'certifications'
    elif any(kw in heading_lower for kw in ["awards", "achievements", "honors", "recognition", "accomplishments",
    "awards & achievements", "awards and achievements", "honors & awards",
    "achievements & awards", "awards received", "awards earned",
    "honors and awards", "professional awards", "academic honors",
    "awards and recognitions", "certifications and awards"]):
        return 'awards'
    elif any(kw in heading_lower for kw in ['languages']):
        return 'languages'
    elif any(kw in heading_lower for kw in ['interest', 'hobby', 'activity']):
        return 'interests'
    elif any(kw in heading_lower for kw in ["references", "referees", "recommendations", "professional references",
    "personal references", "character references", "reference available",
    "references furnished", "references upon request"]):
        return 'references'
    elif any(kw in heading_lower for kw in ['publication', 'paper', 'research', 'journal', 'book']):
        return 'publications'
    elif any(kw in heading_lower for kw in ['volunteer', 'community', 'social']):
        return 'volunteer'
    elif any(kw in heading_lower for kw in ['training', 'seminar', 'workshop']):
        return 'training'
    elif any(kw in heading_lower for kw in ['patent', 'invention']):
        return 'patents'
    elif any(kw in heading_lower for kw in ['presentation', 'talk', 'keynote', 'lecture']):
        return 'presentations'
    elif any(kw in heading_lower for kw in ['affiliation', 'membership', 'society']):
        return 'affiliations'
    elif any(kw in heading_lower for kw in ['service']):
        return 'service'
    elif any(kw in heading_lower for kw in ['strength','strengths', 'competency', 'attribute']):
        return 'strengths'
    elif any(kw in heading_lower for kw in ['declaration', 'statement', 'legal']):
        return 'declaration'
    else:
        
        return 'custom_' + heading_lower.replace(' ', '_')[:20]
    


if __name__ == "__main__":
    
    sample_text = ''
    
    headings = detect_headings(sample_text)
    print("Detected headings:", headings)
