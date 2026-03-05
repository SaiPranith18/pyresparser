
import re
import os
import json
import logging
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


SUMMARY_SKILL_PATTERNS = [
    
    r'(?:^|\n)\s*TECHNICAL\s+SK*(ILLS\s?::|\n|$)',
    r'(?:^|\n)\s*SKILLS\s*(?::|\n|$)',
    r'(?:^|\n)\s*TECHNICAL\s+SKILLS\s*[:\-–—]',
    r'(?:^|\n)\s*SKILLS\s*[:\-–—]',
    r'(?:^|\n)\s*PROGRAMMING\s+LANGUAGES\s*(?::|\n|$)',
    r'(?:^|\n)\s*TECHNOLOGIES\s*(?::|\n|$)',
    r'(?:^|\n)\s*TOOLS\s*(?::|\n|$)',
    
    r'^\s*[\u2022\u2023\u25E6\u2043\u2219•\-\*]\s*(?:python|java|javascript|html|css|sql|react|angular|node|django|flask|aws|docker|kubernetes)',
    
    r'(?:Programming Languages|Web Development|Database|Tools|Soft Skills)[:\s]',
    
    r'^(?:TECHNICAL\s+)?SKILLS\s*$',
]


EDUCATION_SKILL_PATTERNS = [
    r'\b(?:python|java|javascript|typescript|react|angular|vue|node|django|flask)\b',
    r'\b(?:aws|azure|gcp|docker|kubernetes|jenkins|git)\b',
    r'\b(?:machine\s+learning|deep\s+learning|data\s+science|AI|ML|DL)\b',
]


SUMMARY_STOP_KEYWORDS = [
    'skills', 'education', 'experience', 'projects', 'certifications',
    'references', 'declaration', 'technical skills', 'technical expertise',
]


SUMMARY_STOP_PATTERNS = [
    r'(?:^|\n)\s*(?:TECHNICAL\s+)?SKILLS\s*(?::|\n|$)',
    r'(?:^|\n)\s*EDUCATION\s*(?::|\n|$)',
    r'(?:^|\n)\s*EXPERIENCE\s*(?::|\n|$)',
    r'(?:^|\n)\s*PROJECTS\s*(?::|\n|$)',
    r'(?:^|\n)\s*CERTIFICATIONS?\s*(?::|\n|$)',
]


@dataclass
class PatternRule:
    field_name: str
    pattern: str
    description: str
    is_regex: bool = True
    replacement: str = ""
    action: str = "remove_after"  
    confidence_boost: float = 0.1
    enabled: bool = True
    source: str = "builtin"  


@dataclass
class LearnedPattern:
    field_name: str
    original_pattern: str  
    corrected_value: str   
    occurrence_count: int = 1
    confidence: float = 0.5
    timestamp: str = ""


