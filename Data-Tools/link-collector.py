# Python script for scraping links from 
#   html based websites.  Input is a single
#   url.  Output is a list of urls.
#
#   D.Kuhl
#======================================

import os
import re
from requests_html import HTMLSession

# ======================================
# Functions
# ======================================

# Write URLs to list
def write_urls(url_list, file_path):
    if not os.path.exists(file_path):
        os.mknod(file_path)

    with open(file_path, "w") as file:
        for url in url_list:
            file.write(f"{url}")
            file.write(f"\n")
    file.close()


# ==============================================
# Main - Rendering html sites to text files
# ==============================================

# url = "https://www.acquisition.gov/far/"
url = "https://www.acquisition.gov/dfars"

outfile_path = r"/home/da5id/OmniFed/pseudoBucket/htmlSets/out-links.txt"


def main():
    session = HTMLSession()
    response = session.get(url)
    links = response.html.absolute_links
    write_urls(links, outfile_path)



if __name__ == "__main__":
    main()


