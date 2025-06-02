import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, urldefrag
from creepycrawler.linkgraph import LinkGraph
import sys
from .helpers import Logger
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, urldefrag
from creepycrawler.linkgraph import LinkGraph
from .helpers import Logger

class Crawler:
    def __init__(self, base_url, ignore=None, archive_dead=False):
        self.base_url = self._normalize_url(base_url)
        self.domain = urlparse(self.base_url).netloc.lower()
        self.queue = [self.base_url]
        self.visited_keys = set()
        self.ignore_regex = re.compile(ignore) if ignore else None
        self.archive_dead = archive_dead
        self.graph = LinkGraph()
        self.graph.set_root(self.base_url)

    def run(self):
        while self.queue:
            current_url = self.queue.pop(0)
            canon_key = self._unique_key(current_url)
            if canon_key in self.visited_keys:
                continue
            self.visited_keys.add(canon_key)

            Logger.print(2, f"Visiting {current_url}")
            try:
                response = self._fetch(current_url)
                content_type = response.headers.get('Content-Type', '').split(';')[0]
                file_path = urlparse(response.url).path or "/"
                Logger.print(2,f"Downloaded {file_path}!")
                last_modified = response.headers.get('Last-Modified')
                code = response.status_code
                # 400 and higher represent HTTP error status codes.
                is_broken = code >= 400
                node = self.graph.get_or_create_node(
                    current_url,
                    content_type=content_type,
                    response_code=code,
                    last_modified=last_modified,
                    broken=is_broken,
                    external=False,
                    file_path=file_path
                )
                print(node.to_dict())

                # if it's an html document, pick it apart for links we can poach
                if 'text/html' in content_type:
                    node.title, links = self._parse_html(response.text, current_url)
                elif 'text/css' in content_type:
                    links = self._parse_css(response.text, current_url)
                else:
                    links = set()

            except requests.exceptions.RequestException as e:
                Logger.print(1, f"Request failed for {current_url}: {e}")
                node = self.graph.get_or_create_node(
                    current_url,
                    response_code=-1,
                    broken=True,
                    external=False
                )
                links = set()

            for link in links:
                self._handle_link(node, link)

        return self.graph

    def _fetch(self, url):
        return requests.get(url, timeout=10, headers={'User-Agent': 'creepy-crawler'})

    def _normalize_url(self, url):
        base, _ = urldefrag(url)  # remove #fragment
        return base.rstrip('/')  # remove trailing slash

    def _unique_key(self, url):
        # used only for deduplication: ignore difference between https and http; also ignore #fragment
        base, _ = urldefrag(url)
        parsed = urlparse(base)
        return f"{parsed.netloc.lower()}{parsed.path.rstrip('/') or '/'}"

    def _parse_html(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else ''
        links = set()
        for tag, attr in [('a', 'href'), ('link', 'href'), ('script', 'src'),
                          ('img', 'src'), ('iframe', 'src'), ('source', 'src')]:
            for el in soup.find_all(tag):
                raw = el.get(attr)
                if raw:
                    link = urljoin(base_url, raw)
                    links.add(self._normalize_url(link))
        return title, links

    def _parse_css(self, css_text, base_url):
        pattern = re.compile(r'url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)', re.IGNORECASE)
        return {self._normalize_url(urljoin(base_url, match)) for match in pattern.findall(css_text)}

    def _handle_link(self, source_node, target_url):
        # this is the regex that allows you to avoid a lot of pain.
        if self.ignore_regex and self.ignore_regex.search(target_url):
            Logger.print(2, f"Ignored (regex): {target_url}")
            return

        canon_key = self._unique_key(target_url)
        parsed = urlparse(target_url)

        # if it's an externallink, put it on the chart but we can't do anything
        if parsed.netloc and parsed.netloc.lower() != self.domain:
            node = self.graph.get_or_create_node(target_url, external=True)
            source_node.add_target(node)
            return

        # internal and not yet visited
        if canon_key not in self.visited_keys and all(
            self._unique_key(u) != canon_key for u in self.queue
        ):
            self.queue.append(target_url)

        node = self.graph.get_or_create_node(target_url)
        source_node.add_target(node)