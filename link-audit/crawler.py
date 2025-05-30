import requests
from bs4 import BeautifulSoup
class Crawler:
    def __init__(self, url):
        self.url = url

    def crawl(self):
        print(f"Crawling {self.url}...")

    def get_links(self):
       