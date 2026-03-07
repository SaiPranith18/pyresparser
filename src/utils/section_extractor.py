import re
import os
import logging
from typing import Dict, Any, Tuple, Optional

from src.utils.headings import SECTION_HEADINGS


from src.models.education import extract_education_from_resume
from src.models.skills import extract_skills_from_resume
from src.models.certifications import extract_certifications_from_resume
from src.models.projects import extract_projects_section
from src.models.experience import extract_experience_from_resume
from src.models.awards import extract_awards_from_resume
from src.models.references import extract_references_from_resume
from src.models.declaration import extract_declaration_from_resume
from src.models.contact import extract_contact_from_resume
from src.models.strengths import extract_strengths_from_resume
from src.models.training import extract_training_from_resume
from src.models.extracurricular import extract_extracurricular_from_resume
from src.models.email import extract_email_from_resume, extract_all_emails_from_text
from src.models.phone import extract_phone_from_resume, extract_all_phones_from_text
from src.models.links import extract_links_from_resume, extract_all_links_from_text



_CORRECTION_ENGINE = None


def _get_correction_engine():
    global _CORRECTION_ENGINE
    if _CORRECTION_ENGINE is None:
        try:
            from src.training.correction_learning import get_correction_model_engine
            _CORRECTION_ENGINE = get_correction_model_engine()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not load correction engine: {e}")
    return _CORRECTION_ENGINE


def _apply_corrections(field_name: str, value: str, confidence: float) -> Tuple[str, float, Dict[str, Any]]:
    if not value:
        return value, confidence, {"applied": False}
    
    engine = _get_correction_engine()
    if engine is None:
        return value, confidence, {"applied": False, "reason": "engine_not_available"}
    
    try:
        result = engine.apply(
            field_name=field_name,
            value=value,
            confidence=confidence,
            force=False
        )
        
        if result.get("applied"):
            return (
                result.get("corrected_value"),
                result.get("confidence", confidence),
                {
                    "applied": True,
                    "reason": result.get("reason"),
                    "similarity": result.get("similarity"),
                    "model_version": result.get("model_version")
                }
            )
        
        return value, confidence, {"applied": False, "reason": result.get("reason")}
        
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error applying corrections: {e}")
        return value, confidence, {"applied": False, "error": str(e)}


try:
    from src.extractors.layoutlm_extractor import extract_with_layoutlm, is_layoutlm_available
    LAYOUTLM_AVAILABLE = is_layoutlm_available()
except ImportError:
    LAYOUTLM_AVAILABLE = False
    extract_with_layoutlm = None


try:
    from src.utils.ats_extractor import extract_all_ats_sections, is_likely_ats_format
    ATS_EXTRACTOR_AVAILABLE = True
except ImportError:
    ATS_EXTRACTOR_AVAILABLE = False
    extract_all_ats_sections = None
    is_likely_ats_format = None


LAYOUTLM_CONFIDENCE_THRESHOLD = 0.7  
ATS_CONFIDENCE_THRESHOLD = 0.7  


LAYOUTLM_SECTION_MAP = {
    "name": "name",
    "email": "email",
    "phone": "phone",
    "summary": "summary",
    "skills": "skills",
    "education": "education",
    "experience": "experience",
    "projects": "projects",
    "certifications": "certifications",
    "languages": "languages"
}


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


