from multiprocessing.sharedctypes import Value
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from time import sleep
import re
import os
import zipfile

# constants
links_path = "src/links.txt"
excel_path = "metadata.xlsx"
target_path = "books"
metadata_fields = [
    "Author",
    "Title",
    "Language",
    "Subject",
    "Release Date",
    "Copyright Status",
]

# helper functions
def parse_name(name: str) -> dict:
    last_first_prefix_range = r"([^,]+), ([^,]+), ([^,]+), ([0-9-ADBCE ?]+)"
    last_first_range = r"([^,]+), ([^,]+), ([0-9-ADBCE ?]+)"
    last_range = r"([^,]+), ([0-9-ADBCE ?]+)"
    formatted = {}

    if (m := re.match(last_first_prefix_range, name)) is not None:
        # just ignore the prefix if it exists
        formatted["name"] = f"{m.group(2)} {m.group(1)}"
        formatted["lifespan"] = m.group(4)
    elif (m := re.match(last_first_range, name)) is not None:
        formatted["name"] = f"{m.group(2)} {m.group(1)}"
        formatted["lifespan"] = m.group(3)
    elif (m := re.match(last_range, name)) is not None:
        formatted["name"] = m.group(1)
        formatted["lifespan"] = m.group(2)
    else:
        formatted["name"] = name
        formatted["lifespan"] = None

    return formatted


def wiki_lookup(name: str) -> str:
    query = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={name}"
    resp = requests.get(query).json()
    
    pages = resp.get("query", {}).get("search")
    if len(pages) == 0:
        return None
    pageid = pages[0].get("pageid", None)
    if pageid is None:
        return None
    
    return f"http://en.wikipedia.org/?curid={pageid}"


def wiki_author_country_of_origin(name: str) -> str:
    url = wiki_lookup(name)
    if url is None:
        return None
    wiki = requests.get(url)
    soup = BeautifulSoup(wiki.content, "lxml")
    born = soup.find("th", text="Born")

    if born is None:
        return None

    td = born.parent.find("td")
    # <br> tag and semicolon don't format in Excel so use newline instead
    for br in td.find_all("br"):
        br.replace_with("\n")

    location = td.text.split("\n")[-1]
    return location.split(",")[-1].strip()


def wiki_publication_date(title: str) -> str:
    url = wiki_lookup(title)
    if url is None:
        return None
    wiki = requests.get(url)
    soup = BeautifulSoup(wiki.content, "lxml")
    date = soup.find("th", text="Publication date")
    if date is None:
        return None
    return date.parent.find("td").text


# read in links from src/links.txt
with open(links_path, "r") as file:
    links = list(map(lambda x: x.strip(), file.readlines()))

books = []

# make books directory if it doesn't exist
if not os.path.isdir(target_path):
    os.mkdir(target_path)

# grab metadata and download books
for i, link in enumerate(links):
    book = {}
    resp = requests.get(link)
    soup = BeautifulSoup(resp.content, "lxml")

    table = soup.find("table", {"class": "bibrec"})
    for field in metadata_fields:
        row = table.find("th", text=field)
        element = row.parent.find("td")

        # <br> tag and semicolon don't format in Excel so use newline instead
        for br in element.find_all("br"):
            br.replace_with("\n")
        content = element.text.strip()
        content.replace(";", "\n")

        # reformat the Gutenberg author field
        if field == "Author":
            name_data = parse_name(content)
            content = name_data["name"]
            book["Lifespan"] = name_data["lifespan"]
            book["Author Country of Origin"] = wiki_author_country_of_origin(content)

        # sometimes books have subtitles
        if field == "Title" and len(content.split("\n")) > 1:
            [title, subtitle, *_] = content.split("\n")
            content = title

            # splice out leading "or" before subtitle on certain pages
            if subtitle.startswith("Or, "):
                subtitle = subtitle[len("Or, ") :]
            elif subtitle.startswith("or, "):
                subtitle = subtitle[len("or, ") :]
            elif subtitle.startswith("Or "):
                subtitle = subtitle[len("Or ") :]
            elif subtitle.startswith("or "):
                subtitle = subtitle[len("or ") :]

            book["Subtitle"] = subtitle
            book["Publication Date"] = wiki_publication_date(content)
        elif field == "Title":
            book["Subtitle"] = ""
            book["Publication Date"] = wiki_publication_date(content)
        book[field] = content.strip()

    # skip non-English books as they will be difficult for us to analyze
    if book["Language"] != "English":
        continue

    print(f"Downloading {book['Title']} ({i + 1}/{len(links)})")
    save_path = f"{target_path}/{book['Title']}.txt"
    download_link = f"{link}.txt.utf-8"
    source = requests.get(download_link)
    with open(save_path, "wb") as file:
        # # assume that no book will have a title that is more than 4 lines long
        # regex = r"\*\*\*(.*\n){0,4}.*\*\*\*"

        # # cut out the section of the txt file that is actually the story
        # # (and not the Gutenberg legal preface/addendum)
        # sections = re.split(regex, text)
        # if len(sections) >= 3:
        #     content = "\n".join(
        #         map(lambda x: "" if x is None else x.strip(), sections[1:-1])
        #     )
        file.write(source.content)

    book["Download Link"] = f'=HYPERLINK("{download_link}")'
    book["Gutenberg Link"] = f'=HYPERLINK("{link}")'
    books.append(book)

    # this sleep  makes the script a lot longer and can be removed
    # but Gutenberg is free and they request it in their robots.txt
    # file (https://gutenberg.org/robots.txt) so unless you're in a hurry
    # leave it for net politeness
    # sleep(5)

# marshal metadata into Excel
wb = Workbook()
ws = wb.active

# add column names
ws.append(list(books[0].keys()))

# add row level data
for book in books:
    ws.append(list(book.values()))

# save workbook to metadata.xlsx
wb.save(excel_path)

# zip /books directory for easy upload
with zipfile.ZipFile("books.zip", "w") as books_zip:
    for dirname, _, files in os.walk("books"):
        books_zip.write(dirname)
        for filename in files:
            books_zip.write(os.path.join(dirname, filename))
