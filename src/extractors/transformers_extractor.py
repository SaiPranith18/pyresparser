
import re
import logging
from typing import Dict, Tuple, List, Optional, Any


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_TRANSFORMERS_AVAILABLE = None
_ner_model = None
_tokenizer = None


def is_transformers_available() -> bool:
    global _TRANSFORMERS_AVAILABLE
    if _TRANSFORMERS_AVAILABLE is None:
        try:
            import transformers
            _TRANSFORMERS_AVAILABLE = True
        except ImportError:
            _TRANSFORMERS_AVAILABLE = False
    return _TRANSFORMERS_AVAILABLE


def load_ner_model():
    global _ner_model, _tokenizer
    
    if not is_transformers_available():
        return None, None
    
    if _ner_model is None:
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
            
            logger.info("Loading NER model...")
            _tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
            _ner_model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")
            logger.info("NER model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load NER model: {e}")
            return None, None
    
    return _ner_model, _tokenizer


class TransformerExtractor:
    
    def __init__(self):
        self.available = is_transformers_available()
        self.ner_pipeline = None
    
    def initialize(self):
        if not self.available:
            logger.warning("Transformers not available")
            return False
        
        if self.ner_pipeline is None:
            try:
                from transformers import pipeline
                self.ner_pipeline = pipeline(
                    "ner", 
                    model="dslim/bert-base-NER",
                    aggregation_strategy="simple"
                )
                logger.info("NER pipeline initialized")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize NER pipeline: {e}")
                return False
        return True
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        if not self.initialize():
            return {}
        
        try:
            entities = self.ner_pipeline(text[:512])  
            
            result = {
                "PERSON": [],
                "ORG": [],
                "LOC": [],
                "DATE": [],
                "MISC": []
            }
            
            for entity in entities:
                entity_group = entity.get("entity_group", entity.get("entity_type"))
                if entity_group in result:
                    word = entity.get("word", "")
                    if word not in result[entity_group]:
                        result[entity_group].append(word)
            
            return result
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {}
    
    def extract_names_ner(self, text: str) -> List[str]:
        entities = self.extract_entities(text)
        return entities.get("PERSON", [])
    
    def extract_orgs_ner(self, text: str) -> List[str]:
        entities = self.extract_entities(text)
        return entities.get("ORG", [])
    
    def extract_locations_ner(self, text: str) -> List[str]:
        entities = self.extract_entities(text)
        return entities.get("LOC", [])
    
    def extract_dates_ner(self, text: str) -> List[str]:
        entities = self.extract_entities(text)
        return entities.get("DATE", [])



_transformer_extractor = None


def get_transformer_extractor() -> TransformerExtractor:
    global _transformer_extractor
    if _transformer_extractor is None:
        _transformer_extractor = TransformerExtractor()
    return _transformer_extractor




def extract_name_with_transformers(text: str, fallback_name: str = "", fallback_confidence: float = 0.0) -> Tuple[str, float]:
    if not is_transformers_available():
        return fallback_name, fallback_confidence
    
    try:
        extractor = get_transformer_extractor()
        names = extractor.extract_names_ner(text)
        
        if names:
            
            for name in names:
                if len(name) > 3:  
                    
                    confidence = min(fallback_confidence * 1.3, 1.0) if fallback_confidence > 0 else 0.85
                    return name, round(confidence, 2)
        
        logger.info("No name found with transformers, using fallback")
        return fallback_name, fallback_confidence
        
    except Exception as e:
        logger.error(f"Error in transformer name extraction: {e}")
        return fallback_name, fallback_confidence


def extract_education_with_transformers(text: str) -> Dict[str, Any]:
    if not is_transformers_available():
        return {}
    
    try:
        extractor = get_transformer_extractor()
        
        
        orgs = extractor.extract_orgs_ner(text)
        universities = [org for org in orgs if any(
            keyword in org.lower() for keyword in 
            ['university', 'college', 'institute', 'school', 'academy']
        )]
        
        
        dates = extractor.extract_dates_ner(text)
        years = [d for d in dates if re.match(r'^(19|20)\d{2}$', d)]
        
        return {
            "universities": universities,
            "years": years
        }
    except Exception as e:
        logger.error(f"Error in transformer education extraction: {e}")
        return {}