SECTION_KEYWORDS = {
    "name": ["name", "personal details", "personal information", "contact info", "profile"],
    "summary": ["summary", "career summary", "professional summary", "objective", 
                 "career objective", "profile", "about me", "about", "introduction"],
    "skills": ["skills", "technical skills", "key skills", "core skills", "skill set",
               "skills summary", "technical expertise", "technical competencies", 
               "technical proficiencies", "technologies", "tools & technologies",
               "tools and technologies", "software skills", "programming skills",
               "technology stack", "tech stack", "competencies", "professional skills",
               "areas of expertise", "computer skills", "it skills", "skills & abilities",
               "skills and abilities"],
    "education": ["education", "education qualification", "educational qualifications",
                  "academic qualifications", "education & qualifications", "education details",
                  "education background", "academic background", "educational profile",
                  "educational summary", "academic credentials", "qualification", "qualifications",
                  "academic details", "degree", "degrees"],
    "experience": ["experience", "work experience", "employment history", "employment",
                   "professional experience", "work history", "job history", "career history",
                   "internship", "internships", "practical experience"],
    "projects": ["projects", "project", "academic projects", "personal projects",
                 "project experience", "project details", "key projects", "project work",
                 "major projects", "minor projects"],
    "certifications": ["certifications", "certificates", "certification", "credentials",
                       "licenses", "licenses & certifications", "certifications & licenses",
                       "professional certifications", "certifications earned", 
                       "certifications obtained", "certificate", "certified", "license"],
    "awards": ["awards", "achievements", "honors", "recognition", "accomplishments",
               "awards & achievements", "awards and achievements"],
    "languages": ["languages", "language skills", "language proficiency", "known languages"],
    "interests": ["interests", "hobbies", "personal interests", "activities"],
    "references": ["references", "referees", "recommendations"],
    "declaration": ["declaration", "statement", "legal"],
    "contact": ["contact", "contact details", "contact information", "email", "phone", "address"],
    "publications": ["publications", "papers", "research", "conference papers"],
    "volunteer": ["volunteer", "volunteering", "community service", "social work"],
    "training": ["training", "workshops", "seminars", "courses", "professional development"],
    "strengths": ["strengths", "strength", "key strengths", "personal strengths", "core strengths"],
    "extra-curricular": ["extra-curricular", "extracurricular", "co-curricular"]
}


STOP_KEYWORDS = {
    "skills": ["education", "projects", "experience", "certifications", "summary", 
               "about", "technical skills", "strength", "strengths", "personal details",
               "extra-curricular activities", "languages", "interests", "hobbies", 
               "references", "declaration", "objective", "career objective", 
               "introduction", "contact", "achievements", "awards", "publications",
               "volunteer experience", "internships", "work experience", "employment",
               "professional experience", "awards & achievements"],
    "education": ["skills", "projects", "experience", "certifications", "summary",
                  "about", "technical skills", "work experience", "employment",
                  "internships", "achievements", "awards"],
    "projects": ["education", "experience", "skills", "certifications", "summary",
                 "about", "contact", "references", "achievements", "awards",
                 "languages", "declaration"],
    "experience": ["skills", "projects", "education", "certifications", "summary",
                   "about", "contact", "references", "achievements", "awards",
                   "languages", "interests", "hobbies", "declaration"],
    "certifications": ["skills", "projects", "education", "experience", "summary",
                       "about", "technical skills", "work experience", "employment",
                       "interships", "achievements", "awards", "languages"],
    "summary": ["skills", "projects", "education", "experience", "certifications",
                "about", "technical skills", "work experience", "employment",
                "contact", "references"],
    "awards": ["skills", "projects", "education", "experience", "certifications",
               "summary", "languages", "interests", "references", "declaration"],
    "languages": ["skills", "projects", "education", "experience", "certifications",
                  "summary", "interests", "hobbies", "references", "declaration"],
    "interests": ["skills", "projects", "education", "experience", "certifications",
                  "summary", "references", "declaration"],
    "references": ["declaration"],
    "declaration": [],
    "contact": ["skills", "projects", "education", "experience", "certifications",
               "summary", "references"],
    "publications": ["skills", "projects", "education", "experience", "certifications",
                     "summary", "references"],
    "volunteer": ["skills", "projects", "education", "experience", "certifications",
                  "summary", "references", "declaration"],
    "training": ["skills", "projects", "education", "experience", "certifications",
                 "summary", "references"],
    "strengths": ["skills", "projects", "education", "experience", "certifications",
                 "summary", "references"],
    "name": ["summary", "skills", "education", "experience", "projects",
             "certifications", "contact"]
}


