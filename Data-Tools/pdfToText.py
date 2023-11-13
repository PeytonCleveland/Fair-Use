# Python script for converting pdfs to txt files.
#   S3 is used for all file storage.  Set input 
#   and out put locations at the S3 Functions
#   below.
#
#   D.Kuhl
#======================================

import os
import time
import fitz                     # PyMuPDF library
import re
# import docx2txt
# from ebooklib import epub
from subprocess import run
import boto3
import json


# ======================================
# S3 Functions
# ======================================

s3c = boto3.client('s3', region_name='us-gov-west-1')
s3r = boto3.resource('s3', region_name='us-gov-west-1')

bucket_name = "ocelot-data-input"
import_subfolder = "Input/AF-Epub/36-personnel/"        # do not start with "/"
complete_subfolder = "Input/AF-Epub/COMPLETED/36-personnel/"
export_subfolder = "Output/AF-Epub/36-personnel/"
error_subfolder = "Error/"


def s3_list(file_path):
    keySet = []
    # Get list of files from a given s3 location
    bucket = s3r.Bucket(bucket_name)
    b_objects = bucket.objects.filter(Prefix=file_path)
    for obj in b_objects:
        keySet.append(obj.key)

    return keySet


def s3_get(file_key):
    # Retrieves file from S3 bucket for conversion
    file_name = file_key.split("/")[-1]
    s3c.download_file(bucket_name, file_key, file_name)


def s3_put(file_key):
    # Push text file to S3 bucket
    file_name = file_key.split("/")[-1]
    s3c.upload_file(file_name, bucket_name, file_key)


def s3_set_complete(file_key):
    # Update source file with completed tag
    file_name = file_key.split("/")[-1]
    completed_key = complete_subfolder + file_name
    source_block = {
        "Bucket": bucket_name,
        "Key": file_key
    }
    try:
        s3r.meta.client.copy(source_block, bucket_name, completed_key)
        print(f"Document moved to completed directory: {completed_key}")
    except Exception as e:
        print(f"Failed to copy S3 objects because of {e}")
    else:
        s3r.meta.client.delete_object(Bucket=bucket_name, Key=file_key)


def s3_set_error(file_key):
    # Update source file with error tag
    file_name = file_key.split("/")[-1]
    error_key = error_subfolder + file_name
    source_block = {
        "Bucket": bucket_name,
        "Key": file_key
    }
    try:
        s3r.meta.client.copy(source_block, bucket_name, error_key)
        print(f"Document moved to error directory: {error_key}")
    except Exception as e:
        print(f"Failed to copy S3 objects because of {e}")
    else:
        s3r.meta.client.delete_object(Bucket=bucket_name, Key=file_key)

    return error_key


# ======================================
# Text Processing Functions
# ======================================


def set_file_processor(file_key):
    extension = os.path.splitext(file_key)[1]

    FILE_PROCESSORS = {
    '.pdf': extract_text_from_pdf,
    # '.docx': extract_text_from_word,
    '.docx': coming_soon,
    # '.doc': extract_text_from_doc,
    '.doc': coming_soon,
    # '.epub': extract_text_from_epub
    '.epub': coming_soon
    }

    fp = FILE_PROCESSORS.get(extension)
    return fp


def coming_soon(file_key):
    print(f"Document format is currently not processed.  Skipping {file_key}.")


def clean_text(text):
    text = text.replace("�", " ")
    text = text.replace('\f', '')
    text = re.sub(r'(\s*\.\s*){2,}', ' ', text)
    text = re.sub(r'_+', ' ', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'(?i)this page intentionally left blank', '', text)
    # text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '', text)
    # text = re.sub(r'(\(?\d{3}\)?)?[\s|-]?\d{3}-\d{4}', ' XXX-XXX-XXXX ', text)      # phone numbers
    # text = re.sub('[\u00B9\|\u00B2\|\u00B3\|\u2074\|\u2075\|\u2076\|\u2077\|\u2078\|\u2079|\u2070]', '', text) # superscript 0-9
    # text = re.sub(r'\b\d{1,4}\b', '', text)
    # Remove any excess spaces
    # text = re.sub(r'\s{2,}', ' ', text)

    return text.strip()


