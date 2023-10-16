# Python script for downloading files (pdfs)
#   from a list of urls
#   D.Kuhl
#======================================

import os
import re
import boto3
import html2text        # add to requirements
import requests
import requests-html
import lxml.html


# ======================================
# S3 Functions
# ======================================

s3c = boto3.client('s3', region_name='us-gov-west-1')
s3r = boto3.resource('s3', region_name='us-gov-west-1')

bucket_name = "ocelot-data-input"
# do not start subdirectory path with "/"
# import_subfolder = "Test/Import/"        For website sources there is no input bucket
export_subfolder = "Test/Export/"
complete_subfolder = "Test/Complete/"
error_subfolder = "Test/Error/"


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
# Other Functions
# ======================================

# Get URLs from list
def collect_urls(file_path):
    url_list = []
    with open(file_path, "r", encoding="utf8") as file:
        for line in file:
            url = line.strip()
            url_list.append(url)

    return url_list


# Grab the title from the site being read
def title_to_filename(site_object):
    tree = lxml.html.fromstring(site_object.text)
    title_elem = tree.xpath('//title')[0]
    title = title_elem.text_content()
    name_alum = re.sub('\W+', '_', title)[:80]      # limiting file names to 80 chars

    return name_alum


# Cleaning junk text
def clean_text(text):
    text = text.replace("�", " ")
    text = text.replace('\f', '')
    text = re.sub(r'(\s*\.\s*){2,}', ' ', text)
    text = re.sub(r'_+', ' ', text)
    text = re.sub(r'\b\d{1,4}\b', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'(?i)this page intentionally left blank', '', text)
    text = re.sub(r'(?i)leave this field blank', '', text)
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '', text)
    text = re.sub(r'(\(?\d{3}\)?)?[\s|-]?\d{3}-\d{4}', ' XXX-XXX-XXXX ', text)      # phone numbers
    text = re.sub('[\u00B9\|\u00B2\|\u00B3\|\u2074\|\u2075\|\u2076\|\u2077\|\u2078\|\u2079|\u2070]', '', text) # superscript 0-9

    return text.strip()


def remove_copyright_paragraphs(text):
    """Remove copyright related paragraphs."""
    pattern = r'(?:Copyright ©|All rights reserved\.)\s.*?\n'
    return re.sub(pattern, '', text, flags=re.DOTALL)


# ==============================================
# Main - Converting pdf documents to text files
# ==============================================

# A few variables are defined above in the S3 section
link_source_file = r"/home/da5id/OmniFed/pseudoBucket/htmlSets/far-data-links.txt"
out_location = r"/home/da5id/OmniFed/pseudoBucket/htmlOutText/"


def main():

    source_list = collect_urls(link_source_file)
    processor = html2text.HTML2Text()
    processor.ignore_links = True                   # filter out the links

    # Iterate through the source_list
    for url in source_list:
        site = requests.get(url)
        out_filename = title_to_filename(site)
        text_raw = processor.handle(site)
        text_clean = clean_text(text_raw)
        out_path = out_location + out_filename








if __name__ == "__main__":
    main()


