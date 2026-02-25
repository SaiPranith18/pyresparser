# TODO - Name Extraction Enhancement

## Task
Add logic to check first 5 lines for bold text (font_size >= 12) as an EXTRA method for name extraction.

## Steps:
- [x] 1. Read and understand existing code in app.py and related files
- [ ] 2. Add function to extract text with font size from PDF using pdfminer
- [ ] 3. Modify extract_name_with_filename_fallback to include bold text check
- [ ] 4. Test the implementation

## Implementation Details:
- Use pdfminer to extract text with font size information
- Check first 5 lines for bold text (font_size >= 12)
- Add as an extra extraction method in the pipeline
