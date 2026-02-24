import os
import html
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTTextLineHorizontal

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
    
    @property
    def width(self): return self.x1 - self.x0
    @property
    def height(self): return self.y1 - self.y0

@dataclass
class TableBlock:
    rows: List[List[TextElement]] = field(default_factory=list)
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows": [[elem.text for elem in row] for row in self.rows],
            "bbox": {
                "x": round(self.x0, 2),
                "y": round(self.y0, 2),
                "width": round(self.x1 - self.x0, 2),
                "height": round(self.y1 - self.y0, 2)
            },
            "confidence": round(self.confidence, 2)
        }


@dataclass
class LayoutResult:
    text_elements: List[TextElement] = field(default_factory=list)
    tables: List[TableBlock] = field(default_factory=list)
    html_output: str = ""
    json_output: Dict[str, Any] = field(default_factory=dict)

def extract_text_elements(pdf_path: str):
    if not os.path.exists(pdf_path):
        return [], {"error": "File not found"}
    
    elements = []
    metadata = {"file": pdf_path, "pages": 0}
    
    try:
        for pn, page in enumerate(extract_pages(pdf_path), 1):
            metadata["pages"] = pn
            for el in page:
                if isinstance(el, LTTextContainer):
                    t = el.get_text().strip()
                    if not t:
                        continue
                    bb = el.bbox
                    fs = 0.0
                    if bb[3] > bb[1]:
                        fs = max(6, min((bb[3]-bb[1])*0.8, 16))
                    elements.append(TextElement(t, bb[0], bb[1], bb[2], bb[3], pn, fs))
    except Exception as e:
        logger.error(f"Error: {e}")
    return elements, metadata

def make_html(elements, page_width=612, page_height=792):
    """Generate HTML with proper PDF-like layout rendering"""
    parts = ['<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Resume</title>']
    parts.append('''<style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Times New Roman', Times, serif; background: #f5f5f5; padding: 20px; }
        .page { 
            position: relative; 
            width: 612px; 
            min-height: 792px;
            margin: 0 auto 20px auto; 
            background: white; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.15); 
            padding: 40px 50px;
            page-break-after: always;
        }
        .text-block { 
            position: absolute; 
            white-space: pre-wrap; 
            word-wrap: break-word;
            overflow: hidden;
        }
    </style>''')
    parts.append('</head><body>')
    
    pages = {}
    for e in elements:
        pages.setdefault(e.page_num, []).append(e)
    
    for pn in sorted(pages.keys()):
        pes = sorted(pages[pn], key=lambda x: (-x.y0, x.x0))
        
        if pes:
            min_x = min(e.x0 for e in pes)
            max_x = max(e.x1 for e in pes)
            max_y = max(e.y1 for e in pes)
            min_y = min(e.y0 for e in pes)
        else:
            min_x, min_y, max_x, max_y = 50, 40, 562, 752
        
        page_content_height = max_y - min_y + 40
        parts.append(f'<div class="page" style="height:{page_content_height}px">')
        
        for e in pes:
            x = e.x0 - min_x + 10
            y = e.y0 - min_y + 30
            fs = max(8, min(e.font_size, 14))
            width = min(e.width + 5, max_x - min_x + 20 - x)
            is_heading = fs >= 12
            font_weight = "bold" if is_heading else "normal"
            color = "#333"
            
            parts.append(f'''<div class="text-block" style="left:{x:.1f}px;top:{y:.1f}px;width:{width:.1f}px;font-size:{fs:.1f}px;font-weight:{font_weight};color:{color};">{html.escape(e.text)}</div>''')
        
        parts.append('</div>')
    
    parts.append('</body></html>')
    return '\n'.join(parts)

def extract_full_resume_html(pdf_path):
    result = LayoutResult()
    elements, meta = extract_text_elements(pdf_path)
    result.text_elements = elements
    
    if "error" in meta:
        result.json_output = {"error": meta["error"]}
        return result
    
    result.html_output = make_html(elements)
    result.json_output = {"status": "success", "metadata": meta, "count": len(elements)}
    return result

def extract_layout_json(pdf_path):
    return extract_full_resume_html(pdf_path).json_output

def extract_layout_html(pdf_path):
    return extract_full_resume_html(pdf_path).html_output
