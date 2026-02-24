import os
import re
import pdfminer

from flask import Flask, render_template, request,jsonify
from pdfminer.high_level import extract_text
from name import extract_name_from_resume
from skills import extract_skills_from_resume
from education import extract_education_from_resume
from certifications import extract_certifications_from_resume
from formatter import clean_fulltext_format
from projects import extract_projects_section



app = Flask(__name__)

from src.models.models import db, init_database, save_resume, get_resume, get_all_resumes, delete_resume, update_resume, search_resumes
from src.utils.text import extract_text_from_pdf
from src.utils.section_extractor import extract_section_from_resume
from src.models.name import extract_name_from_resume
from src.utils.formatter import clean_fulltext_format
from src.utils.headings import detect_headings

try:
    from src.extractors.layoutlm_extractor import extract_with_layoutlm, is_layoutlm_available, LAYOUTLM_AVAILABLE
except ImportError:
    LAYOUTLM_AVAILABLE = False
    extract_with_layoutlm = None
    is_layoutlm_available = lambda: False

try:
    from src.utils.new_sections import (
        extract_languages_from_resume,
        extract_interests_from_resume,
        extract_achievements_from_resume,
        extract_publications_from_resume,
        extract_volunteer_from_resume,
        extract_summary_from_resume
    )
    NEW_SECTIONS_AVAILABLE = True
except ImportError:
    NEW_SECTIONS_AVAILABLE = False
    extract_languages_from_resume = None
    extract_interests_from_resume = None
    extract_achievements_from_resume = None
    extract_publications_from_resume = None
    extract_volunteer_from_resume = None
    extract_summary_from_resume = None

try:
    from src.utils.structured_output import get_structured_output_generator, generate_structured_resume
    STRUCTURED_OUTPUT_AVAILABLE = True
except ImportError:
    STRUCTURED_OUTPUT_AVAILABLE = False
    get_structured_output_generator = None
    generate_structured_resume = None

try:
    from src.utils.performance import (
        get_parallel_extractor,
        get_performance_metrics,
        extract_all_sections_optimized,
        LRUCache
    )
    PERFORMANCE_AVAILABLE = True
except ImportError:
    PERFORMANCE_AVAILABLE = False
    get_parallel_extractor = None
    get_performance_metrics = None
    extract_all_sections_optimized = None
    LRUCache = None

try:
    from src.extractors.transformers_extractor import (
        is_transformers_available,
        get_transformer_extractor,
        get_ensemble_scorer
    )
    TRANSFORMERS_AVAILABLE = is_transformers_available()
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    is_transformers_available = lambda: False
    get_transformer_extractor = None
    get_ensemble_scorer = None

try:
    from src.extractors.pdf_layout_improved import extract_full_resume_html, extract_layout_html
    
    def extract_layout_json(pdf_path):
        result = extract_full_resume_html(pdf_path)
        return result.json_output
    PDF_LAYOUT_EXTRACTOR_AVAILABLE = True
except ImportError:
    PDF_LAYOUT_EXTRACTOR_AVAILABLE = False
    extract_full_resume_html = None
    extract_layout_json = None
    extract_layout_html = None


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)




app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resumes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)


with app.app_context():
    db.create_all()
    logger.info("Database tables created successfully")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024



confidence_scores = {
    "text_confidence": 0.0,
    "skills_confidence": 0.0,
    "education_confidence": 0.0,
    "certifications_confidence": 0.0,
    "projects_confidence": 0.0,
    "name_confidence": 0.0,
    "languages_confidence": 0.0,
    "interests_confidence": 0.0,
    "achievements_confidence": 0.0,
    "publications_confidence": 0.0,
    "volunteer_confidence": 0.0,
    "summary_confidence": 0.0
}


def calculate_overall_accuracy() -> float:
    valid_scores = [s for s in confidence_scores.values() if s > 0]
    if not valid_scores:
        return 0.0
    overall = sum(valid_scores) / len(valid_scores) * 100
    return round(overall, 2)


