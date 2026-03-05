import os
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def get_correction_learning_store():
    from src.training.correction_learning import get_correction_learning_store as _get_store
    return _get_store()


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().lower().split())


def extract_pattern_from_correction(
    original: str,
    corrected: str
) -> Optional[Dict[str, str]]:
    original_norm = normalize_text(original)
    corrected_norm = normalize_text(corrected)
    
    if not original_norm or not corrected_norm:
        return None
    
    if original_norm == corrected_norm:
        return None
    
    
    if len(corrected_norm) < len(original_norm):
        
        original_words = set(original_norm.split())
        corrected_words = set(corrected_norm.split())
        removed_words = original_words - corrected_words
        
        if removed_words:
            return {
                'original_pattern': ' '.join(sorted(removed_words)),
                'corrected_value': corrected,
                'type': 'removal'
            }
    
    
    original_words = original_norm.split()
    corrected_words = corrected_norm.split()
    
    
    common_prefix_len = 0
    for o, c in zip(original_words, corrected_words):
        if o == c:
            common_prefix_len += 1
        else:
            break
    
    common_suffix_len = 0
    for o, c in zip(reversed(original_words), reversed(corrected_words)):
        if o == c:
            common_suffix_len += 1
        else:
            break
    
    if common_prefix_len > 0 or common_suffix_len > 0:
        
        original_changed = ' '.join(original_words[common_prefix_len:len(original_words)-common_suffix_len] if common_suffix_len else original_words[common_prefix_len:])
        corrected_changed = ' '.join(corrected_words[common_prefix_len:len(corrected_words)-common_suffix_len] if common_suffix_len else corrected_words[common_prefix_len:])
        
        if original_changed and corrected_changed and original_changed != corrected_changed:
            return {
                'original_pattern': original_changed,
                'corrected_value': corrected_changed,
                'type': 'replacement'
            }
    
    return None


def sync_patterns_from_corrections() -> Dict[str, Any]:
    try:
        
        from src.utils.pattern_corrections import PatternCorrectionStore, get_pattern_correction_store
        
        pattern_store = get_pattern_correction_store()
        
        
        store = get_correction_learning_store()
        samples = store.load_samples(status="approved", only_changed=True)
        
        if not samples:
            return {
                "success": True,
                "message": "No correction samples found",
                "patterns_added": 0
            }
        
        
        patterns_added = 0
        fields_processed: Set[str] = set()
        
        for sample in samples:
            field_name = sample.get("field_name", "")
            original = sample.get("original_value", "")
            corrected = sample.get("corrected_value", "")
            confidence = sample.get("confidence_before", 0.5)
            
            if not field_name or not original or not corrected:
                continue
            
            fields_processed.add(field_name)
            
            
            pattern = extract_pattern_from_correction(original, corrected)
            
            if pattern and pattern['original_pattern']:
                
                existing = pattern_store.get_learned_patterns(field_name)
                already_exists = any(
                    p.original_pattern == pattern['original_pattern'] 
                    for p in existing
                )
                
                if not already_exists:
                    pattern_store.add_learned_pattern(
                        field_name=field_name,
                        original_value=pattern['original_pattern'],
                        corrected_value=pattern.get('corrected_value', ''),
                        confidence=confidence
                    )
                    patterns_added += 1
                    logger.info(f"Added pattern for '{field_name}': '{pattern['original_pattern'][:30]}...'")
        
        
        pattern_store._load_learned_patterns()
        
        return {
            "success": True,
            "message": f"Synced patterns from {len(samples)} correction samples",
            "patterns_added": patterns_added,
            "fields_processed": list(fields_processed),
            "total_patterns_in_store": len(pattern_store.learned_patterns)
        }
        
    except Exception as e:
        logger.error(f"Error syncing patterns: {e}")
        return {
            "success": False,
            "message": str(e),
            "patterns_added": 0
        }


def auto_sync_patterns(enabled: bool = True, min_samples: int = 1) -> None:
    if not enabled:
        return
    
    result = sync_patterns_from_corrections()
    if result.get("success") and result.get("patterns_added", 0) > 0:
        logger.info(f"Auto-synced {result['patterns_added']} patterns")


def get_pattern_sync_status() -> Dict[str, Any]:
    try:
        from src.utils.pattern_corrections import get_pattern_correction_store
        
        pattern_store = get_pattern_correction_store()
        store = get_correction_learning_store()
        
        samples = store.load_samples(status="approved", only_changed=True)
        
        return {
            "pattern_file_exists": os.path.exists(pattern_store.storage_path),
            "total_patterns_in_json": len(pattern_store.learned_patterns),
            "total_correction_samples": len(samples),
            "sync_needed": len(pattern_store.learned_patterns) == 0 and len(samples) > 0,
            "pattern_file_path": pattern_store.storage_path
        }
    except Exception as e:
        return {
            "error": str(e)
        }


if __name__ == "__main__":
    
    print("Pattern Sync Status:")
    status = get_pattern_sync_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\nRunning sync...")
    result = sync_patterns_from_corrections()
    print(f"Result: {result}")
