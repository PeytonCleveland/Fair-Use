# Python script for converting pdf documents to
#   raw text.
#   C.Robson / D.Kuhl
#======================================

import fitz
import os
import re


#======================================
# Functions
def clean_text(text):
    text = text.replace("�", " ")
    text = text.replace('\f', '')
    text = re.sub(r'(\s*\.\s*){2,}', ' ', text)
    text = re.sub(r'_+', ' ', text)
    text = re.sub(r'\b\d{1,4}\b', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'(?i)this page intentionally left blank', '', text)

    return text.strip()


def remove_copyright_paragraphs(text):
    pattern = r'(?:Copyright ©|All rights reserved\.)\s.*?\n'
    return re.sub(pattern, '', text, flags=re.DOTALL)


def collect_pdfs(folder_path):
    file_set = []
    for file in os.listdir(folder_path):
        if file.endswith('.pdf'):
            full_name = os.path.join(folder_path, file)
            file_name = os.path.basename(file)
            file_set.append({'full_name': full_name, 'file_name': file_name})

    return file_set


def extract_text_from_pdf(pdf_path, output_path):
    doc = fitz.open(pdf_path)

    with open(output_path, "wb") as out:
        for page in doc:
            text = page.get_text()
            cleaned_text = clean_text(text)

            # Remove copyright paragraphs
            cleaned_text = remove_copyright_paragraphs(cleaned_text)
            # cleaned_text = remove_copyright_paragraphs(text)

            out.write(cleaned_text.encode("utf8"))
            # Adds a form feed byte as separator for each page (optional, if you still want this)
            out.write(bytes((12,)))
    doc.close()


#======================================
def main():
    # Define your input PDF path and output text path here
    pdf_input_path = r"C:\Users\david\Documents\TestDocs"
    text_output_path = r"C:\Users\david\Documents\TextOut"

    # Ensure the output directory exists
    output_dir = os.path.dirname(text_output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    #Gather up pdf files
    pdf_collection = collect_pdfs(pdf_input_path)

    for pdf in pdf_collection:
        input_pdf_path = pdf['full_name']
        out_file = pdf['file_name'].replace('.pdf','.txt')
        output_text_path = os.path.join(text_output_path, out_file)

        extract_text_from_pdf(input_pdf_path, output_text_path)


if __name__ == "__main__":
    main()

