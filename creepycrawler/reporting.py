import json
from .helpers import Logger
class Reporting:
    def generate(link_graph, file_tree=None, frtype=None, fmt="json"):
        print("files in webroot that were not found in live crawl:")
        diff=file_tree.compare(link_graph)
        Logger.print(2, diff)
        return json.dumps(diff);