class PatternCorrectionStore:
    
    DEFAULT_PATTERNS_FILE = "pattern_corrections.json"
    
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            storage_path = os.path.join(base_dir, 'learning_data', 'pattern_corrections.json')
        
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        
        self.builtin_rules: List[PatternRule] = self._get_builtin_rules()
        self.learned_patterns: List[LearnedPattern] = []
        
        
        self._load_learned_patterns()
    
    def _get_builtin_rules(self) -> List[PatternRule]:
        rules = []
        
        
        for pattern in SUMMARY_SKILL_PATTERNS:
            rules.append(PatternRule(
                field_name="summary",
                pattern=pattern,
                description="Remove skills section from summary",
                action="remove_after",
                source="builtin"
            ))
        
        
        for pattern in SUMMARY_STOP_PATTERNS:
            rules.append(PatternRule(
                field_name="summary",
                pattern=pattern,
                description="Stop summary at section headers",
                action="remove_section",
                source="builtin"
            ))
        
        return rules
    
    def _load_learned_patterns(self) -> None:
        if not os.path.exists(self.storage_path):
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                patterns = data.get('learned_patterns', [])
                for p in patterns:
                    self.learned_patterns.append(LearnedPattern(
                        field_name=p.get('field_name', ''),
                        original_pattern=p.get('original_pattern', ''),
                        corrected_value=p.get('corrected_value', ''),
                        occurrence_count=p.get('occurrence_count', 1),
                        confidence=p.get('confidence', 0.5),
                        timestamp=p.get('timestamp', '')
                    ))
        except Exception as e:
            logger.warning(f"Could not load learned patterns: {e}")
    
    def _save_learned_patterns(self) -> None:
        data = {
            'learned_patterns': [
                {
                    'field_name': p.field_name,
                    'original_pattern': p.original_pattern,
                    'corrected_value': p.corrected_value,
                    'occurrence_count': p.occurrence_count,
                    'confidence': p.confidence,
                    'timestamp': p.timestamp
                }
                for p in self.learned_patterns
            ]
        }
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=True)
    
    def add_learned_pattern(
        self,
        field_name: str,
        original_value: str,
        corrected_value: str,
        confidence: float = 0.5
    ) -> None:
        
        for pattern in self.learned_patterns:
            if (pattern.field_name == field_name and 
                pattern.original_pattern == original_value):
                pattern.occurrence_count += 1
                pattern.confidence = min(1.0, confidence + 0.1)
                self._save_learned_patterns()
                return
        
        
        from datetime import datetime, timezone
        new_pattern = LearnedPattern(
            field_name=field_name,
            original_pattern=original_value,
            corrected_value=corrected_value,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        self.learned_patterns.append(new_pattern)
        self._save_learned_patterns()
    
    def get_all_rules(self, field_name: Optional[str] = None) -> List[PatternRule]:
        rules = self.builtin_rules.copy()
        
        if field_name:
            rules = [r for r in rules if r.field_name == field_name]
        
        return rules
    
    def get_learned_patterns(self, field_name: Optional[str] = None) -> List[LearnedPattern]:
        if field_name:
            return [p for p in self.learned_patterns if p.field_name == field_name]
        return self.learned_patterns.copy()



def correct_summary_with_patterns(text: str) -> Tuple[str, Dict[str, Any]]:
    if not text:
        return text, {"applied": False, "reason": "empty_input"}
    
    original_text = text
    corrections_applied = []
    
    
    for pattern in SUMMARY_SKILL_PATTERNS:
        try:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    
                    skill_start = match.start()
                    
                    
                    next_section = re.search(
                        r'\n\s*(?:EDUCATION|EXPERIENCE|PROJECTS|CERTIFICATIONS|REFERENCES|DECLARATION)',
                        text[skill_start:],
                        re.IGNORECASE
                    )
                    
                    if next_section:
                        
                        skill_end = skill_start + next_section.start()
                        text = text[:skill_start] + text[skill_end:]
                        corrections_applied.append(f"Removed section at position {skill_start}")
                    else:
                        
                        text = text[:skill_start].strip()
                        corrections_applied.append(f"Removed trailing content from skill header")
                    
                    break  
        except re.error as e:
            logger.debug(f"Regex error in pattern {pattern}: {e}")
    
    
    lines = text.split('\n')
    if len(lines) > 2:
        
        summary_part = ""
        skill_part = ""
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            if re.match(r'^\s*(?:technical\s+)?skills\s*[:\-–—]?\s*$', line_lower):
                skill_part = '\n'.join(lines[i:])
                break
            elif len(line) < 100:
                summary_part += line + '\n'
            else:
                skill_part = '\n'.join(lines[i:])
                break
        
        if skill_part and summary_part:
            
            skill_keywords = ['python', 'java', 'javascript', 'html', 'css', 'sql', 
                            'react', 'angular', 'node', 'django', 'flask', 'aws',
                            'docker', 'kubernetes', 'git', 'mysql', 'mongodb']
            skill_count = sum(1 for kw in skill_keywords if kw in skill_part.lower())
            
            if skill_count >= 3:  
                text = summary_part.strip()
                corrections_applied.append("Separated summary from skills section")
    
    
    
    skill_category_pattern = r'\n\s*(Programming Languages|Web Development|Database|Tools|Soft Skills)[:\s]'
    match = re.search(skill_category_pattern, text, re.IGNORECASE)
    if match:
        text = text[:match.start()].strip()
        corrections_applied.append("Removed skill categories from end of summary")
    
    
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    corrected = text != original_text
    return text, {
        "applied": corrected,
        "reason": "pattern_correction" if corrected else None,
        "corrections": corrections_applied,
        "method": "pattern_based"
    }


def correct_field_with_learned_patterns(
    field_name: str,
    text: str,
    pattern_store: PatternCorrectionStore
) -> Tuple[str, Dict[str, Any]]:
    if not text:
        return text, {"applied": False, "reason": "empty_input"}
    
    original_text = text
    learned_patterns = pattern_store.get_learned_patterns(field_name)
    corrections_applied = []
    
    for pattern in learned_patterns:
        if pattern.confidence < 0.3:  
            continue
        
        
        if pattern.original_pattern in text:
            
            if not pattern.corrected_value:
                
                text = text.replace(pattern.original_pattern, "")
                corrections_applied.append(f"Removed pattern: {pattern.original_pattern[:50]}")
            elif pattern.corrected_value != text:
                
                text = text.replace(pattern.original_pattern, pattern.corrected_value)
                corrections_applied.append(f"Replaced pattern: {pattern.original_pattern[:50]}")
    
    
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    
    corrected = text != original_text
    return text, {
        "applied": corrected,
        "reason": "learned_pattern" if corrected else None,
        "corrections": corrections_applied,
        "method": "learned_pattern"
    }


def extract_learned_patterns_from_feedback(
    feedback_data: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, str]]]:
    patterns_by_field: Dict[str, List[Dict[str, str]]] = {}
    
    for feedback in feedback_data:
        field_name = feedback.get('field_name', '')
        original = feedback.get('original_value', '')
        corrected = feedback.get('corrected_value', '')
        
        if not field_name or not original or not corrected:
            continue
        
        if field_name not in patterns_by_field:
            patterns_by_field[field_name] = []
        
        
        
        if len(corrected) < len(original):
            
            diff = set(original.split()) - set(corrected.split())
            if diff:
                removed_text = ' '.join(diff)
                patterns_by_field[field_name].append({
                    'original_pattern': removed_text,
                    'corrected_value': corrected,
                    'type': 'removal'
                })
    
    return patterns_by_field






