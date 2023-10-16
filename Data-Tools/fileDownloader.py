# Python script for downloading files (pdfs)
#   from a list of urls
#   D.Kuhl
#======================================

import os
import time
import requests
from tqdm import tqdm

#======================================
# Functions

def collect_urls(file_path):
    url_list = []
    with open(file_path, "r", encoding="utf8") as file:
        for line in file:
            url = line.strip()
            url_list.append(url)

    return url_list

def download_url(url, fn):
    t0 = time.time()
    try:
        r = requests.get(url)
        with open(fn, 'wb') as f:
            f.write(r.content)
        return(url, time.time() - t0)
    except Exception as e:
        print('Exception in download_url():', e)


#======================================
def main():
    # Define source of links and download location:
    link_source_file = r"C:\Users\david\Documents\WorkingDir\guidance-docs.txt"
    download_dir = r"C:\Users\david\Documents\WorkingDir\downloads"

    # Ensure the download directory exists
    downloads = os.path.dirname(download_dir)
    if not os.path.exists(downloads):
        os.makedirs(downloads)

    # Get the list
    url_list = collect_urls(link_source_file)

    # Loop through the list and download in parallel
    for url in tqdm(url_list):
        # Get the filename for output
        file_raw = os.path.basename(url)
        out_filename = file_raw.split("?")[0]
        out_path = os.path.join(download_dir, out_filename)
        download_url(url, out_path)


if __name__ == "__main__":
    main()

