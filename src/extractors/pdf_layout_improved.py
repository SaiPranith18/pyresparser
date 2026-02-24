import os
import html
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTAnno, LTLine, LTFigure

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TextElement:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    font_size: float = 0.0
    font_name: str = ""
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class LayoutResult:
    text_elements: List[TextElement] = field(default_factory=list)
    html_output: str = ""
    json_output: Dict[str, Any] = field(default_factory=dict)


def extract_text_with_details(pdf_path: str):
    if not os.path.exists(pdf_path):
        return [], {"error": "File not found"}
    
    elements = []
    metadata = {"file": pdf_path, "pages": 0, "page_width": 612, "page_height": 792}
    
    try:
        for pn, page in enumerate(extract_pages(pdf_path), 1):
            metadata["pages"] = pn
            
            if hasattr(page, 'width'):
                metadata["page_width"] = page.width
                metadata["page_height"] = page.height
            
            for el in page:
                if isinstance(el, LTTextContainer):
                    text = el.get_text().strip()
                    if not text:
                        continue
                    
                    bbox = el.bbox
                    
                    font_size = 0
                    font_name = ""
                    if hasattr(el, 'get_chars'):
                        chars = list(el.get_chars())
                        if chars:
                            char = chars[0]
                            if hasattr(char, 'size'):
                                font_size = char.size
                            if hasattr(char, 'fontname'):
                                font_name = char.fontname
                    
                    if font_size == 0:
                        if bbox[3] > bbox[1]:
                            font_size = max(6, min((bbox[3] - bbox[1]) * 0.8, 16))
                    
                    elements.append(TextElement(
                        text, bbox[0], bbox[1], bbox[2], bbox[3], 
                        pn, font_size, font_name
                    ))
                    
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
    
    return elements, metadata


def make_html_v2(elements, page_width=612, page_height=792):
    
    pages_dict = {}
    for e in elements:
        pages_dict.setdefault(e.page_num, []).append(e)
    
    html_parts = ['<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Resume</title>']
    html_parts.append('''<style>
        * { box-sizing: border-box; }
        body { font-family: 'Times New Roman', Times, serif; background: 
        .page { width: 612px; min-height: 792px; margin: 0 auto 30px auto; background: white; box-shadow: 0 4px 15px rgba(0,0,0,0.2); padding: 50px 60px; }
        .resume-content { line-height: 1.5; color: 
        .name { font-size: 24px; font-weight: bold; text-align: center; margin-bottom: 8px; color: 
        .contact { font-size: 11px; text-align: center; margin-bottom: 20px; color: 
        .section-title { font-size: 14px; font-weight: bold; text-transform: uppercase; border-bottom: 1px solid 
        .section-content { font-size: 12px; margin-bottom: 12px; }
        .subsection { margin-bottom: 8px; }
        .subsection-title { font-weight: bold; font-size: 12px; }
        .subsection-meta { font-size: 11px; color: 
        ul { margin: 5px 0; padding-left: 20px; }
        li { font-size: 12px; margin-bottom: 4px; }
        .bold { font-weight: bold; }
    </style>''')
    html_parts.append('</head><body>')
    
    for pn in sorted(pages_dict.keys()):
        pes = pages_dict[pn]
        html_parts.append('<div class="page"><div class="resume-content">')
        
        sorted_elements = sorted(pes, key=lambda x: (-x.y1, x.x0))
        
        for e in sorted_elements:
            if len(e.text.strip()) < 2:
                continue
            
            text = html.escape(e.text)
            is_heading = e.font_size >= 14 or (len(e.text) < 40 and e.text.isupper())
            
            section_keywords = ['ABOUT', 'SKILL', 'EDUCATION', 'EXPERIENCE', 'PROJECT', 'CERTIFICATION', 
                             'AWARD', 'LANGUAGE', 'INTEREST', 'REFERENCE', 'SUMMARY', 'PROFILE']
            
            is_section = any(kw in e.text.upper() for kw in section_keywords) and len(e.text) < 50
            
            if is_section:
                html_parts.append(f'<div class="section-title">{text}</div>')
            elif is_heading and e.font_size >= 14:
                html_parts.append(f'<div class="subsection-title">{text}</div>')
            else:
                text_formatted = text.replace('\n', '<br>')
                html_parts.append(f'<div class="section-content">{text_formatted}</div>')
        
        html_parts.append('</div></div>')
    
    html_parts.append('</body></html>')
    return '\n'.join(html_parts)


def extract_full_resume_html(pdf_path: str):
    result = LayoutResult()
    elements, meta = extract_text_with_details(pdf_path)
    result.text_elements = elements
    
    if "error" in meta:
        result.json_output = {"error": meta["error"]}
        return result
    
    result.html_output = make_html_v2(elements)
    result.json_output = {"status": "success", "metadata": meta, "text_elements": len(elements)}
    return result


def extract_layout_html(pdf_path: str):
    return extract_full_resume_html(pdf_path).html_output


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = extract_full_resume_html(sys.argv[1])
        print(result.html_output[:2000])
