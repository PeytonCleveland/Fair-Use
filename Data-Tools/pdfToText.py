import os
import io
import pandas as pd
import fitz
import re
import docx2txt
from ebooklib import epub
from subprocess import run
import boto3
import json


# ============================
# Mode Selector
# ============================
S3_MODE = False  # Set to True for S3, False for local


# ============================
# Local Directory Paths (Modify as needed)
# ============================
LOCAL_DIRECTORY = r"C:\Users\Deft\Desktop\Devlopment\pdf_to_text\Datafolder"

IMPORT_SUBFOLDER = "Test/Import/"
EXPORT_SUBFOLDER = "Test/Export/"
IMPORT_DIRECTORY = os.path.join(LOCAL_DIRECTORY, IMPORT_SUBFOLDER)
EXPORT_DIRECTORY = os.path.join(LOCAL_DIRECTORY, EXPORT_SUBFOLDER)

# ============================
# Local I/O Functions
# ============================


def read_from_local(file_key):
    """Reads a file from local directory given its key."""
    try:
        with open(os.path.join(IMPORT_DIRECTORY, file_key), 'rb') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(os.path.join(IMPORT_DIRECTORY, file_key), 'r', encoding='latin-1') as f:
            return f.read()


def save_to_local(data, file_key):
    """Writes data to a local file given its key."""
    print(f"EXPORT_DIRECTORY: {EXPORT_DIRECTORY}")
    print(f"file_key: {file_key}")
    print(f"Final path: {os.path.join(EXPORT_DIRECTORY, file_key)}")
    os.makedirs(os.path.dirname(os.path.join(
        EXPORT_DIRECTORY, file_key)), exist_ok=True)
    with open(os.path.join(EXPORT_DIRECTORY, file_key), 'w', encoding='utf-8') as f:
        f.write(data)

# ======================================
# S3 Functions
# ======================================


s3 = boto3.client('s3', region_name='us-gov-west-1')

BUCKET_NAME = "ocelot-data-input"
IMPORT_SUBFOLDER = "Test/Import/"
EXPORT_SUBFOLDER = "Test/Export/"


def read_from_s3(file_key):
    """Reads a file from S3 given its key."""
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
    content = obj['Body'].read()
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


def extract_text_from_pdf(file_content, output_text_key=None):
    # Convert the file content to an in-memory byte stream
    pdf_stream = io.BytesIO(file_content)

    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    text_content = []

    for page in doc:
        try:
            text = page.get_text()
            cleaned_text = clean_text(text)
            cleaned_text = remove_copyright_paragraphs(cleaned_text)
            text_content.append(cleaned_text)
        except Exception:
            print(f"Error processing page {page.number}")
    doc.close()
    return "\n".join(text_content)


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
        # Using docx2txt to extract text
        text = docx2txt.process(doc_path)
        cleaned_text = clean_text(text)
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(cleaned_text)
    except Exception as e:
        print(f"Failed to process {os.path.basename(doc_path)}: {e}")


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

    # Extract the file name without extension
    file_name_no_ext = os.path.splitext(os.path.basename(input_filename))[0]

    # Determine the full path of the input file using the IMPORT_DIRECTORY
    input_file_path = os.path.join(IMPORT_DIRECTORY, input_filename)

    # Define the output filename to be in the EXPORT_DIRECTORY
    output_filename = os.path.join(
        EXPORT_DIRECTORY, file_name_no_ext + " OCR processed.pdf")

    # Check if the output file already exists, if so, append a timestamp or number
    if os.path.exists(output_filename):
        import time
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_filename = os.path.join(
            EXPORT_DIRECTORY, file_name_no_ext + f" OCR processed {timestamp}.pdf")

    run(['ocrmypdf', '--force-ocr', input_file_path, output_filename])
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
    # Excluding the folder name
    file_name = file_key.split('/')[-1]
    out_file = file_name

    # Decide on the read function based on the mode
    if S3_MODE:
        file_content = read_from_s3(file_key)
    else:
        file_content = read_from_local(file_key)

    # Identify the processor based on file extension
    file_processor = FILE_PROCESSORS.get(os.path.splitext(out_file)[1])

    if not file_processor:
        print(f"No processor found for file: {out_file}")
        return

    # Determine the output text file name
    out_file_txt = os.path.splitext(out_file)[0] + '.txt'
    output_text_key = os.path.join(EXPORT_DIRECTORY, out_file_txt)

    # Use the identified file processor
    if not out_file.endswith('.pdf'):
        extracted_text = file_processor(file_content, output_text_key)
    else:
        # Special case for PDFs where we may use OCR
        extracted_text = file_processor(file_content, output_text_key)
        word_count = len(extracted_text.split())
        if word_count < 100:
            ocr_processed_file_path = transform_with_ocr(file_name)
            ocr_processed_file_content = read_from_local(
                ocr_processed_file_path)
            extracted_text = file_processor(
                ocr_processed_file_content, output_text_key)

    # Save based on the mode
    if S3_MODE:
        save_to_s3(extracted_text, output_text_key)
    else:
        save_to_local(extracted_text, output_text_key)


##############################################
# Uncomment the following to run locally
##############################################
if __name__ == "__main__":
    for file_name in os.listdir(IMPORT_DIRECTORY):
        file_path = os.path.join(IMPORT_DIRECTORY, file_name)
        print(f"Processing {file_path} ...")
        main(file_name)