def extract_name_with_filename_fallback(text: str, filename: str) -> Tuple[str, float]:
    
    try:
        extracted_name, confidence = extract_name_from_resume(text)
        
        
        if extracted_name and confidence > 0:
            logger.info(f"Name extracted from text: {extracted_name} (confidence: {confidence})")
            return extracted_name, confidence
    except Exception as e:
        logger.warning(f"Error extracting name from text: {e}")
    
    
    if filename:
        
        
        name_from_file = os.path.splitext(filename)[0]
        
        
        name_from_file = name_from_file.replace('_', ' ').replace('-', ' ')
        
        
        common_words = ['resume', 'cv', 'curriculum', 'vitae', 'document', 'file']
        name_parts = name_from_file.split()
        name_parts = [part for part in name_parts if part.lower() not in common_words]
        name_from_file = ' '.join(name_parts)
        
        
        name_from_file = name_from_file.title()
        
        if name_from_file and len(name_from_file) > 1:
            
            logger.info(f"Using filename as name fallback: {name_from_file}")
            return name_from_file, 0.3  
    
    
    logger.warning("Could not extract name, returning empty string")
    return "", 0.0


def extract_all_sections(text: str, pdf_path: Optional[str] = None, filename: str = "") -> Dict[str, Tuple[str, float]]:
    results = {}
    
    
    try:
        
        name, conf = extract_name_with_filename_fallback(text, filename)
        results["name"] = (name, conf)
        confidence_scores["name_confidence"] = conf
    except Exception as e:
        logger.error(f"Error extracting name: {e}")
        results["name"] = ("", 0.0)
    
    try:
        skills, conf = extract_section_from_resume(text, "skills", pdf_path)
        results["skills"] = (skills, conf)
        confidence_scores["skills_confidence"] = conf
    except Exception as e:
        logger.error(f"Error extracting skills: {e}")
        results["skills"] = ("", 0.0)
    
    try:
        education, conf = extract_section_from_resume(text, "education", pdf_path)
        results["education"] = (education, conf)
        confidence_scores["education_confidence"] = conf
    except Exception as e:
        logger.error(f"Error extracting education: {e}")
        results["education"] = ("", 0.0)
    
    try:
        experience, conf = extract_section_from_resume(text, "experience", pdf_path)
        results["experience"] = (experience, conf)
        confidence_scores["experience_confidence"] = conf
    except Exception as e:
        logger.error(f"Error extracting experience: {e}")
        results["experience"] = ("", 0.0)
    
    try:
        projects, conf = extract_section_from_resume(text, "projects", pdf_path)
        results["projects"] = (projects, conf)
        confidence_scores["projects_confidence"] = conf
    except Exception as e:
        logger.error(f"Error extracting projects: {e}")
        results["projects"] = ("", 0.0)
    
    try:
        certifications, conf = extract_section_from_resume(text, "certifications", pdf_path)
        results["certifications"] = (certifications, conf)
        confidence_scores["certifications_confidence"] = conf
    except Exception as e:
        logger.error(f"Error extracting certifications: {e}")
        results["certifications"] = ("", 0.0)
    
    
    if NEW_SECTIONS_AVAILABLE:
        new_sections = [
            ("languages", extract_languages_from_resume),
            ("interests", extract_interests_from_resume),
            ("achievements", extract_achievements_from_resume),
            ("publications", extract_publications_from_resume),
            ("volunteer", extract_volunteer_from_resume),
            ("summary", extract_summary_from_resume)
        ]
        
        for section_name, extractor_func in new_sections:
            try:
                result, conf = extractor_func(text)
                results[section_name] = (result, conf)
                confidence_scores[f"{section_name}_confidence"] = conf
            except Exception as e:
                logger.error(f"Error extracting {section_name}: {e}")
                results[section_name] = ("", 0.0)
    
    return results




@app.route("/", methods=["GET", "POST"])
def home():
    name = None
    resume_text = None
    skills_section = None
    extracted_education = None
    selected_section = None
    section=None
    certifications =None
    projects=None

    if request.method == "POST":
        file = request.files.get("resume")
        text = ""
        text_confidence = 0.0

        if file and file.filename:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
 
            text = extract_text(file_path)
            name = extract_name_from_resume(text)
            resume_text = clean_fulltext_format(text)
            skills_list = [
                "Python", "Data Analysis", "Machine Learning",
                "Communication", "Project Management",
                "Deep Learning", "MySQL", "Tableau"
            ]
            extracted_skills = extract_skills_from_resume(text, skills_list)

            
            extracted_education = extract_education_from_resume(text)
            selected_section = request.form.get("section")
            section = request.form.get("section")

            certifications = extract_certifications_from_resume(text)
            projects = extract_projects_section(text)
            
    return render_template(
    "index.html",
    name=name,
    resume_text=resume_text,
    extracted_skills=extracted_skills,
    extracted_education=extracted_education,
    selected_section=selected_section,
    section=section,
    certifications=certifications,
    projects=projects
)




@app.route("/extract", methods=["POST"])
def extract_ajax():
    file = request.files.get("resume")
    section = request.form.get("section")

    if not file or not section:
        return jsonify({"result": "Invalid input"}), 400

try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

    text = extract_text(file_path)

    if section == "skills":
        skills_list = [
            "Python", "Data Analysis", "Machine Learning",
            "Communication", "Project Management",
            "Deep Learning", "MySQL", "Tableau"
        ]
        result = extract_skills_from_resume(text, skills_list)

    elif section == "education":
        result = extract_education_from_resume(text)

    elif section == "name":
        result = extract_name_from_resume(text)

        elif section == "fulltext":
            result = clean_fulltext_format(text)
            result_data = {"result": result, "confidence": text_confidence}
        
        elif section in ["languages", "interests", "achievements", "publications", "volunteer", "summary"]:
            if NEW_SECTIONS_AVAILABLE:
                extractors = {
                    "languages": extract_languages_from_resume,
                    "interests": extract_interests_from_resume,
                    "achievements": extract_achievements_from_resume,
                    "publications": extract_publications_from_resume,
                    "volunteer": extract_volunteer_from_resume,
                    "summary": extract_summary_from_resume
                }
                result, conf = extractors[section](text)
                result_data = {"result": result, "confidence": conf}
            else:
                result_data = {"result": "Section not available", "confidence": 0.0}
        
        else:
            result, conf = extract_section_from_resume(text, section, file_path)
            result_data = {"result": result, "confidence": conf}

        overall_accuracy = calculate_overall_accuracy()
        result_data["overall_accuracy"] = overall_accuracy
        
        return jsonify(result_data)
    
    except Exception as e:
        logger.error(f"Error in extract_ajax: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/parse", methods=["POST", "GET", "DELETE"])
def api_parse_resume():
    file = request.files.get("resume")
    section = request.form.get("section")

    if not file or not section:
        return jsonify({
            "status": "error",
            "message": "resume file and section are required"
        }), 400

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        text, text_confidence = extract_text_from_pdf(file_path)
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to extract PDF text"
        }), 500

    try:
        if section == "skills":
            skills_list = [
                "Python", "Data Analysis", "Machine Learning",
                "Communication", "Project Management",
                "Deep Learning", "MySQL", "Tableau"
            ]
            result = extract_skills_from_resume(text, skills_list)

        elif section == "education":
            result = extract_education_from_resume(text)

        elif section == "projects":
            result = extract_projects_section(text)

        elif section == "certifications":
            result = extract_certifications_from_resume(text)

        elif section == "name":
            result = extract_name_from_resume(text)

        elif section == "fulltext":
            result_data = clean_fulltext_format(text)
            section_confidence = text_confidence
        
        elif section == "structured":
            
            if STRUCTURED_OUTPUT_AVAILABLE:
                all_sections = extract_all_sections(text, file_path)
                all_sections["text"] = (text, text_confidence)
                structured = generate_structured_resume(text, all_sections)
                return jsonify({
                    "status": "success",
                    "data": structured,
                    "overall_accuracy": calculate_overall_accuracy()
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "Structured output not available"
                }), 500

        elif section in ["languages", "interests", "achievements", "publications", "volunteer", "summary"]:
            if NEW_SECTIONS_AVAILABLE:
                extractors = {
                    "languages": extract_languages_from_resume,
                    "interests": extract_interests_from_resume,
                    "achievements": extract_achievements_from_resume,
                    "publications": extract_publications_from_resume,
                    "volunteer": extract_volunteer_from_resume,
                    "summary": extract_summary_from_resume
                }
                result, conf = extractors[section](text)
                result_data = result
                section_confidence = conf
            else:
                return jsonify({
                    "status": "error",
                    "message": f"Section {section} not available"
                }), 500

        else:
            result, conf = extract_section_from_resume(text, section, file_path)
            result_data = result
            section_confidence = conf

        if not result_data:
            return jsonify({
                "status": "error",
                "message": f"No data found for section: {section}"
            })

        overall_accuracy = calculate_overall_accuracy()

        return jsonify({
            "status": "success",
            "section": section,
            "data": result_data,
            "confidence": section_confidence,
            "text_confidence": text_confidence,
            "overall_accuracy": overall_accuracy
        })

    except Exception as e:
        logger.error(f"Error in api_parse_resume: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/parse-all", methods=["POST"])
def api_parse_all():
    file = request.files.get("resume")

    if not file:
        return jsonify({
            "status": "error",
            "message": "Resume file is required"
        }), 400

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        text, text_confidence = extract_text_from_pdf(file_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to extract text: {str(e)}"
        }), 500

    try:
        
        all_sections = extract_all_sections(text, file_path)
        
        
        overall_accuracy = calculate_overall_accuracy()
        
        
        response = {
            "status": "success",
            "overall_accuracy": overall_accuracy,
            "text_confidence": text_confidence,
            "sections": {}
        }
        
        for section_name, (data, confidence) in all_sections.items():
            response["sections"][section_name] = {
                "data": data,
                "confidence": confidence
            }
        
        
        if STRUCTURED_OUTPUT_AVAILABLE:
            all_sections["text"] = (text, text_confidence)
            structured = generate_structured_resume(text, all_sections)
            response["structured"] = structured
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in api_parse_all: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/detect-headings", methods=["POST"])
def detect_headings_api():
    file = request.files.get("resume")

    if not file or not file.filename:
        return jsonify({
            "status": "error",
            "message": "Resume file is required"
        }), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        text, text_confidence = extract_text_from_pdf(file_path)
        
        if not text or len(text.strip()) < 10:
            return jsonify({
                "status": "error",
                "message": "Could not extract text from the resume"
            }), 400
        
        headings, headings_confidence = detect_headings(text)
        heading_texts = [heading[1] for heading in headings]
        
        return jsonify({
            "status": "success",
            "headings": heading_texts,
            "headings_confidence": headings_confidence,
            "text_confidence": text_confidence
        })

    except Exception as e:
        logger.error(f"Error detecting headings: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/extract-layoutlm", methods=["POST"])
def extract_layoutlm():
    file = request.files.get("resume")

    if not file:
        return jsonify({
            "status": "error",
            "message": "Resume file is required"
        }), 400

    if not LAYOUTLM_AVAILABLE or extract_with_layoutlm is None:
        return jsonify({
            "status": "error",
            "message": "LayoutLMv3 is not available. Please install required dependencies."
        }), 500

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        result, confidence = extract_with_layoutlm(file_path)
        
        return jsonify({
            "status": "success",
            "data": result,
            "confidence": confidence,
            "extraction_method": "layoutlmv3"
        })

    except Exception as e:
        logger.error(f"Error extracting with LayoutLMv3: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/status", methods=["GET"])
def get_status():
    return jsonify({
        "status": "success",
        "features": {
            "layoutlm": LAYOUTLM_AVAILABLE,
            "new_sections": NEW_SECTIONS_AVAILABLE,
            "structured_output": STRUCTURED_OUTPUT_AVAILABLE,
            "performance": PERFORMANCE_AVAILABLE,
            "transformers": TRANSFORMERS_AVAILABLE,
            "pdf_layout_extractor": PDF_LAYOUT_EXTRACTOR_AVAILABLE
        },
        "supported_sections": [
            "name", "fulltext", "skills", "education", "experience",
            "projects", "certifications", "languages", "interests",
            "achievements", "publications", "volunteer", "summary",
            "structured" if STRUCTURED_OUTPUT_AVAILABLE else None
        ]
    })


@app.route("/layoutlm-status", methods=["GET"])
def layoutlm_status():
    return jsonify({
        "status": "success",
        "available": LAYOUTLM_AVAILABLE
    })


@app.route("/api/extract-layout", methods=["POST"])
def api_extract_layout():
    file = request.files.get("resume")
    output_format = request.form.get("format", "json")
    if not file or not file.filename:
        return jsonify({"status": "error", "message": "Resume file is required"}), 400
    if not PDF_LAYOUT_EXTRACTOR_AVAILABLE:
        return jsonify({"status": "error", "message": "PDF Layout Extractor is not available"}), 500
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    try:
        result = extract_full_resume_html(file_path)
        if output_format == "html":
            return jsonify({"status": "success", "html_output": result.html_output, "extraction_pipeline": ["PDF", "Extract text with positions", "Flow-based HTML reconstruction"], "summary": {"text_elements": len(result.text_elements)}})
        else:
            return jsonify(result.json_output)
    except Exception as e:
        logger.error(f"Error in layout extraction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/layout-status", methods=["GET"])
def layout_status():
    return jsonify({"status": "success", "available": PDF_LAYOUT_EXTRACTOR_AVAILABLE, "features": {"bounding_boxes": PDF_LAYOUT_EXTRACTOR_AVAILABLE, "table_detection": PDF_LAYOUT_EXTRACTOR_AVAILABLE, "html_reconstruction": PDF_LAYOUT_EXTRACTOR_AVAILABLE, "css_positioning": PDF_LAYOUT_EXTRACTOR_AVAILABLE}})




