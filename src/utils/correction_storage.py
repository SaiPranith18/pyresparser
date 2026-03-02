import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CorrectionStorage:
    
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            storage_path = os.path.join(base_dir, 'learning_data', 'corrections.json')
        
        self.storage_path = storage_path
        self._ensure_storage_exists()
        
    def _ensure_storage_exists(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            self._save_data({"corrections": [], "metadata": {"created_at": datetime.now().isoformat()}})
    
    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"corrections": [], "metadata": {"created_at": datetime.now().isoformat()}}
    
    def _save_data(self, data: Dict[str, Any]) -> None:
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def add_correction(
        self,
        field_name: str,
        original_value: str,
        corrected_value: str,
        resume_id: Optional[int] = None,
        comment: str = ""
    ) -> str:
        data = self._load_data()
        
        correction_id = f"corr_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        correction = {
            "id": correction_id,
            "field_name": field_name,
            "original_value": original_value,
            "corrected_value": corrected_value,
            "resume_id": resume_id,
            "comment": comment,
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        
        data["corrections"].append(correction)
        self._save_data(data)
        
        logger.info(f"Permanent correction added: {correction_id} for field '{field_name}'")
        return correction_id
    
    def get_corrections(self, field_name: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._load_data()
        
        corrections = data.get("corrections", [])
        
        
        if field_name:
            corrections = [c for c in corrections if c.get("field_name") == field_name]
        
        
        corrections = [c for c in corrections if c.get("active", True)]
        
        return corrections
    
    def get_corrections_dict(self, field_name: Optional[str] = None) -> Dict[str, str]:
        corrections = self.get_corrections(field_name)
        
        result = {}
        for correction in corrections:
            original = correction.get("original_value", "")
            corrected = correction.get("corrected_value", "")
            if original and corrected:
                result[original.lower()] = corrected
        
        return result
    
    def delete_correction(self, correction_id: str) -> bool:
        data = self._load_data()
        
        for correction in data.get("corrections", []):
            if correction.get("id") == correction_id:
                correction["active"] = False
                correction["deleted_at"] = datetime.now().isoformat()
                self._save_data(data)
                logger.info(f"Correction deleted: {correction_id}")
                return True
        
        return False
    
    def delete_correction_by_values(
        self,
        field_name: str,
        original_value: str
    ) -> bool:
        data = self._load_data()
        
        for correction in data.get("corrections", []):
            if (correction.get("field_name") == field_name and 
                correction.get("original_value") == original_value and
                correction.get("active", True)):
                correction["active"] = False
                correction["deleted_at"] = datetime.now().isoformat()
                self._save_data(data)
                logger.info(f"Correction deleted for '{field_name}': '{original_value}'")
                return True
        
        return False
    
    def clear_corrections(self, field_name: Optional[str] = None) -> int:
        data = self._load_data()
        
        count = 0
        for correction in data.get("corrections", []):
            if field_name is None or correction.get("field_name") == field_name:
                if correction.get("active", True):
                    correction["active"] = False
                    correction["deleted_at"] = datetime.now().isoformat()
                    count += 1
        
        if count > 0:
            self._save_data(data)
            logger.info(f"Cleared {count} corrections" + (f" for field '{field_name}'" if field_name else ""))
        
        return count
    
    def get_statistics(self) -> Dict[str, Any]:
        data = self._load_data()
        
        corrections = data.get("corrections", [])
        active_corrections = [c for c in corrections if c.get("active", True)]
        
        field_counts = {}
        for correction in active_corrections:
            field = correction.get("field_name", "unknown")
            field_counts[field] = field_counts.get(field, 0) + 1
        
        return {
            "total_corrections": len(corrections),
            "active_corrections": len(active_corrections),
            "by_field": field_counts,
            "storage_path": self.storage_path
        }
    
    def update_correction(
        self,
        correction_id: str,
        corrected_value: str = None,
        comment: str = None
    ) -> bool:
        data = self._load_data()
        
        for correction in data.get("corrections", []):
            if correction.get("id") == correction_id:
                if corrected_value is not None:
                    correction["corrected_value"] = corrected_value
                if comment is not None:
                    correction["comment"] = comment
                correction["updated_at"] = datetime.now().isoformat()
                self._save_data(data)
                logger.info(f"Correction updated: {correction_id}")
                return True
        
        return False



_correction_storage = None


def get_correction_storage() -> CorrectionStorage:
    global _correction_storage
    if _correction_storage is None:
        _correction_storage = CorrectionStorage()
    return _correction_storage