SECTION_PATTERNS = {
    "skills": [
        r'\b(python|java|javascript|html|css|sql|react|angular|vue|node|django|flask)\b',
        r'\b(machine learning|deep learning|data science|artificial intelligence)\b',
        r'\b(aws|azure|gcp|docker|kubernetes|jenkins|git)\b',
        r'\b(c\+\+|c#|ruby|php|swift|kotlin|go|rust)\b',
        r'\b(mysql|postgresql|mongodb|redis|elasticsearch)\b',
        r'\b(framework|library|tool|platform|language)\b'
    ],
    "education": [
        r'\b(bachelor|master|phd|doctorate|diploma|certificate)\b',
        r'\b(20\d{2}|19\d{2})\b',
        r'\b(university|college|institute|school)\b',
        r'\b(gpa|grade|percentage|score)\b',
        r'\b(degree|graduation|passed)\b'
    ],
    "projects": [
        r'\b(developed|built|created|designed|implemented|led)\b',
        r'\b(python|java|javascript|react|angular|node|django|flask)\b',
        r'\b(machine learning|data science|api|database|web)\b',
        r'\b(github|gitlab|heroku|aws|azure)\b',
        r'\b(project|team|application|system)\b'
    ],
    "experience": [
        r'\b(company|organization|employer|work)\b',
        r'\b(20\d{2}|19\d{2})\b',
        r'\b(developer|engineer|manager|analyst|designer|consultant)\b',
        r'\b(intern|junior|senior|lead|head)\b',
        r'\b(responsible|duties|achievements)\b'
    ],
    "certifications": [
        r'\b(certified|certificate|certification)\b',
        r'\b(aws|azure|gcp|google|amazon|microsoft)\b',
        r'\b(pmp|scrum|agile|pmi|itil|ccna|ccnp|mcse|mcsa)\b',
        r'\b(iso|ceh|cissp|cisa|comptia)\b',
        r'\b(license|earned|obtained)\b'
    ],
    "awards": [
        r'\b(awarded|won|received|achieved)\b',
        r'\b(prize|medal|certificate|recognition)\b',
        r'\b(competition|contest|event)\b',
        r'\b(first|second|third|winner)\b'
    ]
}


def calculate_section_confidence(section_text, original_text, section_type):
    if not section_text or not section_text.strip():
        return 0.0
    
    lines = [l.strip() for l in section_text.splitlines() if l.strip()]
    
    if not lines:
        return 0.0
    

    item_count = len(lines)
    item_factor = min(item_count / 5, 1.0) * 0.3  
    

    patterns = SECTION_PATTERNS.get(section_type, [])
    pattern_matches = 0
    for pattern in patterns:
        pattern_matches += len(re.findall(pattern, section_text, re.IGNORECASE))
    

    if section_type in ["skills", "education", "experience", "projects", "certifications"]:
        pattern_factor = min(pattern_matches / 5, 1.0) * 0.4
    else:
        pattern_factor = min(pattern_matches / 3, 1.0) * 0.3
    

    length_factor = min(len(section_text) / 200, 1.0) * 0.3
    

    relevance_factor = 0.0
    if section_type in SECTION_KEYWORDS:
        keywords = SECTION_KEYWORDS[section_type]
       
        keyword_count = sum(1 for kw in keywords if kw.lower() in section_text.lower())
        relevance_factor = min(keyword_count / 3, 1.0) * 0.1
    
    confidence = item_factor + pattern_factor + length_factor + relevance_factor

    if confidence > 0.7:
        confidence = min(confidence * 1.1, 1.0)  
    
    return round(min(confidence, 1.0), 2)


def extract_section_by_type(text, section_type):
    if not text:
        return "", 0.0
    
    keywords = SECTION_KEYWORDS.get(section_type.lower(), [])
    stops = STOP_KEYWORDS.get(section_type.lower(), [])
    
    lines = text.splitlines()
    section_lines = []
    capture = False
    header_found = False
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()
  
        is_header = False
        for keyword in keywords:
           
            if line_lower == keyword:
                is_header = True
                break
      
            
            if len(line_stripped) < 50:
             
                if line_lower.startswith(keyword) or re.match(rf'^{re.escape(keyword)}[\s:\-–—]+', line_lower):
                    is_header = True
                    break
                
                if keyword in line_lower and len(line_stripped) < 40:
                   
                    keyword_pos = line_lower.find(keyword)
                    if keyword_pos == 0 or (keyword_pos > 0 and line_stripped[keyword_pos-1] in ' -:'):
                        is_header = True
                        break
        
        if is_header:
            capture = True
            header_found = True
            continue


        if capture and header_found and len(section_lines) > 0:
            should_stop = False
            for stop in stops:
           
                if line_lower.startswith(stop) or re.match(rf'^{re.escape(stop)}[\s:\-–—]+', line_lower):
                    should_stop = True
                    break
             
                if line_lower == stop:
                    should_stop = True
                    break
            
            if should_stop and len(section_lines) >= 2:
                break
            

            if not any(kw in line_lower for kw in keywords):
                section_lines.append(line_stripped)
    

    cleaned = []
    seen = set()
    separator_pattern = re.compile(r'^[-–—=_*#]+$')
    
    for line in section_lines:
        
        if len(line) < 2:
            continue
        
        if separator_pattern.match(line):
            continue
       
        if re.match(r'^(19|20)\d{2}(\s*[-–]\s*(19|20)\d{2})?$', line):
            continue
       
        if line not in seen:
            cleaned.append(line)
            seen.add(line)
    
    section_text = "\n".join(cleaned)

    confidence = calculate_section_confidence(section_text, text, section_type.lower())
    
    logger.info(f"Extracted section '{section_type}'. Items found: {len(cleaned)}, Confidence: {confidence}")
    
    return section_text, confidence


