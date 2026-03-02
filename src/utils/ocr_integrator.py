import os
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


from src.utils.text import extract_text_from_pdf
from src.extractors.handwriting_extractor import (
    get_handwriting_extractor,
    is_handwriting_available,
    HandwritingExtractor
)
from src.utils.image_preprocessor import get_image_preprocessor


class OCRIntegrator:
    
    def __init__(self):
        self.handwriting_extractor = get_handwriting_extractor()
        self.image_preprocessor = get_image_preprocessor()
        self._ocr_available = is_handwriting_available()
        
    def is_available(self) -> bool:
        return self._ocr_available
    
    def extract_with_ocr_fallback(
        self,
        pdf_path: str,
        confidence_threshold: float = 0.7
    ) -> Tuple[str, float]:
        
        text, confidence = extract_text_from_pdf(pdf_path)
        
        
        if confidence >= confidence_threshold:
            return text, confidence
            
        
        if self._ocr_available:
            logger.info(f"Low confidence ({confidence}), attempting OCR enhancement")
            
            try:
                
                ocr_results = self.handwriting_extractor.extract_from_pdf(pdf_path)
                
                if ocr_results:
                    ocr_text = "\n".join([r.text for r in ocr_results])
                    
                    
                    
                    if len(ocr_text) > len(text):
                        combined_confidence = (confidence + 0.8) / 2
                        logger.info(f"OCR enhanced extraction (confidence: {combined_confidence})")
                        return ocr_text, combined_confidence
                    else:
                        
                        combined = f"{text}\n\n[OCR Enhanced]\n{ocr_text}"
                        combined_confidence = max(confidence, 0.75)
                        return combined, combined_confidence
                        
            except Exception as e:
                logger.error(f"OCR enhancement failed: {e}")
                
        return text, confidence
    
    def detect_handwritten_sections(
        self,
        pdf_path: str
    ) -> Dict[str, Any]:
        if not self._ocr_available:
            return {
                "available": False,
                "error": "OCR not available"
            }
            
        try:
            
            ocr_results = self.handwriting_extractor.extract_from_pdf(pdf_path)
            
            result = {
                "available": True,
                "pages": []
            }
            
            for page_result in ocr_results:
                result["pages"].append({
                    "page": page_result.metadata.get("page", 0),
                    "handwriting_detected": page_result.metadata.get("handwriting_detected", False),
                    "handwriting_confidence": page_result.metadata.get("handwriting_confidence", 0),
                    "text_length": len(page_result.text)
                })
                
            return result
            
        except Exception as e:
            logger.error(f"Error detecting handwritten sections: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    def extract_handwritten_text_only(
        self,
        pdf_path: str
    ) -> Tuple[str, float]:
        if not self._ocr_available:
            return "", 0.0
            
        try:
            ocr_results = self.handwriting_extractor.extract_from_pdf(pdf_path)
            
            handwritten_texts = []
            total_confidence = 0.0
            count = 0
            
            for result in ocr_results:
                if result.metadata.get("handwriting_detected"):
                    handwritten_texts.append(result.text)
                    total_confidence += result.confidence
                    count += 1
            
            if handwritten_texts:
                confidence = total_confidence / count if count > 0 else 0.0
                return "\n\n".join(handwritten_texts), confidence
                
            return "", 0.0
            
        except Exception as e:
            logger.error(f"Error extracting handwritten text: {e}")
            return "", 0.0
    
    def enhanced_extraction_pipeline(
        self,
        pdf_path: str,
        use_ocr: bool = True,
        ocr_threshold: float = 0.7
    ) -> Dict[str, Any]:
        result = {
            "text": "",
            "confidence": 0.0,
            "extraction_method": "standard",
            "ocr_used": False,
            "handwriting_detected": False,
            "handwriting_sections": []
        }
        
        
        text, confidence = extract_text_from_pdf(pdf_path)
        result["text"] = text
        result["confidence"] = confidence
        
        
        if use_ocr and self._ocr_available and confidence < ocr_threshold:
            logger.info(f"Using OCR fallback (confidence: {confidence} < {ocr_threshold})")
            
            
            hw_detection = self.detect_handwritten_sections(pdf_path)
            if hw_detection.get("available"):
                result["handwriting_detected"] = any(
                    p.get("handwriting_detected", False) 
                    for p in hw_detection.get("pages", [])
                )
                result["handwriting_sections"] = hw_detection.get("pages", [])
            
            
            ocr_text, ocr_confidence = self.extract_with_ocr_fallback(
                pdf_path, ocr_threshold
            )
            
            if ocr_text:
                result["text"] = ocr_text
                result["confidence"] = ocr_confidence
                result["extraction_method"] = "ocr_enhanced"
                result["ocr_used"] = True
                
        return result
    
    def preprocess_and_extract(
        self,
        image_path: str,
        extract_handwriting: bool = True
    ) -> Dict[str, Any]:
        result = {
            "text": "",
            "confidence": 0.0,
            "preprocessing_applied": False,
            "handwriting_detected": False
        }
        
        if not self._ocr_available:
            result["error"] = "OCR not available"
            return result
            
        try:
            
            if self.image_preprocessor.is_available():
                processed_path = self.image_preprocessor.preprocess_image_for_ocr(
                    image_path
                )
                if processed_path != image_path:
                    result["preprocessing_applied"] = True
                    image_path = processed_path
                    
            
            extract_result = self.handwriting_extractor.extract_from_image_file(
                image_path,
                detect_handwriting=extract_handwriting
            )
            
            result["text"] = extract_result.get("text", "")
            result["confidence"] = extract_result.get("confidence", 0.0)
            result["handwriting_detected"] = extract_result.get("handwriting_detected", False)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in preprocess and extract: {e}")
            result["error"] = str(e)
            return result



_ocr_integrator = None


def get_ocr_integrator() -> OCRIntegrator:
    global _ocr_integrator
    if _ocr_integrator is None:
        _ocr_integrator = OCRIntegrator()
    return _ocr_integrator


def is_ocr_available() -> bool:
    return is_handwriting_available()


def enhanced_extract_text(
    pdf_path: str,
    use_ocr: bool = True
) -> Tuple[str, float]:
    integrator = get_ocr_integrator()
    
    if use_ocr:
        result = integrator.enhanced_extraction_pipeline(pdf_path)
        return result["text"], result["confidence"]
    else:
        return extract_text_from_pdf(pdf_path)
