# Implementation Plan: Continuous Learning, Custom Model Training & Handwritten Recognition

## 1. Continuous Learning System

### 1.1 Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│               Continuous Learning Module                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Feedback     │  │ Model        │  │ Data            │  │
│  │ Collector   │  │ Updater      │  │ Store           │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Database: SQLite (learning_data table)                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Database Schema Changes
```
python
# New table: learning_data
- id: Integer (Primary Key)
- resume_id: Integer (Foreign Key)
- field_name: String (e.g., "skills", "education")
- original_extraction: Text (JSON)
- corrected_extraction: Text (JSON)
- correction_feedback: Text
- confidence_before: Float
- confidence_after: Float
- timestamp: DateTime
- status: String ("pending", "approved", "rejected")

# New table: model_metrics
- id: Integer (Primary Key)
- model_name: String
- accuracy: Float
- precision: Float
- recall: Float
- f1_score: Float
- training_samples: Integer
- timestamp: DateTime
```

### 1.3 API Endpoints
- `POST /api/feedback` - Submit correction feedback
- `GET /api/learning/stats` - Get learning statistics
- `POST /api/model/retrain` - Trigger model retraining
- `GET /api/learning/pending` - Get pending corrections

### 1.4 Implementation Files
- `src/utils/continuous_learning.py` - Core learning logic
- `src/utils/feedback_collector.py` - Feedback collection
- `src/utils/model_updater.py` - Model update management

---

## 2. Custom Model Training

### 2.1 Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│               Custom Model Training Module                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Data         │  │ Training     │  │ Model           │  │
│  │ Preparator   │  │ Pipeline     │  │ Registry        │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Supports: spaCy NER, Custom Transformers, Rule-based     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Features
- **Training Data Management**: Import/export labeled data
- **Model Configuration**: Custom hyperparameters
- **Training Pipeline**: spaCy + Transformers support
- **Model Registry**: Version control for models
- **A/B Testing**: Compare model performance

### 2.3 API Endpoints
- `POST /api/model/train` - Start training job
- `GET /api/model/status/<job_id>` - Get training status
- `POST /api/model/deploy` - Deploy trained model
- `GET /api/model/list` - List available models
- `POST /api/model/compare` - A/B test models

### 2.4 Implementation Files
- `src/training/data_preparator.py` - Prepare training data
- `src/training/trainer.py` - Model training logic
- `src/training/model_registry.py` - Model version management

---

## 3. Handwritten Recognition

### 3.1 Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│               Handwritten Recognition Module                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Image        │  │ OCR          │  │ Text            │  │
│  │ Preprocessor│  │ Engine       │  │ Integrator       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Uses: Tesseract OCR + Custom ML (optional)                │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Features
- **OCR Integration**: Tesseract OCR for text extraction
- **Image Preprocessing**: Denoising, binarization, deskewing
- **Handwritten Detection**: Identify handwritten vs printed sections
- **Hybrid Extraction**: Combine OCR with ML for better results
- **Confidence Scoring**: Rate OCR accuracy

### 3.3 Dependencies
- `pytesseract` - Tesseract Python bindings
- `opencv-python` - Image preprocessing
- `pillow` - Image manipulation
- `pytesseract` requires Tesseract installed on system

### 3.4 Implementation Files
- `src/extractors/handwriting_extractor.py` - Handwriting OCR
- `src/utils/image_preprocessor.py` - Image preprocessing
- `src/utils/ocr_integrator.py` - Combine OCR with existing extractors

### 3.5 Updated Extraction Pipeline
```
python
def extract_text_from_pdf(pdf_path):
    # Step 1: Try standard PDF text extraction
    # Step 2: If low confidence, check for handwritten sections
    # Step 3: Apply OCR to handwritten sections
    # Step 4: Combine results
```

---

## 4. Implementation Order

### Phase 1: Foundation (Week 1)
1. [ ] Create database schema for learning data
2. [ ] Implement feedback collection API
3. [ ] Set up Tesseract OCR integration
4. [ ] Create image preprocessing utilities

### Phase 2: Core Features (Week 2)
1. [ ] Implement continuous learning engine
2. [ ] Create handwritten detection module
3. [ ] Build OCR integration layer
4. [ ] Add feedback review interface

### Phase 3: Training System (Week 3)
1. [ ] Implement data preparator
2. [ ] Create training pipeline
3. [ ] Build model registry
4. [ ] Add A/B testing framework

### Phase 4: Testing & Optimization (Week 4)
1. [ ] Integration testing
2. [ ] Performance optimization
3. [ ] Documentation
4. [ ] Bug fixes

---

## 5. File Changes Summary

### New Files to Create
| File | Purpose |
|------|---------|
| `src/utils/continuous_learning.py` | Core learning logic |
| `src/utils/feedback_collector.py` | Feedback management |
| `src/training/data_preparator.py` | Training data prep |
| `src/training/trainer.py` | Model training |
| `src/training/model_registry.py` | Model versioning |
| `src/extractors/handwriting_extractor.py` | OCR for handwriting |
| `src/utils/image_preprocessor.py` | Image processing |
| `src/utils/ocr_integrator.py` | OCR integration |

### Files to Modify
| File | Changes |
|------|---------|
| `app.py` | Add new API endpoints |
| `requirements.txt` | Add new dependencies |
| `src/models/models.py` | Add learning tables |
| `src/utils/section_extractor.py` | Integrate OCR |

---

## 6. New Dependencies
```
txt
# requirements.txt additions
pytesseract==0.3.10
opencv-python==4.8.1
pillow==10.1.0
scikit-learn==1.3.2
tensorflow==2.14.0  # For custom ML models
torch==2.1.0
torchvision==0.16.0
joblib==1.3.2
```

---

## 7. Configuration Options
```
python
# config.py additions
CONTINUOUS_LEARNING = {
    "enabled": True,
    "auto_retrain_threshold": 100,  # samples
    "approval_required": True
}

HANDWRITTEN_OCR = {
    "enabled": True,
    "tesseract_path": "/usr/bin/tesseract",
    "confidence_threshold": 0.6
}

MODEL_TRAINING = {
    "default_model": "spacy",
    "training_data_path": "./training_data",
    "output_model_path": "./models"
}
```

---

## 8. Estimated Time to Implement
- **Continuous Learning**: 3-4 days
- **Custom Model Training**: 4-5 days
- **Handwritten Recognition**: 3-4 days
- **Total**: ~2 weeks
