import pdfminer
import re
import os

from pdfminer.high_level import extract_text
from nlp_utils import extract_name_nlp
from flask import Flask,request

def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

def extract_name_from_resume(text):
    name = None
    UPLOAD_FOLDER="uploads"

    
    pattern = r"(\b[A-Z]+\b)\s(\b[A-Z]+\b)"
    match = re.search(pattern, text)
    if match:
        name = match.group()

    return name

if __name__ == '__main__':
    
    file = request.files["resume"]
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    text = extract_text_from_pdf(file_path)
    name = extract_name_nlp(text)

    if name:
        print("Name:", name)
    else:
        print("Name not found")


