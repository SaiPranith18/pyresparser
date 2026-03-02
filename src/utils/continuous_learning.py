import os
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field, asdict

from flask import Flask

logger = logging.getLogger(__name__)


@dataclass
class LearningSample:
    resume_id: int
    field_name: str
    original_extraction: str
    corrected_extraction: str
    correction_feedback: str = ""
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "pending"  


@dataclass
class ModelMetrics:
    model_name: str
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    training_samples: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class ContinuousLearning:
    
    
    AUTO_RETRAIN_THRESHOLD = 100  
    MIN_CONFIDENCE_IMPROVEMENT = 0.05  
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.db = None
        self._initialized = False
        
    def init_app(self, app: Flask):
        self.app = app
        self.db = app.extensions.get('sqlalchemy')
        self._initialized = True
        logger.info("Continuous Learning module initialized")
        
    def collect_feedback(
        self,
        resume_id: int,
        field_name: str,
        original_extraction: str,
        corrected_extraction: str,
        confidence_before: float,
        correction_feedback: str = ""
    ) -> bool:
        try:
            
            
            confidence_after = min(confidence_before + 0.1, 1.0) if original_extraction != corrected_extraction else confidence_before
            
            
            sample = LearningSample(
                resume_id=resume_id,
                field_name=field_name,
                original_extraction=original_extraction,
                corrected_extraction=corrected_extraction,
                correction_feedback=correction_feedback,
                confidence_before=confidence_before,
                confidence_after=confidence_after,
                timestamp=datetime.now(),
                status="pending"
            )
            
            
            self._store_learning_sample(sample)
            
            logger.info(f"Feedback collected for field '{field_name}' on resume {resume_id}")
            
            
            if self._should_trigger_retraining():
                logger.info("Retraining threshold reached. Consider triggering model retraining.")
                
            return True
            
        except Exception as e:
            logger.error(f"Error collecting feedback: {e}")
            return False
    
    def _store_learning_sample(self, sample: LearningSample) -> None:
        
        
        self._store_sample_json(sample)
        
    def _store_sample_json(self, sample: LearningSample) -> None:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'learning_data')
        os.makedirs(storage_dir, exist_ok=True)
        
        
        filename = f"sample_{sample.timestamp.strftime('%Y%m%d_%H%M%S_%f')}.json"
        filepath = os.path.join(storage_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(asdict(sample), f, default=str)
            
    def _should_trigger_retraining(self) -> bool:
        approved_count = self._get_approved_samples_count()
        return approved_count >= self.AUTO_RETRAIN_THRESHOLD
    
    def _get_approved_samples_count(self) -> int:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'learning_data')
        
        if not os.path.exists(storage_dir):
            return 0
            
        count = 0
        for filename in os.listdir(storage_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(storage_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if data.get('status') == 'approved':
                            count += 1
                except:
                    pass
        return count
    
    def get_pending_corrections(self) -> List[Dict[str, Any]]:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        storage_dirs = [
            os.path.join(base_dir, 'learning_data'),
            os.path.join(base_dir, 'learning_data', 'feedback')
        ]
        
        corrections = []
        
        for storage_dir in storage_dirs:
            if not os.path.exists(storage_dir):
                continue
                
            for filename in os.listdir(storage_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(storage_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            # Check both 'status' and 'processed' fields
                            is_pending = data.get('status') == 'pending' or data.get('processed') == False
                            if is_pending:
                                # Add sample_id for consistency
                                data['sample_id'] = filename.replace('.json', '')
                                corrections.append(data)
                    except Exception as e:
                        logger.debug(f"Error reading {filename}: {e}")
        return corrections
    
    def approve_correction(self, sample_id: str) -> bool:
        return self._update_sample_status(sample_id, "approved")
    
    def reject_correction(self, sample_id: str, reason: str = "") -> bool:
        return self._update_sample_status(sample_id, "rejected")
    
    def _update_sample_status(self, sample_id: str, status: str) -> bool:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        storage_dirs = [
            os.path.join(base_dir, 'learning_data'),
            os.path.join(base_dir, 'learning_data', 'feedback')
        ]
        
        logger.info(f"_update_sample_status called with sample_id: {sample_id}, status: {status}")
        
        for storage_dir in storage_dirs:
            if not os.path.exists(storage_dir):
                logger.info(f"Storage dir does not exist: {storage_dir}")
                continue
            
            logger.info(f"Checking storage dir: {storage_dir}")
            
            for filename in os.listdir(storage_dir):
                if filename.endswith('.json') and (filename.startswith('sample_') or filename.startswith('fb_')):
                    filepath = os.path.join(storage_dir, filename)
                    file_id = filename.replace('.json', '')
                    logger.info(f"Comparing sample_id '{sample_id}' with filename '{file_id}'")
                    
                    if sample_id == file_id or sample_id in filename:
                        try:
                            with open(filepath, 'r') as f:
                                data = json.load(f)
                            
                            data['status'] = status
                            if 'processed' in data:
                                data['processed'] = True
                            with open(filepath, 'w') as f:
                                json.dump(data, f, default=str)
                            logger.info(f"Updated {filename} status to {status}")
                            return True
                        except Exception as e:
                            logger.debug(f"Error updating {filename}: {e}")
        
        logger.warning(f"No matching file found for sample_id: {sample_id}")
        return False
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'learning_data')
        
        stats = {
            "total_samples": 0,
            "pending_samples": 0,
            "approved_samples": 0,
            "rejected_samples": 0,
            "fields": {},
            "ready_for_retraining": False
        }
        
        if not os.path.exists(storage_dir):
            return stats
            
        field_counts = {}
        
        for filename in os.listdir(storage_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(storage_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        stats['total_samples'] += 1
                        
                        status = data.get('status', 'pending')
                        if status == 'pending':
                            stats['pending_samples'] += 1
                        elif status == 'approved':
                            stats['approved_samples'] += 1
                        elif status == 'rejected':
                            stats['rejected_samples'] += 1
                            
                        field = data.get('field_name', 'unknown')
                        field_counts[field] = field_counts.get(field, 0) + 1
                        
                except:
                    pass
                    
        stats['fields'] = field_counts
        stats['ready_for_retraining'] = self._should_trigger_retraining()
        
        return stats
    
    def apply_corrections_to_extraction_rules(self, field_name: str) -> Dict[str, Any]:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'learning_data')
        
        patterns = {
            "common_mistakes": [],
            "suggested_keywords": [],
            "suggested_patterns": []
        }
        
        if not os.path.exists(storage_dir):
            return patterns
            
        for filename in os.listdir(storage_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(storage_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        
                    if data.get('field_name') == field_name and data.get('status') == 'approved':
                        original = data.get('original_extraction', '')
                        corrected = data.get('corrected_extraction', '')
                        
                        if original != corrected:
                            patterns["common_mistakes"].append({
                                "original": original[:100],
                                "corrected": corrected[:100]
                            })
                            
                except:
                    pass
                    
        return patterns
    
    def generate_training_data(
        self,
        field_name: Optional[str] = None,
        min_samples: int = 10
    ) -> List[Dict[str, Any]]:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'learning_data')
        
        training_data = []
        
        if not os.path.exists(storage_dir):
            return training_data
            
        for filename in os.listdir(storage_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(storage_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        
                    if data.get('status') == 'approved':
                        if field_name is None or data.get('field_name') == field_name:
                            training_data.append({
                                "input": data.get('original_extraction', ''),
                                "output": data.get('corrected_extraction', ''),
                                "field": data.get('field_name', ''),
                                "feedback": data.get('correction_feedback', '')
                            })
                            
                except:
                    pass
                    
        
        if len(training_data) >= min_samples:
            return training_data
        return []



_continuous_learning = None


def get_continuous_learning(app: Optional[Flask] = None) -> ContinuousLearning:
    global _continuous_learning
    if _continuous_learning is None:
        _continuous_learning = ContinuousLearning(app)
    return _continuous_learning


def init_continuous_learning(app: Flask) -> None:
    learning = get_continuous_learning(app)
    learning.init_app(app)
