import os
import json
import shutil
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ModelVersion:
    version_id: str
    model_name: str
    model_type: str  
    path: str
    created_at: datetime
    status: str = "staged"  
    metrics: Dict[str, float] = None
    config: Dict[str, Any] = None
    parent_version: Optional[str] = None
    description: str = ""


class ModelRegistry:
    
    def __init__(self, registry_dir: Optional[str] = None):
        if registry_dir is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            registry_dir = os.path.join(base_dir, 'models', 'registry')
        
        self.registry_dir = registry_dir
        os.makedirs(self.registry_dir, exist_ok=True)
        
    def _get_version_path(self, model_name: str) -> str:
        return os.path.join(self.registry_dir, f"{model_name}.json")
    
    def register_model(
        self,
        model_name: str,
        model_path: str,
        model_type: str,
        config: Dict[str, Any],
        metrics: Dict[str, float] = None,
        description: str = ""
    ) -> str:
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        version_id = f"v{timestamp}_{hashlib.md5(model_path.encode()).hexdigest()[:6]}"
        
        
        prev_version = self.get_latest_version(model_name)
        
        version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            model_type=model_type,
            path=model_path,
            created_at=datetime.now(),
            status="staged",
            metrics=metrics or {},
            config=config,
            parent_version=prev_version.version_id if prev_version else None,
            description=description
        )
        
        
        metadata_path = self._get_version_path(model_name)
        versions = self._load_versions(model_name)
        versions.append(asdict(version))
        
        with open(metadata_path, 'w') as f:
            json.dump({
                "model_name": model_name,
                "model_type": model_type,
                "versions": versions
            }, f, indent=2, default=str)
        
        logger.info(f"Registered model {model_name} version {version_id}")
        
        return version_id
    
    def _load_versions(self, model_name: str) -> List[Dict[str, Any]]:
        metadata_path = self._get_version_path(model_name)
        
        if not os.path.exists(metadata_path):
            return []
            
        with open(metadata_path, 'r') as f:
            data = json.load(f)
            return data.get('versions', [])
    
    def get_versions(self, model_name: str) -> List[ModelVersion]:
        versions_data = self._load_versions(model_name)
        
        versions = []
        for v in versions_data:
            v['created_at'] = datetime.fromisoformat(v['created_at'])
            versions.append(ModelVersion(**v))
            
        return versions
    
    def get_latest_version(self, model_name: str) -> Optional[ModelVersion]:
        versions = self.get_versions(model_name)
        
        if not versions:
            return None
            
        return versions[-1]
    
    def get_active_version(self, model_name: str) -> Optional[ModelVersion]:
        versions = self.get_versions(model_name)
        
        for v in reversed(versions):
            if v.status == "active":
                return v
                
        return None
    
    def deploy_version(
        self,
        model_name: str,
        version_id: str
    ) -> bool:
        versions = self._load_versions(model_name)
        
        for v in versions:
            if v['version_id'] == version_id:
                
                current_active = self.get_active_version(model_name)
                if current_active:
                    self._update_version_status(model_name, current_active.version_id, "archived")
                
                
                v['status'] = "active"
                
                
                metadata_path = self._get_version_path(model_name)
                with open(metadata_path, 'w') as f:
                    json.dump({
                        "model_name": model_name,
                        "model_type": v['model_type'],
                        "versions": versions
                    }, f, indent=2, default=str)
                    
                logger.info(f"Deployed {model_name} version {version_id}")
                return True
                
        return False
    
    def _update_version_status(
        self,
        model_name: str,
        version_id: str,
        status: str
    ) -> bool:
        versions = self._load_versions(model_name)
        
        for v in versions:
            if v['version_id'] == version_id:
                v['status'] = status
                
                metadata_path = self._get_version_path(model_name)
                with open(metadata_path, 'w') as f:
                    json.dump({
                        "model_name": model_name,
                        "model_type": v['model_type'],
                        "versions": versions
                    }, f, indent=2, default=str)
                return True
                
        return False
    
    def archive_version(
        self,
        model_name: str,
        version_id: str
    ) -> bool:
        return self._update_version_status(model_name, version_id, "archived")
    
    def delete_version(
        self,
        model_name: str,
        version_id: str
    ) -> bool:
        versions = self._load_versions(model_name)
        
        for i, v in enumerate(versions):
            if v['version_id'] == version_id:
                if v['status'] != 'staged':
                    logger.warning(f"Cannot delete non-staged version {version_id}")
                    return False
                    
                
                versions.pop(i)
                
                
                metadata_path = self._get_version_path(model_name)
                with open(metadata_path, 'w') as f:
                    json.dump({
                        "model_name": model_name,
                        "model_type": v['model_type'],
                        "versions": versions
                    }, f, indent=2, default=str)
                    
                logger.info(f"Deleted version {version_id}")
                return True
                
        return False
    
    def compare_versions(
        self,
        model_name: str,
        version_id_1: str,
        version_id_2: str
    ) -> Optional[Dict[str, Any]]:
        versions = self.get_versions(model_name)
        
        v1 = None
        v2 = None
        
        for v in versions:
            if v.version_id == version_id_1:
                v1 = v
            if v.version_id == version_id_2:
                v2 = v
                
        if not v1 or not v2:
            return None
            
        return {
            "version_1": asdict(v1),
            "version_2": asdict(v2),
            "differences": {
                "metrics_changed": v1.metrics != v2.metrics,
                "config_changed": v1.config != v2.config,
                "time_difference": (v2.created_at - v1.created_at).total_seconds()
            }
        }
    
    def rollback_to_version(
        self,
        model_name: str,
        version_id: str
    ) -> bool:
        return self.deploy_version(model_name, version_id)
    
    def list_models(self) -> List[Dict[str, Any]]:
        models = []
        
        for filename in os.listdir(self.registry_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.registry_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        
                    model_name = data.get('model_name')
                    versions = data.get('versions', [])
                    
                    
                    active = None
                    for v in versions:
                        if v.get('status') == 'active':
                            active = v.get('version_id')
                            
                    models.append({
                        "name": model_name,
                        "type": data.get('model_type'),
                        "version_count": len(versions),
                        "active_version": active,
                        "latest_version": versions[-1].get('version_id') if versions else None
                    })
                    
                except Exception as e:
                    logger.error(f"Error reading model metadata: {e}")
                    
        return models
    
    def get_model_for_inference(
        self,
        model_name: str
    ) -> Optional[Tuple[Any, str]]:
        active = self.get_active_version(model_name)
        
        if not active:
            
            active = self.get_latest_version(model_name)
            
        if not active:
            return None
            
        
        try:
            if active.model_type.startswith("spacy"):
                import spacy
                model = spacy.load(active.path)
                return model, active.version_id
            elif active.model_type == "transformer":
                
                from transformers import AutoModel
                model = AutoModel.from_pretrained(active.path)
                return model, active.version_id
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
            
        return None



_model_registry = None


def get_model_registry() -> ModelRegistry:
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry
