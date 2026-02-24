import os
import io
import logging
from typing import Tuple, Dict, Any, List, Optional


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


try:
    from transformers import LayoutLMv3Processor, LayoutLMv3ForQuestionAnswering, LayoutLMv3TokenizerFast, LayoutLMv3FeatureExtractor
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Transformers not available: {e}. LayoutLMv3 extraction will use fallback method.")
    TRANSFORMERS_AVAILABLE = False
    torch = None


try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None


class LayoutLMv3Extractor:
    
    
    MODEL_NAME = "microsoft/layoutlmv3-base"
    
    
    SECTION_QUESTIONS = {
        "name": "What is the candidate's full name?",
        "email": "What is the candidate's email address?",
        "phone": "What is the candidate's phone number?",
        "summary": "What is the professional summary or objective?",
        "skills": "What are the technical skills and competencies?",
        "education": "What is the educational background and qualifications?",
        "experience": "What is the work experience and employment history?",
        "projects": "What are the projects mentioned?",
        "certifications": "What certifications has the candidate earned?",
        "languages": "What languages does the candidate know?"
    }
    
    def __init__(self, model_path: Optional[str] = None, use_gpu: bool = True):
        self.model = None
        self.processor = None
        self.feature_extractor = None
        self.tokenizer = None
        self.device = None
        self.model_path = model_path or self.MODEL_NAME
        self.use_gpu = use_gpu and TRANSFORMERS_AVAILABLE
        
        if TRANSFORMERS_AVAILABLE:
            self._initialize_model()
        else:
            logger.warning("LayoutLMv3 model not loaded. Install transformers to enable.")
    
    def _initialize_model(self):
        try:
            logger.info(f"Loading LayoutLMv3 model: {self.model_path}")
            
            
            if self.use_gpu and torch.cuda.is_available():
                self.device = torch.device("cuda")
                logger.info("Using GPU for LayoutLMv3")
            else:
                self.device = torch.device("cpu")
                logger.info("Using CPU for LayoutLMv3")
            
            
            self.processor = LayoutLMv3Processor.from_pretrained(self.model_path)
            
            
            self.model = LayoutLMv3ForQuestionAnswering.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("LayoutLMv3 model loaded successfully!")
            
        except Exception as e:
            logger.error(f"Error loading LayoutLMv3 model: {e}")
            self.model = None
            self.processor = None
    
    def is_available(self) -> bool:
        return self.model is not None and self.processor is not None
    
    def extract_from_image(self, image_path: str) -> Dict[str, Any]:
        if not self.is_available():
            return {"error": "LayoutLMv3 model not available"}
        
        if not PIL_AVAILABLE:
            return {"error": "PIL not available"}
        
        try:
            
            image = Image.open(image_path).convert("rgb")
            
            results = {}
            
            
            for section, question in self.SECTION_QUESTIONS.items():
                answer = self._answer_question(image, question)
                if answer:
                    results[section] = answer
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting from image: {e}")
            return {"error": str(e)}
    
    def extract_from_pdf(self, pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
        if not self.is_available():
            return {"error": "LayoutLMv3 model not available"}
        
        if not PIL_AVAILABLE:
            return {"error": "PIL not available"}
        
        try:
            
            import fitz  
            
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[page_num]
            
            
            zoom = 2  
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data)).convert("rgb")
            
            pdf_document.close()
            
            
            results = {}
            for section, question in self.SECTION_QUESTIONS.items():
                answer = self._answer_question(image, question)
                if answer:
                    results[section] = answer
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting from PDF: {e}")
            return {"error": str(e)}
    
    def _answer_question(self, image: Image.Image, question: str) -> Optional[str]:
        if not self.is_available():
            return None
        
        try:
            
            encoding = self.processor(
                question,
                image,
                max_length=512,
                truncation=True,
                padding="max_length",
                return_tensors="pt"
            )
            
            
            encoding = {k: v.to(self.device) for k, v in encoding.items()}
            
            
            with torch.no_grad():
                outputs = self.model(**encoding)
            
            
            start_logits = outputs.start_logits[0]
            end_logits = outputs.end_logits[0]
            
            start_idx = torch.argmax(start_logits)
            end_idx = torch.argmax(end_logits) + 1
            
            
            answer_tokens = encoding["input_ids"][0][start_idx:end_idx]
            
            
            answer = self.processor.decode(answer_tokens, skip_special_tokens=True)
            
            
            answer = answer.strip()
            
            if answer and len(answer) > 2:
                return answer
            
            return None
            
        except Exception as e:
            logger.debug(f"Error answering question '{question}': {e}")
            return None
    
    def extract_with_confidence(self, image_path: str) -> Tuple[Dict[str, Any], float]:
        if not self.is_available():
            return {"error": "LayoutLMv3 model not available"}, 0.0
        
        try:
            
            ext = os.path.splitext(image_path)[1].lower()
            
            if ext == '.pdf':
                results = self.extract_from_pdf(image_path)
            else:
                results = self.extract_from_image(image_path)
            
            
            valid_fields = sum(1 for v in results.values() if v and not isinstance(v, str) or (isinstance(v, str) and v))
            total_fields = len(self.SECTION_QUESTIONS)
            confidence = valid_fields / total_fields
            
            return results, round(confidence, 2)
            
        except Exception as e:
            logger.error(f"Error in extract_with_confidence: {e}")
            return {"error": str(e)}, 0.0
    
    def batch_extract(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        results = []
        
        for file_path in file_paths:
            logger.info(f"Processing: {file_path}")
            result = self.extract_with_confidence(file_path)
            results.append(result)
        
        return results



_extractor = None

def get_extractor() -> LayoutLMv3Extractor:
    global _extractor
    if _extractor is None:
        _extractor = LayoutLMv3Extractor()
    return _extractor


def extract_with_layoutlm(file_path: str) -> Tuple[Dict[str, Any], float]:
    extractor = get_extractor()
    return extractor.extract_with_confidence(file_path)


def is_layoutlm_available() -> bool:
    extractor = get_extractor()
    return extractor.is_available()


if __name__ == "__main__":
    
    print("LayoutLMv3 Resume Extractor")
    print("=" * 50)
    
    available = is_layoutlm_available()
    print(f"LayoutLMv3 Available: {available}")
    
    if available:
        print("\nModel loaded successfully!")
        print("You can now use extract_with_layoutlm() for better extraction.")
    else:
        print("\nPlease install required dependencies:")
        print("pip install transformers torch torchvision accelerate")
