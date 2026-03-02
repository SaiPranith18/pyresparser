import os
import json
import logging
import hashlib
import random
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


try:
    import spacy
    from spacy.training import Example
    import srsly
    SPACY_AVAILABLE = True
except ImportError:
    logger.warning("spaCy not available")
    spacy = None
    Example = None
    srsly = None
    SPACY_AVAILABLE = False

try:
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForTokenClassification,
        AutoModelForSequenceClassification,
        TrainingArguments, Trainer
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("Transformers not available")
    torch = None
    TRANSFORMERS_AVAILABLE = False


@dataclass
class TrainingConfig:
    model_type: str = "spacy"  
    base_model: str = "en_core_web_sm"
    epochs: int = 10
    batch_size: int = 8
    learning_rate: float = 5e-5
    output_dir: str = "./models"
    field: str = "general"
    

@dataclass
class TrainingJob:
    job_id: str
    config: TrainingConfig
    status: str = "pending"  
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    error_message: str = ""


class ModelTrainer:
    
    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            models_dir = os.path.join(base_dir, 'models')
        
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.active_jobs: Dict[str, TrainingJob] = {}
        
    def is_spacy_available(self) -> bool:
        return SPACY_AVAILABLE
    
    def is_transformers_available(self) -> bool:
        return TRANSFORMERS_AVAILABLE
    
    def create_training_job(
        self,
        config: TrainingConfig
    ) -> str:
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        job_id = f"train_{timestamp}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]}"
        
        job = TrainingJob(
            job_id=job_id,
            config=config,
            status="pending"
        )
        
        self.active_jobs[job_id] = job
        logger.info(f"Created training job: {job_id}")
        
        return job_id
    
    def train_spacy_ner(
        self,
        training_data: List[Tuple[str, Dict[str, Any]]],
        config: TrainingConfig
    ) -> Tuple[bool, str]:
        if not SPACY_AVAILABLE:
            return False, "spaCy not available"
        
        try:
            
            if config.base_model and os.path.exists(config.base_model):
                nlp = spacy.load(config.base_model)
            else:
                nlp = spacy.blank("en")
            
            
            if "ner" not in nlp.pipe_names:
                nlp.add_pipe("ner")
            
            ner = nlp.get_pipe("ner")
            
            
            labels = set()
            for text, annotations in training_data:
                for ent in annotations.get("entities", []):
                    labels.add(ent[2])
            
            for label in labels:
                ner.add_label(label)
            
            
            n_iter = config.epochs
            
            
            other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
            with nlp.disable_pipes(*other_pipes):
                optimizer = nlp.begin_training()
                
                for epoch in range(n_iter):
                    random.shuffle(training_data)
                    losses = {}
                    
                    for text, annotations in training_data:
                        doc = nlp.make_doc(text)
                        example = Example.from_dict(doc, annotations)
                        nlp.update([example], sgd=optimizer, losses=losses)
                    
                    logger.info(f"Epoch {epoch + 1}/{n_iter}, Loss: {losses.get('ner', 0)}")
            
            
            model_name = f"{config.field}_ner_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_path = os.path.join(self.models_dir, model_name)
            nlp.to_disk(output_path)
            
            logger.info(f"Model saved to {output_path}")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error training spaCy model: {e}")
            return False, str(e)
    
    def train_spacy_textcat(
        self,
        training_data: List[Tuple[str, Dict[str, Any]]],
        config: TrainingConfig,
        categories: List[str]
    ) -> Tuple[bool, str]:
        if not SPACY_AVAILABLE:
            return False, "spaCy not available"
        
        try:
            
            if config.base_model and os.path.exists(config.base_model):
                nlp = spacy.load(config.base_model)
            else:
                nlp = spacy.blank("en")
            
            
            if "textcat" not in nlp.pipe_names:
                nlp.add_pipe("textcat", config={"categories": categories})
            
            textcat = nlp.get_pipe("textcat")
            
            
            n_iter = config.epochs
            
            other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "textcat"]
            with nlp.disable_pipes(*other_pipes):
                optimizer = nlp.begin_training()
                
                for epoch in range(n_iter):
                    random.shuffle(training_data)
                    losses = {}
                    
                    for text, annotations in training_data:
                        doc = nlp.make_doc(text)
                        example = Example.from_dict(doc, annotations)
                        nlp.update([example], sgd=optimizer, losses=losses)
                    
                    logger.info(f"Epoch {epoch + 1}/{n_iter}, Loss: {losses.get('textcat', 0)}")
            
            
            model_name = f"{config.field}_textcat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_path = os.path.join(self.models_dir, model_name)
            nlp.to_disk(output_path)
            
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error training spaCy textcat model: {e}")
            return False, str(e)
    
    def train_transformer(
        self,
        training_data: List[Tuple[str, int]],
        config: TrainingConfig,
        num_labels: int = 2
    ) -> Tuple[bool, str]:
        if not TRANSFORMERS_AVAILABLE:
            return False, "Transformers not available"
        
        try:
            
            tokenizer = AutoTokenizer.from_pretrained(config.base_model)
            model = AutoModelForSequenceClassification.from_pretrained(
                config.base_model,
                num_labels=num_labels
            )
            
            
            texts, labels = zip(*training_data)
            encodings = tokenizer(
                list(texts),
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors="pt"
            )
            
            class Dataset(torch.utils.data.Dataset):
                def __init__(self, encodings, labels):
                    self.encodings = encodings
                    self.labels = labels
                    
                def __getitem__(self, idx):
                    item = {key: val[idx] for key, val in self.encodings.items()}
                    item['labels'] = torch.tensor(self.labels[idx])
                    return item
                    
                def __len__(self):
                    return len(self.labels)
            
            dataset = Dataset(encodings, labels)
            
            
            output_dir = os.path.join(
                config.output_dir,
                f"transformer_{config.field}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=config.epochs,
                per_device_train_batch_size=config.batch_size,
                learning_rate=config.learning_rate,
                logging_dir=os.path.join(output_dir, "logs"),
                logging_steps=10,
                save_steps=100,
                save_total_limit=2
            )
            
            
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=dataset
            )
            
            
            trainer.train()
            
            
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
            
            logger.info(f"Transformer model saved to {output_dir}")
            return True, output_dir
            
        except Exception as e:
            logger.error(f"Error training transformer model: {e}")
            return False, str(e)
    
    def run_training_job(self, job_id: str) -> bool:
        if job_id not in self.active_jobs:
            logger.error(f"Job not found: {job_id}")
            return False
            
        job = self.active_jobs[job_id]
        job.status = "running"
        job.start_time = datetime.now()
        
        try:
            
            from src.training.data_preparator import get_data_preparator
            preparator = get_data_preparator()
            
            
            result = preparator.prepare_for_training(
                job.config.field,
                min_examples=10
            )
            
            if result is None:
                job.status = "failed"
                job.error_message = "Insufficient training data"
                return False
            
            train, val, test = result
            
            
            if job.config.model_type == "spacy":
                
                training_data = []
                for ex in train:
                    annotations = {
                        "entities": []  
                    }
                    training_data.append((ex.input_text, annotations))
                
                success, result_path = self.train_spacy_ner(
                    training_data, job.config
                )
            else:
                
                training_data = [(ex.input_text, 1 if ex.output_text else 0) for ex in train]
                success, result_path = self.train_transformer(
                    training_data, job.config
                )
            
            if success:
                job.status = "completed"
                job.progress = 100.0
                job.metrics = {"model_path": result_path}
            else:
                job.status = "failed"
                job.error_message = result_path
                
            job.end_time = datetime.now()
            return success
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.end_time = datetime.now()
            logger.error(f"Error running training job {job_id}: {e}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        if job_id not in self.active_jobs:
            return None
            
        job = self.active_jobs[job_id]
        return {
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "metrics": job.metrics,
            "error_message": job.error_message,
            "config": asdict(job.config)
        }
    
    def cancel_job(self, job_id: str) -> bool:
        if job_id not in self.active_jobs:
            return False
            
        job = self.active_jobs[job_id]
        if job.status == "running":
            job.status = "cancelled"
            job.end_time = datetime.now()
            return True
        return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        models = []
        
        if not os.path.exists(self.models_dir):
            return models
            
        for model_name in os.listdir(self.models_dir):
            model_path = os.path.join(self.models_dir, model_name)
            if os.path.isdir(model_path):
                
                info_file = os.path.join(model_path, "meta.json")
                if os.path.exists(info_file):
                    with open(info_file, 'r') as f:
                        info = json.load(f)
                else:
                    info = {"name": model_name}
                    
                info["path"] = model_path
                info["created"] = datetime.fromtimestamp(
                    os.path.getctime(model_path)
                ).isoformat()
                
                models.append(info)
        
        return models
    
    def load_model(self, model_path: str) -> Optional[Any]:
        if not os.path.exists(model_path):
            return None
            
        try:
            if "ner" in model_path or "spacy" in model_path.lower():
                return spacy.load(model_path)
            else:
                
                return None
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
    
    def evaluate_model(
        self,
        model_path: str,
        test_data: List[Tuple[str, Dict[str, Any]]]
    ) -> Dict[str, float]:
        nlp = self.load_model(model_path)
        if nlp is None:
            return {"error": "Could not load model"}
        
        correct = 0
        total = 0
        
        for text, expected in test_data:
            doc = nlp(text)
            
            total += 1
            
        accuracy = correct / total if total > 0 else 0
        
        return {
            "accuracy": accuracy,
            "total_samples": total,
            "correct_predictions": correct
        }



_model_trainer = None


def get_model_trainer() -> ModelTrainer:
    global _model_trainer
    if _model_trainer is None:
        _model_trainer = ModelTrainer()
    return _model_trainer
