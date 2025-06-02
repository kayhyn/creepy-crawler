import re
import requests
from bs4 import BeautifulSoup
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
        self.queued_keys = set()


    def run(self):
        while self.queue:
            current_url = self.queue.pop(0)

            canon_key = self._stupid_dedup_key(current_url)
            if canon_key in self.visited_keys:
                continue
            # no longer queued - this babys moving to the visited list
            self.queued_keys.discard(canon_key)
            self.visited_keys.add(canon_key)

            Logger.print(2, f"Visiting {current_url}")
            try:
                response = requests.get(current_url, timeout=10, headers={'User-Agent': 'creepy-crawler'})
                # follow redirects, and store the *correct* URL
                current_url = response.url
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

                # if it's an html document, pick it apart for links we can poach
                if 'text/html' in content_type:
                    node.title, links = self._parse_html(response.text, current_url)
                elif 'text/css' in content_type:
                    links = self._parse_css(response.text, current_url)
                else:
                    links = set()

                Logger.print(2,node.to_dict())
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
                self._cue_up_link(node, link)

        return self.graph

    def _normalize_url(self, url):
        # remove #fragment
        base, _ = urldefrag(url)  
        return base

    def _stupid_dedup_key(self, url):
        base, _ = urldefrag(url)
        parsed = urlparse(base)
        # I had to do this because apparently some sites serve both http and https versions
        return f"{parsed.netloc.lower()}{parsed.path.rstrip('/') or '/'}"

    def _parse_html(self, html, base):
        # what a fun name
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else ''
        links = set()
        # loop through all the tags that have links, and the corresponding attribute that holds the link.
        # grab the links for all those.
        for tag, attr in [('a', 'href'), ('link', 'href'), ('script', 'src'),
                          ('img', 'src'), ('iframe', 'src'), ('source', 'src')]:
            for el in soup.find_all(tag):
                raw = el.get(attr)
                if raw:
                    link = urljoin(base, raw)
                    links.add(self._normalize_url(link))
        return title, links

    def _parse_css(self, css_text, base_url):
        # i'll be honest, I got this from stackoverflow. it's a very impressive regex.
        pattern = re.compile(r'url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)', re.IGNORECASE)
        return {self._normalize_url(urljoin(base_url, match)) for match in pattern.findall(css_text)}

    def _cue_up_link(self, source_node, target_url):
        #  apply regex filter to ignore parts of the site you don't want to index
        #  if the link matches, we can discard it
        if self.ignore_regex and self.ignore_regex.search(target_url):
            Logger.print(2, f"Ignored (regex): {target_url}")
            return

        # ensure every URL has a unique normalised ID, regardless of schema
        canon_key = self._stupid_dedup_key(target_url)
        parsed = urlparse(target_url)

        # external link? onto the graph, but don't follow it or we'll be swallowing the whole internet
        if parsed.netloc and parsed.netloc.lower() != self.domain:
            node = self.graph.get_or_create_node(target_url, external=True)
            source_node.add_target(node)
            return

        # internal and not yet visited
        if canon_key not in self.visited_keys and canon_key not in self.queued_keys:
            self.queue.append(target_url)
            self.queued_keys.add(canon_key)

        node = self.graph.get_or_create_node(target_url)
        source_node.add_target(node)