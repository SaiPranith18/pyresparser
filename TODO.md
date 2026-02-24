# Folder Reorganization Plan

## Task: Format the messy folder structure - COMPLETED ✓

### Summary:
The folder structure has been successfully reorganized from a messy flat structure to a clean modular structure.

### New Structure:
```
pyresparser/
├── app.py                    # Main Flask app (kept in root)
├── requirements.txt
├── TODO.md
├── src/                      # Source code package
│   ├── __init__.py
│   ├── extractors/           # PDF extraction modules
│   │   ├── __init__.py
│   │   ├── layoutlm_extractor.py
│   │   ├── pdf_layout_extractor.py
│   │   ├── pdf_layout_improved.py
│   │   └── transformers_extractor.py
│   ├── models/               # Data models
│   │   ├── __init__.py
│   │   ├── certifications.py
│   │   ├── education.py
│   │   ├── experience.py
│   │   ├── models.py
│   │   ├── name.py
│   │   ├── projects.py
│   │   └── skills.py
│   └── utils/                # Utility functions
│       ├── __init__.py
│       ├── formatter.py
│       ├── headings.py
│       ├── name_database.py
│       ├── new_sections.py
│       ├── nlp_utils.py
│       ├── performance.py
│       ├── section_extractor.py
│       ├── structured_output.py
│       └── text.py
├── static/
│   └── style.css
├── templates/
│   ├── index.html
│   └── preview.html
├── instance/
│   └── resumes.db
├── uploads/
│   └── *.pdf files
└── docs/                     # Documentation (empty - created)
    └── (empty)
```

### Files Moved:
1. Extractors → src/extractors/
2. Models → src/models/
3. Utils → src/utils/

### Imports Updated:
All imports in app.py have been updated to use the new src/ path structure.
