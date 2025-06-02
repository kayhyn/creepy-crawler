from .helpers import Logger 
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom
import datetime

import json
class Node:
    def __init__(self, url, content_type=None, response_code=None, last_modified=None, title=None, broken=False, external=False, file_path=None):
        self.url = url
        self.content_type = content_type
        self.response_code = response_code
        self.last_modified = last_modified
        self.title = title
        self.broken = broken
        self.external = external
        self.file_path = file_path
        # list of target Node objects (i.e. any resources loaded by the page)
        self.links = []

    def add_target(self, target_node):
        if all(target.url != target_node.url for target in self.links):
            self.links.append(target_node)
    
    def to_dict(self):
        return {
            "url": self.url,
            "content_type": self.content_type,
            "response_code": self.response_code,
            "last_modified": self.last_modified,
            "title": self.title,
            "broken": self.broken,
            "external": self.external,
            "file_path": self.file_path,
            "links": [n.url for n in self.links],  # only store URLs
    }

    @classmethod
    def from_dict(cls, data):
        node = cls(
            url=data["url"],
            content_type=data.get("content_type"),
            response_code=data.get("response_code"),
            last_modified=data.get("last_modified"),
            title=data.get("title"),
            broken=data.get("broken", False),
            external=data.get("external", False),
            file_path=data.get("file_path"),
        )
        # placeholder for links
        node._link_urls = data.get("links", [])
        return node



class LinkGraph:
    def __init__(self):
        # this will be index.html usually
        self.root = None

        # store all nodes in dictionary (hashmap)
        # O1 access :D
        self._crawled = {}
    
    # provide access to data from the nodes - TODO make this more efficient
    def view(self,feature):
        return [ node.to_dict()[feature] for node in self._crawled.values() ]

    # determine if a link has yet been visited 
    def visited(self, url):
        return url in self._crawled

    # create a new node for a new link, otherwise return a reference to the existing node
    def get_or_create_node(self, url, **kwargs):
        if url not in self._crawled:
            self._crawled[url] = Node(url, **kwargs)
        else:
            # crucially, if the node does exist make sure all of its items are updated with new information
            node = self._crawled[url]
            for k, v in kwargs.items():
                setattr(node, k, v)

        return self._crawled[url]

    # when we come across a link, determine how it should be added to the graph
    def add_link(self, source_url, target_url, target_metadata=None):
        # first, look up the source node
        source = self._crawled.get(source_url)
        # then, either find the child already in 
        target = self.get_or_create_node(target_url, **(target_metadata or {}))
        if source:
            source.add_target(target)
        else:
            Logger.eprint(f"link {target} appears to have no source; this shouldn't be possible.")

    # initial operation
    def set_root(self, url, **kwargs):
        self.root = self.get_or_create_node(url, **kwargs)
        return self.root

    # only JSON is currently supported. This just converts the nodes to dictionaries and serialises everything.
    def serialize(self, fmt="json"):
        if fmt == "json":
            data = {
                "root": self.root.url if self.root else None,
                "nodes": {url: node.to_dict() for url, node in self._crawled.items()}
            }
            return json.dumps(data, indent=2)
        raise ValueError(f"Unknown format: {fmt}")

    # function decorators are really great
    @classmethod
    def deserialize(cls, data, fmt="json"):
        if fmt == "json":
            graph_data = json.loads(data)
            graph = cls()
            # First pass: create all nodes
            for url, node_dict in graph_data["nodes"].items():
                graph._crawled[url] = Node.from_dict(node_dict)

            # Second pass: resolve links
            for node in graph._crawled.values():
                node.links = [graph._crawled[target_url] for target_url in getattr(node, "_link_urls", [])]

            # Set root
            root_url = graph_data.get("root")
            if root_url:
                graph.root = graph._crawled.get(root_url)

            return graph
        raise ValueError(f"Unknown format: {fmt}")

    @classmethod
    def load(cls, data):
        return cls.deserialize("".join(data))

    # Turn our site map format into standards compliant XML that you can host!! Coming soon, miracy considerations.
    def generate_sitemap(self):
        urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

        for node in self._crawled.values():
            if node.external or node.broken:
                continue

            url_elem = SubElement(urlset, "url")

            loc = SubElement(url_elem, "loc")
            loc.text = node.url

            if node.last_modified:
                lastmod = SubElement(url_elem, "lastmod")
                try:
                    # Attempt to parse and reformat timestamp if valid
                    dt = datetime.datetime.fromisoformat(node.last_modified)
                    lastmod.text = dt.date().isoformat()
                except Exception:
                    lastmod.text = node.last_modified  # fallback: raw string

        # Prettify
        raw_xml = tostring(urlset, encoding="utf-8")
        dom = xml.dom.minidom.parseString(raw_xml)
        return dom.toprettyxml(indent="  ")



