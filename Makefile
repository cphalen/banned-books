install:
	pipenv install

scrape:
	pipenv run python scrape.py

clean:
	rm -rf books
	rm -f books.zip
	rm -f metadata.xlsx
	rm -f \~\$metadata.xlsx