def apply_all_pattern_corrections(
    field_name: str,
    text: str,
    pattern_store: Optional[PatternCorrectionStore] = None
) -> Tuple[str, Dict[str, Any]]:
    if not text:
        return text, {"applied": False, "reason": "empty_input"}
    
    if pattern_store is None:
        pattern_store = PatternCorrectionStore()
    
    original_text = text
    all_corrections = []
    
    
    if field_name == "summary":
        text, info = correct_summary_with_patterns(text)
        if info.get("applied"):
            all_corrections.extend(info.get("corrections", []))
    
    
    if text:
        text, info = correct_field_with_learned_patterns(field_name, text, pattern_store)
        if info.get("applied"):
            all_corrections.extend(info.get("corrections", []))
    
    
    text = text.strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    corrected = text != original_text
    return text, {
        "applied": corrected,
        "reason": "pattern_corrections" if corrected else None,
        "corrections": all_corrections,
        "fields_applied": ["builtin_patterns", "learned_patterns"] if all_corrections else []
    }


_pattern_store: Optional[PatternCorrectionStore] = None


def get_pattern_correction_store() -> PatternCorrectionStore:
    global _pattern_store
    if _pattern_store is None:
        _pattern_store = PatternCorrectionStore()
    return _pattern_store


def apply_pattern_corrections(
    field_name: str,
    text: str
) -> Tuple[str, Dict[str, Any]]:
    store = get_pattern_correction_store()
    return apply_all_pattern_corrections(field_name, text, store)


def learn_from_correction(
    field_name: str,
    original_value: str,
    corrected_value: str,
    confidence: float = 0.5
) -> None:
    store = get_pattern_correction_store()
    store.add_learned_pattern(field_name, original_value, corrected_value, confidence)
    logger.info(f"Learned pattern for field '{field_name}': {original_value[:50]}...")


if __name__ == "__main__":
    
    test_summary = ""
    
    corrected, info = apply_pattern_corrections("summary", test_summary)
    print("Original:")
    print(test_summary)
    print("\nCorrected:")
    print(corrected)
    print("\nInfo:", info)
