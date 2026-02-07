import pdfminer
import re


from pdfminer.high_level import extract_text

def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

def extract_education_from_resume(text):
    education = []

    # Use regex pattern to find education information
    pattern = r"(?i)(?:(?:Bachelor|B\.S\.|B\.A\.|B\.Tech\.|Master|M\.S\.|M\.A\.|Ph\.D\.)\s(?:[A-Za-z]+\s)*[A-Za-z]+)"
    matches = re.findall(pattern, text)
    for match in matches:
        education.append(match.strip())

    return education

if __name__ == '__main__':
    text = extract_text_from_pdf(r"C:\Users\hp\Downloads\Sai Praneet (2) (1) (2).pdf")

    extracted_education = extract_education_from_resume(text)
    if extracted_education:
        print("Education:", extracted_education)
    else:
        print("No education information found")