def enhance_with_layoutlm(pdf_path, section_type, traditional_result, traditional_confidence):
    if not LAYOUTLM_AVAILABLE:
        logger.info(f"LayoutLMv3 not available for section '{section_type}'")
        return traditional_result, traditional_confidence, False
    
    if traditional_confidence >= LAYOUTLM_CONFIDENCE_THRESHOLD:
        logger.info(f"Traditional extraction confidence ({traditional_confidence}) >= threshold ({LAYOUTLM_CONFIDENCE_THRESHOLD}), skipping LayoutLMv3")
        return traditional_result, traditional_confidence, False
    
    if section_type.lower() not in LAYOUTLM_SECTION_MAP:
        logger.info(f"Section type '{section_type}' not supported by LayoutLMv3")
        return traditional_result, traditional_confidence, False
    
    if not pdf_path or not os.path.exists(pdf_path):
        logger.warning(f"Invalid PDF path for LayoutLMv3: {pdf_path}")
        return traditional_result, traditional_confidence, False
    
    try:
        logger.info(f"Enhancing section '{section_type}' with LayoutLMv3 (traditional confidence: {traditional_confidence})")
        
        layoutlm_result, layoutlm_confidence = extract_with_layoutlm(pdf_path)
        
        if not layoutlm_result or "error" in layoutlm_result:
            logger.warning(f"LayoutLMv3 extraction failed: {layoutlm_result.get('error', 'Unknown error')}")
            return traditional_result, traditional_confidence, False
        
        layoutlm_section_key = LAYOUTLM_SECTION_MAP.get(section_type.lower())
        layoutlm_value = layoutlm_result.get(layoutlm_section_key)
        
        if not layoutlm_value:
            logger.info(f"LayoutLMv3 did not find section '{section_type}'")
            return traditional_result, traditional_confidence, False
        
        if layoutlm_confidence > traditional_confidence:
            logger.info(f"LayoutLMv3 enhanced '{section_type}' (confidence: {layoutlm_confidence} vs {traditional_confidence})")
            return layoutlm_value, layoutlm_confidence, True
        else:
            logger.info(f"LayoutLMv3 confidence ({layoutlm_confidence}) not better than traditional ({traditional_confidence})")
            return traditional_result, traditional_confidence, False
            
    except Exception as e:
        logger.error(f"Error enhancing with LayoutLMv3: {e}")
        return traditional_result, traditional_confidence, False


def _try_ats_fallback(text, section_type):
    if not ATS_EXTRACTOR_AVAILABLE or not text:
        return None
    
    ats_supported = ['name', 'skills', 'education', 'experience', 'summary']
    if section_type.lower() not in ats_supported:
        return None
    
    try:
        ats_results = extract_all_ats_sections(text)
        ats_result = ats_results.get(section_type.lower())
        
        if ats_result and ats_result[0] and ats_result[1] >= ATS_CONFIDENCE_THRESHOLD:
            logger.info(f"ATS fallback used for '{section_type}' (confidence: {ats_result[1]})")
            return ats_result
        
    except Exception as e:
        logger.debug(f"ATS fallback failed for '{section_type}': {e}")
    
    return None


def _try_ats_primary(text, section_type):
    if not ATS_EXTRACTOR_AVAILABLE or not text:
        return None
    
    if not is_likely_ats_format(text):
        return None
    
    ats_supported = ['name', 'skills', 'education', 'experience', 'summary']
    if section_type.lower() not in ats_supported:
        return None
    
    try:
        ats_results = extract_all_ats_sections(text)
        ats_result = ats_results.get(section_type.lower())
        
        if ats_result and ats_result[0]:
            logger.info(f"ATS primary extraction used for '{section_type}' (confidence: {ats_result[1]})")
            return ats_result
        
    except Exception as e:
        logger.debug(f"ATS primary extraction failed for '{section_type}': {e}")
    
    return None


