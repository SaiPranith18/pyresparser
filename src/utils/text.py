import pdfminer
import re
import os
import logging

from pdfminer.high_level import extract_text


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
    logger.info("OCR libraries loaded successfully")
except ImportError as e:
    OCR_AVAILABLE = False
    logger.warning(f"OCR libraries not available: {e}. Some PDF formats may not be parsed correctly.")


def preprocess_image_for_ocr(image):
    try:
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        
        image = image.convert('L')
        
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        
        image = image.filter(ImageFilter.SHARPEN)
        
        
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        image = image.convert('L')
        
        return image
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return image


def extract_text_with_ocr(pdf_path, use_preprocessing=True):
    try:
        logger.info(f"Starting OCR extraction for: {pdf_path}")
        
        
        images = convert_from_path(pdf_path, dpi=300)
        
        text = ""
        for page_num, image in enumerate(images):
            logger.info(f"Processing page {page_num + 1} with OCR")
            
            
            if use_preprocessing:
                image = preprocess_image_for_ocr(image)
            
            
            custom_config = r'--oem 3 --psm 6'  
            page_text = pytesseract.image_to_string(image, config=custom_config)
            text += page_text + "\n"
        
        logger.info(f"OCR extraction completed. Text length: {len(text)}")
        return text
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return ""


def extract_text_with_ocr_fallback(pdf_path):
    
    text = extract_text_with_ocr(pdf_path, use_preprocessing=True)
    if text and len(text.strip()) > 50:
        return text
    
    
    logger.info("Retrying OCR without preprocessing")
    text = extract_text_with_ocr(pdf_path, use_preprocessing=False)
    if text and len(text.strip()) > 50:
        return text
    
    
    logger.info("Retrying OCR with different configuration")
    try:
        images = convert_from_path(pdf_path, dpi=300)
        text = ""
        for image in images:
            
            custom_config = r'--oem 3 --psm 1'
            page_text = pytesseract.image_to_string(image, config=custom_config)
            text += page_text + "\n"
        
        if text and len(text.strip()) > 50:
            return text
    except Exception as e:
        logger.error(f"Fallback OCR also failed: {e}")
    
    return ""


def calculate_text_confidence(text):
    if not text or not text.strip():
        return 0.0
    
    text_length = len(text.strip())
    word_count = len(text.split())
    
    
    error_patterns = [
        r'[\x00-\x08\x0b-\x0c\x0e-\x1f]',  
        r'[_\~]{5,}',  
    ]
    
    error_count = 0
    for pattern in error_patterns:
        error_count += len(re.findall(pattern, text))
    
    
    
    length_factor = min(text_length / 1000, 1.0) * 0.4
    
    
    word_factor = min(word_count / 200, 1.0) * 0.3
    
    
    error_factor = max(1.0 - (error_count / 100), 0.0) * 0.3
    
    confidence = length_factor + word_factor + error_factor
    
    return round(confidence, 2)


def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return "", 0.0
    
    text = ""
    method_used = "none"
    confidence = 0.0
    
    
    try:
        logger.info(f"Trying pdfminer extraction for: {pdf_path}")
        text = extract_text(pdf_path)
        
        
        if text and len(text.strip()) > 50:
            method_used = "pdfminer"
            confidence = calculate_text_confidence(text)
            logger.info(f"pdfminer extraction successful. Text length: {len(text)}, Confidence: {confidence}")
            return text, confidence
        else:
            logger.warning(f"pdfminer returned empty or very short text. Length: {len(text) if text else 0}")
    except Exception as e:
        logger.error(f"pdfminer extraction failed: {e}")
    
    
    if OCR_AVAILABLE:
        logger.info("Falling back to OCR extraction")
        ocr_text = extract_text_with_ocr_fallback(pdf_path)
        
        if ocr_text and len(ocr_text.strip()) > 50:
            method_used = "ocr"
            confidence = calculate_text_confidence(ocr_text) * 0.8  
            logger.info(f"OCR extraction successful. Text length: {len(ocr_text)}, Confidence: {confidence}")
            return ocr_text, confidence
        else:
            logger.warning("OCR also returned empty or short text")
    else:
        logger.warning("OCR not available. Returning pdfminer result even if empty.")
    
    
    confidence = calculate_text_confidence(text)
    return text if text else "", confidence


def extract_text_from_image(image_path):
    if not OCR_AVAILABLE:
        logger.error("OCR libraries not available")
        return "", 0.0
    
    try:
        image = Image.open(image_path)
        
        
        image = preprocess_image_for_ocr(image)
        
        
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)
        
        confidence = calculate_text_confidence(text)
        return text, confidence
    except Exception as e:
        logger.error(f"Image OCR extraction failed: {e}")
        return "", 0.0
 
 
if __name__ == '__main__':
    pdf_path = "sample_resume.pdf"
    text, confidence = extract_text_from_pdf(pdf_path)
    print(f"Text: {text[:500]}...")
    print(f"Confidence: {confidence}")
