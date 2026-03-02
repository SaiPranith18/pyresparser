import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEntry:
    resume_id: int
    field_name: str
    original_value: str
    corrected_value: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    feedback_type: str = "correction"  
    comment: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    processed: bool = False


class FeedbackCollector:
    
    def __init__(self, storage_path: Optional[str] = None):
        
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            storage_path = os.path.join(base_dir, 'learning_data', 'feedback')
        
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)
        print("Feedback storage path:", self.storage_path)
        
    def add_correction(
        self,
        resume_id: int,
        field_name: str,
        original_value: str,
        corrected_value: str,
        user_id: Optional[str] = None,
        comment: str = ""
    ) -> str:
        entry = FeedbackEntry(
            resume_id=resume_id,
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            user_id=user_id,
            feedback_type="correction",
            comment=comment,
            timestamp=datetime.now(),
            processed=False
        )
        
        return self._save_feedback(entry)
        
    def add_confirmation(
        self,
        resume_id: int,
        field_name: str,
        value: str,
        user_id: Optional[str] = None
    ) -> str:
        entry = FeedbackEntry(
            resume_id=resume_id,
            field_name=field_name,
            original_value=value,
            corrected_value=value,  
            user_id=user_id,
            feedback_type="confirmation",
            timestamp=datetime.now(),
            processed=False
        )
        
        return self._save_feedback(entry)
        
    def add_rejection(
        self,
        resume_id: int,
        field_name: str,
        value: str,
        reason: str = "",
        user_id: Optional[str] = None
    ) -> str:
        entry = FeedbackEntry(
            resume_id=resume_id,
            field_name=field_name,
            original_value=value,
            corrected_value="",  
            user_id=user_id,
            feedback_type="rejection",
            comment=reason,
            timestamp=datetime.now(),
            processed=False
        )
        
        return self._save_feedback(entry)
    
    def _save_feedback(self, entry: FeedbackEntry) -> str:
        
        feedback_id = f"fb_{entry.timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
        
        filepath = os.path.join(self.storage_path, f"{feedback_id}.json")
        
        with open(filepath, 'w') as f:
            json.dump(asdict(entry), f, default=str)
            
        logger.info(f"Feedback saved: {feedback_id} for field '{entry.field_name}'")
        
        return feedback_id
    
    def get_feedback_by_resume(self, resume_id: int) -> List[Dict[str, Any]]:
        feedback_list = []
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.storage_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if data.get('resume_id') == resume_id:
                            feedback_list.append(data)
                except:
                    pass
                    
        return feedback_list
    
    def get_feedback_by_field(self, field_name: str) -> List[Dict[str, Any]]:
        feedback_list = []
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.storage_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if data.get('field_name') == field_name:
                            feedback_list.append(data)
                except:
                    pass
                    
        return feedback_list
    
    def get_unprocessed_feedback(self) -> List[Dict[str, Any]]:
        feedback_list = []
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.storage_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if not data.get('processed', False):
                            feedback_list.append(data)
                except:
                    pass
                    
        return feedback_list
    
    def mark_as_processed(self, feedback_id: str) -> bool:
        filepath = os.path.join(self.storage_path, f"{feedback_id}.json")
        
        if not os.path.exists(filepath):
            return False
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            data['processed'] = True
            
            with open(filepath, 'w') as f:
                json.dump(data, f, default=str)
                
            return True
        except:
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            "total": 0,
            "corrections": 0,
            "confirmations": 0,
            "rejections": 0,
            "processed": 0,
            "unprocessed": 0,
            "by_field": {}
        }
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.storage_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        stats['total'] += 1
                        
                        fb_type = data.get('feedback_type', 'correction')
                        if fb_type == 'correction':
                            stats['corrections'] += 1
                        elif fb_type == 'confirmation':
                            stats['confirmations'] += 1
                        elif fb_type == 'rejection':
                            stats['rejections'] += 1
                            
                        if data.get('processed', False):
                            stats['processed'] += 1
                        else:
                            stats['unprocessed'] += 1
                            
                        field = data.get('field_name', 'unknown')
                        if field not in stats['by_field']:
                            stats['by_field'][field] = 0
                        stats['by_field'][field] += 1
                        
                except:
                    pass
                    
        return stats
    
    def export_training_data(
        self,
        field_name: Optional[str] = None,
        feedback_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        if feedback_types is None:
            feedback_types = ['correction', 'rejection']
            
        training_data = []
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.storage_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        
                    
                    if field_name and data.get('field_name') != field_name:
                        continue
                        
                    if data.get('feedback_type') not in feedback_types:
                        continue
                        
                    
                    if data.get('feedback_type') in ['correction', 'rejection']:
                        training_data.append({
                            "input": data.get('original_value', ''),
                            "output": data.get('corrected_value', ''),
                            "field": data.get('field_name', ''),
                            "type": data.get('feedback_type', ''),
                            "comment": data.get('comment', '')
                        })
                        
                except:
                    pass
                    
        return training_data



_feedback_collector = None


def get_feedback_collector() -> FeedbackCollector:
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector
