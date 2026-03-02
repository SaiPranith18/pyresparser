import os
import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)


api_features_bp = Blueprint('api_features', __name__)






@api_features_bp.route("/api/feedback", methods=["POST"])
def submit_feedback():
    try:
        from src.utils.feedback_collector import get_feedback_collector
        from src.utils.correction_storage import get_correction_storage
        
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        resume_id = data.get("resume_id")
        field_name = data.get("field_name")
        original_value = data.get("original_value")
        corrected_value = data.get("corrected_value")
        
        if not all([resume_id, field_name, original_value, corrected_value]):
            return jsonify({
                "status": "error", 
                "message": "Missing required fields"
            }), 400
        
        collector = get_feedback_collector()
        feedback_id = collector.add_correction(
            resume_id=resume_id,
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            user_id=data.get("user_id"),
            comment=data.get("comment", "")
        )
        
        # Save correction permanently to the correction storage
        storage = get_correction_storage()
        correction_id = storage.add_correction(
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            resume_id=resume_id,
            comment=data.get("comment", "")
        )
        
        # Mark the feedback as processed since it's now saved permanently
        collector.mark_as_processed(feedback_id)
        
        return jsonify({
            "status": "success",
            "feedback_id": feedback_id,
            "correction_id": correction_id,
            "message": "Feedback submitted and saved permanently"
        })
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/feedback/confirm", methods=["POST"])
def confirm_extraction():
    try:
        from src.utils.feedback_collector import get_feedback_collector
        
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        collector = get_feedback_collector()
        feedback_id = collector.add_confirmation(
            resume_id=data.get("resume_id"),
            field_name=data.get("field_name"),
            value=data.get("value"),
            user_id=data.get("user_id")
        )
        
        return jsonify({
            "status": "success",
            "feedback_id": feedback_id
        })
        
    except Exception as e:
        logger.error(f"Error confirming extraction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/feedback/reject", methods=["POST"])
def reject_extraction():
    try:
        from src.utils.feedback_collector import get_feedback_collector
        
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        collector = get_feedback_collector()
        feedback_id = collector.add_rejection(
            resume_id=data.get("resume_id"),
            field_name=data.get("field_name"),
            value=data.get("value"),
            reason=data.get("reason", ""),
            user_id=data.get("user_id")
        )
        
        return jsonify({
            "status": "success",
            "feedback_id": feedback_id
        })
        
    except Exception as e:
        logger.error(f"Error rejecting extraction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/learning/stats", methods=["GET"])
