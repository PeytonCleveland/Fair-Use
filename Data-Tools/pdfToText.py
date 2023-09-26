import os
import pandas as pd
import fitz
import re
from docx import Document
from win32com import client as win32client  # For DOC extraction
from ebooklib import epub  # For EPUB extraction
from subprocess import run


# ======================================
# Functions

def clean_text(text):
    text = text.replace("�", " ")
    text = text.replace('\f', '')
    text = re.sub(r'(\s*\.\s*){2,}', ' ', text)
    text = re.sub(r'_+', ' ', text)
    text = re.sub(r'\b\d{1,4}\b', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'(?i)this page intentionally left blank', '', text)
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '', text)
    text = re.sub(r'\d{3}-\d{2}-\d{4}', 'XXX-XX-XXXX', text)

    # Remove any excess spaces
    # text = re.sub(r'\s{2,}', ' ', text)

    return text.strip()


def remove_copyright_paragraphs(text):
    """Remove copyright related paragraphs."""
    pattern = r'(?:Copyright ©|All rights reserved\.)\s.*?\n'
    return re.sub(pattern, '', text, flags=re.DOTALL)


def collect_files(folder_path, extensions):
    """Collect files with given extensions from a folder."""
    file_set = []
    try:
        for file in os.listdir(folder_path):
            if file.endswith(tuple(extensions)):
                full_name = os.path.join(folder_path, file)
                file_name = os.path.basename(file)
                file_set.append(
                    {'full_name': full_name, 'file_name': file_name})
    except OSError as err:
        print("Error: {} - {}".format(err.filename, err.strerror))

    return file_set


def extract_text_from_pdf(pdf_path, output_path):
    if os.path.exists(output_path):
        print(f"{os.path.basename(pdf_path)} already processed. Skipping...")
        return

    doc = fitz.open(pdf_path)
    with open(output_path, "wb") as out:
        for page in doc:
            try:
                text = page.get_text()
                cleaned_text = clean_text(text)
                cleaned_text = remove_copyright_paragraphs(cleaned_text)
                out.write(cleaned_text.encode("utf8"))
                out.write(bytes((12,)))
            except Exception:
                print(f"Error processing page {page.number} of {pdf_path}")
    doc.close()


def extract_text_from_word(docx_path, output_path):
    if os.path.exists(output_path):
        print(f"{os.path.basename(docx_path)} already processed. Skipping...")
        return

    doc = Document(docx_path)

    text = '\n'.join([p.text for p in doc.paragraphs])
    cleaned_text = clean_text(text)

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(cleaned_text)


def extract_text_from_doc(doc_path, output_path):
    if os.path.exists(output_path):
        print(f"{os.path.basename(doc_path)} already processed. Skipping...")
        return

    try:
        word_app = win32client.Dispatch('Word.Application')
        doc = word_app.Documents.Open(doc_path)
        text = doc.Content.Text
        cleaned_text = clean_text(text)
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(cleaned_text)
        doc.Close()
        word_app.Quit()
    except Exception as e:
        print(f"Failed to process {os.path.basename(doc_path)}: {e}")
        return


def extract_text_from_epub(epub_path, output_path):
    if os.path.exists(output_path):
        print(f"{os.path.basename(epub_path)} already processed. Skipping...")
        return

    book = epub.read_epub(epub_path)
    text = ''
    for item in book.items:
        if item.get_type() == 9:  # Check if item is of type 'text'
            text += item.content.decode("utf-8")

    # We might need more cleaning depending on EPUB's HTML structure
    cleaned_text = clean_text(text)
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(cleaned_text)


def transform_with_ocr(input_filename):
    """Transforms a single file with OCR."""
    print("Converting with OCR : " + os.path.basename(input_filename))

    # Extract the file name without extension and the directory
    file_dir = os.path.dirname(input_filename)
    file_name_no_ext = os.path.splitext(os.path.basename(input_filename))[0]

    # Define the output filename
    output_filename = os.path.join(
        file_dir, file_name_no_ext + " OCR processed.pdf")

    # Check if the output file already exists, if so, append a timestamp or number
    if os.path.exists(output_filename):
        import time
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_filename = os.path.join(
            file_dir, file_name_no_ext + f" OCR processed {timestamp}.pdf")

    run(['ocrmypdf', '--force-ocr', input_filename, output_filename])
    return output_filename


# ======================================
def main():
    # Define your input path and output text path here
    input_path = r"C:\Users\Deft\Desktop\Devlopment\pdf to text\Datafolder"
    output_path = r"C:\Users\Deft\Desktop\Devlopment\pdf to text\Dataoutputfolder"

    # Ensure the output directory exists
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    file_collection = collect_files(
        input_path, ['.pdf', '.docx', '.doc', '.txt', '.epub'])

    for file in file_collection:
        input_file_path = file['full_name']
        out_file = file['file_name']

        if out_file.endswith('.pdf'):
            out_file_txt = out_file.replace('.pdf', '.txt')
            output_text_path = os.path.join(output_path, out_file_txt)
            extract_text_from_pdf(input_file_path, output_text_path)

            # Checking word count and decide if to process with OCR
            with open(output_text_path, 'r', encoding="utf-8") as f:
                word_count = len(f.read().split())

            # Close the file explicitly, if not using a with statement
            f.close()

            if word_count < 100:
                ocr_processed_file = transform_with_ocr(input_file_path)
                # Delete the initial output text file
                if os.path.exists(output_text_path):
                    os.remove(output_text_path)
                extract_text_from_pdf(ocr_processed_file, output_text_path)

        elif out_file.endswith('.docx'):
            out_file_txt = out_file.replace('.docx', '.txt')
            output_text_path = os.path.join(output_path, out_file_txt)
            extract_text_from_word(input_file_path, output_text_path)
        elif out_file.endswith('.doc'):
            out_file_txt = out_file.replace('.doc', '.txt')
            output_text_path = os.path.join(output_path, out_file_txt)
            extract_text_from_doc(input_file_path, output_text_path)
        elif out_file.endswith('.txt'):
            os.copy(input_file_path, os.path.join(output_path, out_file))
        elif out_file.endswith('.epub'):
            out_file_txt = out_file.replace('.epub', '.txt')
            output_text_path = os.path.join(output_path, out_file_txt)
            extract_text_from_epub(input_file_path, output_text_path)


if __name__ == "__main__":
    main()