def extract_companies_with_transformers(text: str) -> List[str]:
    if not is_transformers_available():
        return []
    
    try:
        extractor = get_transformer_extractor()
        orgs = extractor.extract_orgs_ner(text)
        
        
        companies = [org for org in orgs if len(org) > 2]
        return companies
    except Exception as e:
        logger.error(f"Error in transformer company extraction: {e}")
        return []




def calculate_text_similarity(text1: str, text2: str) -> float:
    if not is_transformers_available():
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1.intersection(words2)) / len(words1.union(words2))
    
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        embeddings = model.encode([text1, text2])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1.intersection(words2)) / len(words1.union(words2))




class EnsembleConfidenceScorer:
    
    def __init__(self):
        self.transformer_available = is_transformers_available()
    
    def calculate_ensemble_confidence(
        self,
        regex_confidence: float,
        nlp_confidence: float,
        transformer_confidence: float = 0.0,
        layoutlm_confidence: float = 0.0
    ) -> Tuple[float, str]:
        
        scores = []
        
        if regex_confidence > 0:
            scores.append((regex_confidence, 0.25, "regex"))
        
        if nlp_confidence > 0:
            scores.append((nlp_confidence, 0.30, "nlp"))
        
        if transformer_confidence > 0:
            scores.append((transformer_confidence, 0.40, "transformer"))
        
        if layoutlm_confidence > 0:
            scores.append((layoutlm_confidence, 0.35, "layoutlm"))
        
        if not scores:
            return 0.0, "none"
        
        
        total_weight = sum(w for _, w, _ in scores)
        weighted_sum = sum(score * weight for score, weight, _ in scores)
        
        ensemble_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        
        best_method = max(scores, key=lambda x: x[0])[2] if scores else "none"
        
        
        if len(scores) >= 2:
            avg_score = sum(s for s, _, _ in scores) / len(scores)
            if abs(ensemble_confidence - avg_score) < 0.15:
                
                ensemble_confidence = min(ensemble_confidence * 1.1, 1.0)
        
        return round(ensemble_confidence, 2), best_method
    
    def calculate_cross_validation_score(
        self,
        extracted_text: str,
        original_text: str,
        section_type: str
    ) -> float:
        if not extracted_text or not original_text:
            return 0.0
        
        
        extracted_words = set(extracted_text.lower().split())
        original_words = set(original_text.lower().split())
        
        if not extracted_words:
            return 0.0
        
        overlap = len(extracted_words.intersection(original_words))
        overlap_ratio = overlap / len(extracted_words)
        
        
        validation_boost = 0.0
        
        if section_type == "skills":
            
            skill_keywords = ['python', 'java', 'javascript', 'react', 'angular', 'vue', 
                            'node', 'django', 'flask', 'aws', 'azure', 'gcp', 'docker']
            if any(skill in extracted_text.lower() for skill in skill_keywords):
                validation_boost = 0.1
        
        elif section_type == "education":
            
            edu_keywords = ['bachelor', 'master', 'phd', 'university', 'college', 'degree']
            if any(keyword in extracted_text.lower() for keyword in edu_keywords):
                validation_boost = 0.1
        
        elif section_type == "experience":
            
            exp_keywords = ['company', 'engineer', 'developer', 'manager', 'experience', 'years']
            if any(keyword in extracted_text.lower() for keyword in exp_keywords):
                validation_boost = 0.1
        
        final_score = min(overlap_ratio + validation_boost, 1.0)
        return round(final_score, 2)



_ensemble_scorer = None


def get_ensemble_scorer() -> EnsembleConfidenceScorer:
    global _ensemble_scorer
    if _ensemble_scorer is None:
        _ensemble_scorer = EnsembleConfidenceScorer()
    return _ensemble_scorer


if __name__ == "__main__":
    
    print("Transformers available:", is_transformers_available())
    
    
    scorer = get_ensemble_scorer()
    confidence, method = scorer.calculate_ensemble_confidence(
        regex_confidence=0.7,
        nlp_confidence=0.8,
        transformer_confidence=0.9,
        layoutlm_confidence=0.75
    )
    print(f"Ensemble confidence: {confidence}, method: {method}")
    
    
    validation = scorer.calculate_cross_validation_score(
        "Python JavaScript React",
        "Experienced in Python, JavaScript, React and Node.js",
        "skills"
    )
    print(f"Validation score: {validation}")
