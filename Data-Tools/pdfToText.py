import fitz
import os
import re
from docx import Document
from win32com import client as win32client  # For DOC extraction
from ebooklib import epub  # For EPUB extraction


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
            out_file = out_file.replace('.pdf', '.txt')
            output_text_path = os.path.join(output_path, out_file)
            extract_text_from_pdf(input_file_path, output_text_path)
        elif out_file.endswith('.docx'):
            out_file = out_file.replace('.docx', '.txt')
            output_text_path = os.path.join(output_path, out_file)
            extract_text_from_word(input_file_path, output_text_path)
        elif out_file.endswith('.doc'):
            out_file = out_file.replace('.doc', '.txt')
            output_text_path = os.path.join(output_path, out_file)
            extract_text_from_doc(input_file_path, output_text_path)
        elif out_file.endswith('.txt'):
            # No extraction needed, just copying the text file to output directory
            os.copy(input_file_path, os.path.join(output_path, out_file))
        elif out_file.endswith('.epub'):
            out_file = out_file.replace('.epub', '.txt')
            output_text_path = os.path.join(output_path, out_file)
            extract_text_from_epub(input_file_path, output_text_path)


if __name__ == "__main__":
    main()