@app.route("/api/save-resume", methods=["POST"])
def api_save_resume():
    file = request.files.get("resume")
    
    if not file or not file.filename:
        return jsonify({"status": "error", "message": "Resume file is required"}), 400
    
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        
        
        text, text_confidence = extract_text_from_pdf(file_path)
        
        
        all_sections = extract_all_sections(text, file_path, file.filename)
        
        
        structured_data = {}
        if STRUCTURED_OUTPUT_AVAILABLE:
            all_sections["text"] = (text, text_confidence)
            structured_data = generate_structured_resume(text, all_sections)
        else:
            
            for section_name, (data, confidence) in all_sections.items():
                structured_data[section_name] = {
                    "raw_text": data,
                    "confidence": confidence
                }
        
        
        layout_html = ""
        if PDF_LAYOUT_EXTRACTOR_AVAILABLE:
            try:
                layout_result = extract_full_resume_html(file_path)
                layout_html = layout_result.html_output
            except Exception as e:
                logger.warning(f"Could not extract layout HTML: {e}")
        
        
        resume = save_resume(
            filename=file.filename,
            structured_data=structured_data,
            extracted_text=text,
            layout_html=layout_html,
            original_pdf_path=file_path
        )
        
        return jsonify({
            "status": "success",
            "message": "Resume saved successfully",
            "resume_id": resume.id,
            "filename": resume.filename,
            "sections": list(structured_data.keys()),
            "created_at": resume.created_at.isoformat() if resume.created_at else None
        })
        
    except Exception as e:
        logger.error(f"Error saving resume: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/resumes", methods=["GET"])
def api_get_all_resumes():
    try:
        resumes = get_all_resumes()
        return jsonify({
            "status": "success",
            "count": len(resumes),
            "resumes": [r.to_dict() for r in resumes]
        })
    except Exception as e:
        logger.error(f"Error getting resumes: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/resume/<int:resume_id>", methods=["GET"])
def api_get_resume(resume_id):
    try:
        resume = get_resume(resume_id)
        if not resume:
            return jsonify({"status": "error", "message": "Resume not found"}), 404
        
        return jsonify({
            "status": "success",
            "resume": resume.to_full_dict()
        })
    except Exception as e:
        logger.error(f"Error getting resume: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/resume/<int:resume_id>/preview", methods=["GET"])
def api_get_resume_preview(resume_id):
    try:
        resume = get_resume(resume_id)
        if not resume:
            return jsonify({"status": "error", "message": "Resume not found"}), 404
        
        if not resume.layout_html:
            return jsonify({"status": "error", "message": "No preview available"}), 404
        
        return jsonify({
            "status": "success",
            "resume_id": resume_id,
            "filename": resume.filename,
            "html_output": resume.layout_html,
            "text_elements_count": len(resume.extracted_text) if resume.extracted_text else 0
        })
    except Exception as e:
        logger.error(f"Error getting preview: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/resume/<int:resume_id>", methods=["DELETE"])
def api_delete_resume(resume_id):
    try:
        success = delete_resume(resume_id)
        if success:
            return jsonify({"status": "success", "message": "Resume deleted"})
        else:
            return jsonify({"status": "error", "message": "Resume not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting resume: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/search", methods=["GET"])
def api_search_resumes():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"status": "error", "message": "Search query required"}), 400
    
    try:
        resumes = search_resumes(query)
        return jsonify({
            "status": "success",
            "query": query,
            "count": len(resumes),
            "resumes": [r.to_dict() for r in resumes]
        })
    except Exception as e:
        logger.error(f"Error searching resumes: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/preview/<int:resume_id>", methods=["GET"])
def preview_resume(resume_id):
    try:
        resume = get_resume(resume_id)
        if not resume:
            return "Resume not found", 404
        
        return render_template("preview.html", resume=resume)
    except Exception as e:
        logger.error(f"Error previewing resume: {e}")
        return f"Error: {str(e)}", 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("Starting Enhanced Resume Parser")
    logger.info(f"LayoutLM Available: {LAYOUTLM_AVAILABLE}")
    logger.info(f"New Sections Available: {NEW_SECTIONS_AVAILABLE}")
    logger.info(f"Structured Output Available: {STRUCTURED_OUTPUT_AVAILABLE}")
    logger.info(f"Performance Features Available: {PERFORMANCE_AVAILABLE}")
    logger.info(f"Transformers Available: {TRANSFORMERS_AVAILABLE}")
    logger.info(f"PDF Layout Extractor Available: {PDF_LAYOUT_EXTRACTOR_AVAILABLE}")
    
    app.run(host="127.0.0.1", port=8000, debug=True)
