import os
import pandas as pd
import fitz
import re
from docx import Document
from win32com import client as win32client  # For DOC extraction
from ebooklib import epub  # For EPUB extraction
from subprocess import run
import boto3


# ======================================
# S3 Functions
# ======================================

s3 = boto3.client('s3', region_name='us-gov-west-1')

BUCKET_NAME = "ocelot-data-input"
IMPORT_SUBFOLDER = "Import"
EXPORT_SUBFOLDER = "Export"


def read_from_s3(file_key):
    """Reads a file from S3 given its key."""
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
    content = obj['Body'].read().decode('utf-8')
    return content


def save_to_s3(data, file_key):
    """Writes data to an S3 file given its key."""
    s3.put_object(Body=data, Bucket=BUCKET_NAME, Key=file_key)


def list_files_in_s3_subfolder(subfolder_name):
    """Lists all files in a specific S3 subfolder."""
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=subfolder_name)
    return [item['Key'] for item in response.get('Contents', [])]


# ======================================
# Functions
# ======================================


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


def lambda_handler(event, context):
    try:
        # Get the S3 file key from the event
        s3_event = event['Records'][0]['s3']
        file_key = s3_event['object']['key']

        # Call main with the specific file key
        main(file_key)

        return {
            'statusCode': 200,
            'body': json.dumps('Text extraction completed successfully!')
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Failed due to: {str(e)}")
        }

# ======================================
# Main
# ======================================


FILE_PROCESSORS = {
    '.pdf': extract_text_from_pdf,
    '.docx': extract_text_from_word,
    '.doc': extract_text_from_doc,
    '.txt': lambda content: content,
    '.epub': extract_text_from_epub
}


def main(file_key):
    # excluding the folder name
    file_name = file_key.split('/')[-1]
    out_file = file_name

    # Use the read_from_s3 function to read file content
    file_content = read_from_s3(file_key)

    # Identify the processor based on file extension
    file_processor = FILE_PROCESSORS.get(os.path.splitext(out_file)[1])

    if not file_processor:
        print(f"No processor found for file: {out_file}")
        return

    extracted_text = file_processor(file_content)

    # Special case for PDFs where we may use OCR
    if out_file.endswith('.pdf'):
        word_count = len(extracted_text.split())
        if word_count < 100:
            ocr_processed_file_content = transform_with_ocr(file_content)
            extracted_text = file_processor(ocr_processed_file_content)

    # Determine the output text file name
    out_file_txt = os.path.splitext(out_file)[0] + '.txt'
    output_text_key = f"{EXPORT_SUBFOLDER}/{out_file_txt}"

    save_to_s3(extracted_text, output_text_key)
