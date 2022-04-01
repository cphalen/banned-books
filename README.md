# ENG 98: Banned Books Final Project

### Description

In this final project for Data Science in the Humanities (ENG 98) we analyze [Anne Haight's banned book list](https://www.gutenberg.org/ebooks/bookshelf/336) on Project Gutenberg.

### Execution

To run the web scraper and download the book corpus from Project Gutenberg run the following commands:
```
pipenv install
pipenv run python scrape.py
```
the texts will be downloaded to `/books` and the metadata about the texts will be stored in Excel format as `metadata.xlsx`.