def get_learning_stats():
    try:
        from src.utils.continuous_learning import get_continuous_learning
        
        learning = get_continuous_learning()
        stats = learning.get_learning_statistics()
        
        return jsonify({
            "status": "success",
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting learning stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/learning/pending", methods=["GET"])
def get_pending_corrections():
    try:
        from src.utils.continuous_learning import get_continuous_learning
        
        learning = get_continuous_learning()
        corrections = learning.get_pending_corrections()
        
        return jsonify({
            "status": "success",
            "count": len(corrections),
            "corrections": corrections
        })
        
    except Exception as e:
        logger.error(f"Error getting pending corrections: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/learning/approve/<sample_id>", methods=["POST"])
def approve_correction(sample_id):
    try:
        from src.utils.continuous_learning import get_continuous_learning
        
        learning = get_continuous_learning()
        success = learning.approve_correction(sample_id)
        
        if success:
            return jsonify({"status": "success", "message": "Correction approved"})
        else:
            return jsonify({"status": "error", "message": "Correction not found"}), 404
            
    except Exception as e:
        logger.error(f"Error approving correction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/learning/reject/<sample_id>", methods=["POST"])
def reject_correction(sample_id):
    try:
        from src.utils.continuous_learning import get_continuous_learning
        
        data = request.get_json() or {}
        reason = data.get("reason", "")
        
        learning = get_continuous_learning()
        success = learning.reject_correction(sample_id, reason)
        
        if success:
            return jsonify({"status": "success", "message": "Correction rejected"})
        else:
            return jsonify({"status": "error", "message": "Correction not found"}), 404
            
    except Exception as e:
        logger.error(f"Error rejecting correction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500






@api_features_bp.route("/api/model/train", methods=["POST"])
def train_model():
    try:
        from src.training.trainer import get_model_trainer, TrainingConfig
        
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        config = TrainingConfig(
            model_type=data.get("model_type", "spacy"),
            base_model=data.get("base_model", "en_core_web_sm"),
            epochs=data.get("epochs", 10),
            batch_size=data.get("batch_size", 8),
            learning_rate=data.get("learning_rate", 5e-5),
            output_dir=data.get("output_dir", "./models"),
            field=data.get("field", "general")
        )
        
        trainer = get_model_trainer()
        job_id = trainer.create_training_job(config)
        
        
        success = trainer.run_training_job(job_id)
        
        if success:
            return jsonify({
                "status": "success",
                "job_id": job_id,
                "message": "Training completed"
            })
        else:
            job_status = trainer.get_job_status(job_id)
            return jsonify({
                "status": "error",
                "job_id": job_id,
                "message": job_status.get("error_message", "Training failed")
            }), 500
            
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/model/status", methods=["GET"])
def model_status():
    """Get overall model training status and capabilities."""
    try:
        from src.training.trainer import get_model_trainer
        from src.training.data_preparator import get_data_preparator
        
        trainer = get_model_trainer()
        preparator = get_data_preparator()
        
        # Get available models
        models = trainer.list_models()
        
        # Get training data stats
        try:
            data_stats = preparator.get_dataset_statistics()
        except:
            data_stats = {}
        
        return jsonify({
            "status": "success",
            "training_available": True,
            "available_models": models,
            "training_data_stats": data_stats,
            "features": {
                "spacy_training": True,
                "transformer_training": True,
                "custom_ner": True,
                "feedback_based_training": True
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/model/status/<job_id>", methods=["GET"])
def get_training_status(job_id):
    try:
        from src.training.trainer import get_model_trainer
        
        trainer = get_model_trainer()
        status = trainer.get_job_status(job_id)
        
        if status:
            return jsonify({
                "status": "success",
                "job_status": status
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Job not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting training status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/model/list", methods=["GET"])
def list_models():
    try:
        from src.training.trainer import get_model_trainer
        
        trainer = get_model_trainer()
        models = trainer.list_models()
        
        return jsonify({
            "status": "success",
            "count": len(models),
            "models": models
        })
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/model/deploy", methods=["POST"])
def deploy_model():
    try:
        from src.training.model_registry import get_model_registry
        
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        registry = get_model_registry()
        success = registry.deploy_version(
            data.get("model_name"),
            data.get("version_id")
        )
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Model deployed successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to deploy model"
            }), 500
            
    except Exception as e:
        logger.error(f"Error deploying model: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/training/data/stats", methods=["GET"])
def get_training_data_stats():
    try:
        from src.training.data_preparator import get_data_preparator
        
        field = request.args.get("field")
        
        preparator = get_data_preparator()
        stats = preparator.get_dataset_statistics(field)
        
        return jsonify({
            "status": "success",
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting training data stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500






@api_features_bp.route("/api/ocr/status", methods=["GET"])
def ocr_status():
    try:
        from src.extractors.handwriting_extractor import is_handwriting_available, get_handwriting_extractor
        
        available = is_handwriting_available()
        extractor = get_handwriting_extractor()
        
        tesseract_version = None
        if available:
            try:
                import pytesseract
                tesseract_version = str(pytesseract.get_tesseract_version())
            except:
                pass
        
        return jsonify({
            "status": "success",
            "ocr_available": available,
            "tesseract_version": tesseract_version,
            "features": {
                "handwriting_recognition": available,
                "image_preprocessing": available
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking OCR status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/ocr/extract", methods=["POST"])
def extract_with_ocr():
    try:
        from src.utils.ocr_integrator import get_ocr_integrator
        
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file provided"}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({"status": "error", "message": "No file selected"}), 400
        
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            detect_handwriting = request.form.get('detect_handwriting', 'true').lower() == 'true'
            
            integrator = get_ocr_integrator()
            
            if tmp_path.lower().endswith('.pdf'):
                result = integrator.enhanced_extraction_pipeline(
                    tmp_path, 
                    use_ocr=True
                )
            else:
                result = integrator.preprocess_and_extract(
                    tmp_path,
                    extract_handwriting=detect_handwriting
                )
            
            return jsonify({
                "status": "success",
                "result": result
            })
            
        finally:
            
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        logger.error(f"Error extracting with OCR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/ocr/detect-handwriting", methods=["POST"])
def detect_handwriting():
    try:
        from src.utils.ocr_integrator import get_ocr_integrator
        
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file provided"}), 400
        
        file = request.files['file']
        
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            integrator = get_ocr_integrator()
            result = integrator.detect_handwritten_sections(tmp_path)
            
            return jsonify({
                "status": "success",
                "result": result
            })
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        logger.error(f"Error detecting handwriting: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500






@api_features_bp.route("/api/feedback/stats", methods=["GET"])
def get_feedback_stats():
    try:
        from src.utils.feedback_collector import get_feedback_collector
        
        collector = get_feedback_collector()
        stats = collector.get_statistics()
        
        return jsonify({
            "status": "success",
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/feedback/export", methods=["GET"])
def export_training_data():
    try:
        from src.utils.feedback_collector import get_feedback_collector
        
        field = request.args.get("field")
        fb_type = request.args.get("type")
        
        feedback_types = [fb_type] if fb_type else None
        
        collector = get_feedback_collector()
        data = collector.export_training_data(field, feedback_types)
        
        return jsonify({
            "status": "success",
            "count": len(data),
            "training_data": data
        })
        
    except Exception as e:
        logger.error(f"Error exporting training data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/corrections", methods=["GET"])
def get_corrections():
    """Get all permanent corrections, optionally filtered by field."""
    try:
        from src.utils.correction_storage import get_correction_storage
        
        field_name = request.args.get("field")
        
        storage = get_correction_storage()
        corrections = storage.get_corrections(field_name)
        
        return jsonify({
            "status": "success",
            "count": len(corrections),
            "corrections": corrections
        })
        
    except Exception as e:
        logger.error(f"Error getting corrections: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/corrections/stats", methods=["GET"])
def get_correction_stats():
    """Get statistics about permanent corrections."""
    try:
        from src.utils.correction_storage import get_correction_storage
        
        storage = get_correction_storage()
        stats = storage.get_statistics()
        
        return jsonify({
            "status": "success",
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting correction stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_features_bp.route("/api/corrections/<correction_id>", methods=["DELETE"])
def delete_correction(correction_id):
    """Delete a permanent correction by ID."""
    try:
        from src.utils.correction_storage import get_correction_storage
        
        storage = get_correction_storage()
        success = storage.delete_correction(correction_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Correction {correction_id} deleted"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Correction not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error deleting correction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def register_routes(app):
    app.register_blueprint(api_features_bp)
    logger.info("Feature API routes registered")