def remove_copyright_paragraphs(text):
    """Remove copyright related paragraphs."""
    pattern = r'(?:Copyright ©|All rights reserved\.)\s.*?\n'
    return re.sub(pattern, '', text, flags=re.DOTALL)


def extract_text_from_pdf(file_key):
    pdf_name = file_key.split("/")[-1]
    out_filename = pdf_name.replace('.pdf','.txt')
    try:
        doc = fitz.open(pdf_name)
        with open(out_filename, "wb") as out:
            for page in doc:
                try:
                    text = page.get_text()
                    cleaned_text = clean_text(text)
                    cleaned_text = remove_copyright_paragraphs(cleaned_text)
                    out.write(cleaned_text.encode("utf8"))
                    # out.write(bytes((12,)))
                    out.write(b'\n')
                except Exception:
                    print(f"Error processing page {page.number} of {pdf_path}")
        doc.close()
        # Test for successful conversion
        test = open(out_filename, 'r')
        textData = test.read()
        word_count = len(textData.split())
        if word_count < 100:
            out_filename = transform_with_ocr(file_key)

        return out_filename      # return file name for testing the file

    except Exception as e:
        print(f"File failed to open:  {e} ")
        out_filename = "ERROR"
        return out_filename      # return file name for testing the file


def transform_with_ocr(file_key):
    # Transforms a single file with OCR.
    # Extract the file name without extension and the directory
    pdf_name = file_key.split("/")[-1]
    out_filename = pdf_name.replace('.pdf','.txt')
    try:
        run(['ocrmypdf', '--force-ocr', pdf_name, out_filename])
    except Exception as e:
            print(f"Error with OCR conversion of {file_key}")
            print(f"Error message: {e}")
            out_filename = "ERROR"

    return out_filename


'''
    # COMING SOON!

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


def extract_text_from_epub(file_key):
    book = epub.read_epub(epub_path)
    text = ''
    for item in book.items:
        if item.get_type() == 9:  # Check if item is of type 'text'
            text += item.content.decode("utf-8")

    # We might need more cleaning depending on EPUB's HTML structure
    cleaned_text = clean_text(text)
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(cleaned_text)

'''


def lambda_handler(event, context):
    try:
        # Get the S3 file key from the event
        # s3_event = event['Records'][0]['s3']
        # file_key = s3_event['object']['key']

        # Call main with the specific file key
        main()

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


# ==============================================
# Main - Converting pdf documents to text files
# ==============================================

# A few variables are defined above in the S3 section

def main():

    # Control lists
    convert_list = []
    # success_list = []       # not sure this is a need for these
    # failure_list = []

    # Get list of documents tagged with import keys
    convert_list = s3_list(import_subfolder)
    # print(convert_list)

    for document_key in convert_list:
        # Retrieve
        print(f"Retrieving {document_key}")
        s3_get(document_key)

        # Convert
        # Identify the processor based on file extension
        file_processor = set_file_processor(document_key)
        print(f"processor picked for {document_key}")
        if not file_processor:
            print(f"No processor found for file: {document_key}")
            return

        # Execute the file_processor, returns name of converted document unless error
        text_filename = file_processor(document_key)
        if text_filename ==  "ERROR" :
            print(f"Error processing file. Moving it to: {error_subfolder} ")
            s3_set_error(document_key)
        else:
            print(f"Created {text_filename}")
            s3_set_complete(document_key)

        # Publish
        if text_filename !=  "ERROR" :
            upload_key = export_subfolder + text_filename
            s3_put(upload_key)
            print(f"Converted text file has been uploaded to the S3 location: {upload_key}")

        # Clean up
        pdf_filename = document_key.split("/")[-1]
        os.remove(pdf_filename)
        if text_filename !=  "ERROR" :
            os.remove(text_filename)


if __name__ == "__main__":
    main()


