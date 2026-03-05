import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class CorrectionStorage:
    
    def __init__(self):
        self._cached_corrections: Dict[str, Dict[str, str]] = {}
        self._cache_loaded = False
    
    def _load_corrections(self) -> Dict[str, Dict[str, str]]:
        if self._cache_loaded:
            return self._cached_corrections
        
        corrections: Dict[str, Dict[str, str]] = {}
        
        try:
            from src.training.correction_learning import (
                get_correction_learning_store,
                normalize_text,
                _guess_field,
            )
            
            store = get_correction_learning_store()
            
            
            samples = store.load_samples(status="approved", only_changed=True)
            
            logger.info(f"Loading {len(samples)} correction samples from store")
            
            for sample in samples:
                field = _guess_field(sample.get("field_name", ""))
                original = normalize_text(sample.get("original_value", ""))
                corrected = sample.get("corrected_value", "")
                
                if not original or not corrected:
                    continue
                
                
                if field not in corrections:
                    corrections[field] = {}
                
                
                original_raw = sample.get("original_value", "")
                corrections[field][original_raw.lower()] = corrected
            
            self._cached_corrections = corrections
            self._cache_loaded = True
            
            logger.info(f"Loaded corrections for {len(corrections)} fields: {list(corrections.keys())}")
            
        except Exception as e:
            logger.warning(f"Error loading corrections from store: {e}")
            
            try:
                base_dir = os.path.dirname(os.path.dirname(__file__))
                jsonl_path = os.path.join(base_dir, "learning_data", "structured_corrections.jsonl")
                
                if os.path.exists(jsonl_path):
                    import json
                    with open(jsonl_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            try:
                                sample = json.loads(line)
                                if sample.get("status") != "approved":
                                    continue
                                if sample.get("feedback_type") == "rejection":
                                    continue
                                
                                field = _guess_field(sample.get("field_name", ""))
                                original = sample.get("original_value", "")
                                corrected = sample.get("corrected_value", "")
                                
                                if not original or not corrected:
                                    continue
                                
                                if field not in corrections:
                                    corrections[field] = {}
                                
                                corrections[field][original.lower()] = corrected
                            except:
                                continue
                    
                    self._cached_corrections = corrections
                    self._cache_loaded = True
                    logger.info(f"Loaded corrections from fallback: {len(corrections)} fields")
            except Exception as fallback_error:
                logger.warning(f"Fallback also failed: {fallback_error}")
        
        return corrections
    
    def invalidate_cache(self):
        self._cached_corrections = {}
        self._cache_loaded = False
        logger.info("Correction cache invalidated")
    
    def get_corrections_dict(self, field_name: str) -> Dict[str, str]:
        corrections = self._load_corrections()
        field = field_name.lower().strip()
        
        
        if field in corrections:
            return corrections[field]
        
        
        for key, value in corrections.items():
            if field in key or key in field:
                return value
        
        return {}
    
    def get_all_corrections(self) -> Dict[str, Dict[str, str]]:
        return self._load_corrections()
    
    def apply_correction(self, field_name: str, value: str) -> Optional[str]:
        if not value:
            return None
        
        corrections = self.get_corrections_dict(field_name)
        value_lower = value.lower().strip()
        
        
        if value_lower in corrections:
            corrected = corrections[value_lower]
            logger.info(f"Applied correction for '{field_name}': '{value}' -> '{corrected}'")
            return corrected
        
        
        for original, corrected in corrections.items():
            if original in value_lower or value_lower in original:
                logger.info(f"Applied fuzzy correction for '{field_name}': '{value}' -> '{corrected}'")
                return corrected
        
        return None
    
    def has_corrections(self, field_name: Optional[str] = None) -> bool:
        corrections = self._load_corrections()
        
        if field_name is None:
            return len(corrections) > 0
        
        field = field_name.lower().strip()
        return field in corrections and len(corrections[field]) > 0



_correction_storage: Optional[CorrectionStorage] = None


def get_correction_storage() -> CorrectionStorage:
    global _correction_storage
    if _correction_storage is None:
        _correction_storage = CorrectionStorage()
    return _correction_storage


def invalidate_correction_cache():
    storage = get_correction_storage()
    storage.invalidate_cache()
