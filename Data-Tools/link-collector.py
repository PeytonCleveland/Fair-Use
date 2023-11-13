# Python script for scraping links from 
#   html based websites.  Input is a single
#   url (currently inline in code).  
#   Output is a list of urls.
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
        os.mknod(file_path)                 # Change this if you are not on Linux

    with open(file_path, "w") as file:
        for url in url_list:
            file.write(f"{url}")
            file.write(f"\n")
    file.close()


# ==============================================
# Main - Rendering html sites to text files
# ==============================================

# url = "https://www.acquisition.gov/far/"
# url = "https://www.acquisition.gov/dfars"
url = "https://www.e-publishing.af.mil/Product-Index/#/?view=pubs&orgID=10141&catID=1&series=-1&modID=449&tabID=131"
# url = "https://www.e-publishing.af.mil/Product-Index/"



outfile_path = r"/home/da5id/OmniFed/temp/out-links.txt"


def link_collector():
    session = HTMLSession()
    response = session.get(url)
    links = response.html.absolute_links
    write_urls(links, outfile_path)



if __name__ == "__main__":
    main()