def extract_section_from_resume(text, section_type, pdf_path=None):
    if not text:
        return "", 0.0
    

    section_type = section_type.lower().strip()


    if section_type == "fulltext":
        from src.utils.formatter import clean_fulltext_format
        result = clean_fulltext_format(text)
        return result, 0.95
    
    if section_type == "name":
        from src.models.name import extract_name_from_resume
        result, confidence = extract_name_from_resume(text)
        
        if pdf_path and confidence < LAYOUTLM_CONFIDENCE_THRESHOLD:
            result, confidence, _ = enhance_with_layoutlm(pdf_path, section_type, result, confidence)
        
        
        if confidence < ATS_CONFIDENCE_THRESHOLD:
            ats_result = _try_ats_fallback(text, section_type)
            if ats_result and ats_result[1] > confidence:
                result, confidence = ats_result
        
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    

    if section_type == "skills":
        result, confidence = extract_skills_from_resume(text)
        
        if pdf_path and confidence < LAYOUTLM_CONFIDENCE_THRESHOLD:
            result, confidence, _ = enhance_with_layoutlm(pdf_path, section_type, result, confidence)
        
        
        if confidence < ATS_CONFIDENCE_THRESHOLD:
            ats_result = _try_ats_fallback(text, section_type)
            if ats_result and ats_result[1] > confidence:
                result, confidence = ats_result
        
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "education":
        result, confidence = extract_education_from_resume(text)
        
        if pdf_path and confidence < LAYOUTLM_CONFIDENCE_THRESHOLD:
            result, confidence, _ = enhance_with_layoutlm(pdf_path, section_type, result, confidence)
        
        
        if confidence < ATS_CONFIDENCE_THRESHOLD:
            ats_result = _try_ats_fallback(text, section_type)
            if ats_result and ats_result[1] > confidence:
                result, confidence = ats_result
        
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "certifications":
        result, confidence = extract_certifications_from_resume(text)
        
        if pdf_path and confidence < LAYOUTLM_CONFIDENCE_THRESHOLD:
            result, confidence, _ = enhance_with_layoutlm(pdf_path, section_type, result, confidence)
        
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "projects":
        result, confidence = extract_projects_section(text)
        
        if pdf_path and confidence < LAYOUTLM_CONFIDENCE_THRESHOLD:
            result, confidence, _ = enhance_with_layoutlm(pdf_path, section_type, result, confidence)
        
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "experience":
        result, confidence = extract_experience_from_resume(text)
        
        if pdf_path and confidence < LAYOUTLM_CONFIDENCE_THRESHOLD:
            result, confidence, _ = enhance_with_layoutlm(pdf_path, section_type, result, confidence)
        
        
        if confidence < ATS_CONFIDENCE_THRESHOLD:
            ats_result = _try_ats_fallback(text, section_type)
            if ats_result and ats_result[1] > confidence:
                result, confidence = ats_result
        
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "awards":
        result, confidence = extract_awards_from_resume(text)
        
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "references":
        result, confidence = extract_references_from_resume(text)
        
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "declaration":
        result, confidence = extract_declaration_from_resume(text)
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "contact":
        result, confidence = extract_contact_from_resume(text)
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "strengths":
        result, confidence = extract_strengths_from_resume(text)
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "training":
        result, confidence = extract_training_from_resume(text)
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "extra-curricular":
        result, confidence = extract_extracurricular_from_resume(text)
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "email":
        result, confidence = extract_email_from_resume(text)
        
        
        if not result or confidence == 0.0:
            emails, conf = extract_all_emails_from_text(text)
            if emails:
                result = "\n".join(emails)
                confidence = conf
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "phone":
        result, confidence = extract_phone_from_resume(text)
        
        
        if not result or confidence == 0.0:
            phones, conf = extract_all_phones_from_text(text)
            if phones:
                result = "\n".join(phones)
                confidence = conf
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    if section_type == "links":
        result, confidence = extract_links_from_resume(text)
        
        
        if not result or confidence == 0.0:
            links, conf = extract_all_links_from_text(text)
            if links:
                result = "\n".join(links)
                confidence = conf
        
        result, confidence, _ = _apply_corrections(section_type, result, confidence)
        return result, confidence
    
    
    result, confidence = extract_section_by_type(text, section_type)
    if pdf_path and confidence < LAYOUTLM_CONFIDENCE_THRESHOLD:
        result, confidence, _ = enhance_with_layoutlm(pdf_path, section_type, result, confidence)
    
    
    result, confidence, _ = _apply_corrections(section_type, result, confidence)
    return result, confidence


def get_available_sections():
    return list(SECTION_KEYWORDS.keys())
