import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
import re

links_path = "src/links.txt"
excel_path = "metadata.xlsx"
metadata_fields = ["Author", "Title", "Language", "Subject", "Release Date", "Copyright Status"]

with open(links_path, 'r') as file:
    links = list(map(lambda x: x.strip(), file.readlines()))

books = []

# grab metadata and download books
for i, link in enumerate(links):
    book = {}
    resp = requests.get(link)
    soup = BeautifulSoup(resp.content, "lxml")
    
    table = soup.find("table", {'class': 'bibrec'})
    for field in metadata_fields:
        row = table.find("th", text=field)
        element = row.parent.find("td")
        for br in element.find_all("br"):
            br.replace_with("\n")
        content = element.text.strip()
        print(content)
        # sometimes books have subtitles
        if field == "Title" and len(content.split("\n")) > 1:
            [title, subtitle, *_] = content.split("\n")
            content = title
            book["Subtitle"] = subtitle
        else:
            book["Subtitle"] = ""

        book[field] = content

    print(f"Downloading {book['Title']} ({i + 1}/{len(links)})")
    save_path = f"books/{book['Title']}.txt"
    download_link = f"{link}.txt.utf-8"
    source = requests.get(download_link)
    with open(save_path, "w") as file:
        text = source.content.decode("utf-8")
        sections = re.split(r"\*\*\*.+\*\*\*", text)
        if len(sections) >= 3:
            content = sections[1].strip()
        else:
            continue
        file.write(content)

    book["Download Link"] = f"=HYPERLINK(\"{download_link}\")"
    book["Gutenberg Link"] = f"=HYPERLINK(\"{link}\")"
    books.append(book)

# marshal metadata into Excel
wb = Workbook()
ws = wb.active

# add column names
ws.append(list(books[0].keys()))

# add row level data
for book in books:
    ws.append(list(book.values()))

wb.save(excel_path)