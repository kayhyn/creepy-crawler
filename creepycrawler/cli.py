"""creepy-crawler - Create sitemaps, bust linkrot, find unlinked files, and more!

Usage:
  PROGRAM crawl [options] <website> [<webroot>] 
    [--working-dir <directory>] 
  PROGRAM report [options] <webroot> --link-graph <file> 
    [--working-dir <directory>]
  PROGRAM (-h | --help)
  PROGRAM (-v | --version)

Commands:
  crawl                         Crawl a live website and generate a link graph.
  report                        Generate reports using a pre-existing link 
                                graph and a local directory.

Arguments:
    <website>                   The URL of the website you are trying to crawl.
    <webroot>                   The path to the folder containing the web files.
                                Supports remote path using scp syntax
                                        [user@]server:path/
                                 An SSH session will be establised.

Options:
  -a --archive-dead-links       If dead links are found, look for the 
                                most recent copy on the Internet Archive.
  -f --format <fmt>             Output format(s) for the report(s) (comma-
                                separated): 
                                    json, xml, md 
                                The default is json.
  -h --help                     Show this help message.
  -i --ignore <regex>           Any files matching the specified regex will be
                                excluded from the local tree. Defaults to 
                                ^\\..* (i.e., any file beginning with a .)
  -l --link-graph <file>        In crawl mode, link graph will be saved to this
                                file. In report mode, graph will be read from 
                                this file. If not specified, will try working
                                directory.
  -w --working-dir <directory>  Set the working directory to read from or output 
                                to. Defaults to ./<website>.
  -q --quiet                    Show only abnormalities, like broken links.
  -r --report-types <types>     Comma-separated: 
                                    deadlinks, unreachable, combined, all
                                Defaults to all in report mode, otherwise none.
  -s --silent                   Don't show any output.
  -v --version                  Show version.
  -x --sitemap-xml              Generate a standards-compliant XML sitemap.

"""
from docopt import docopt
import sys
import signal
import re
import os
from pathlib import Path
from urllib.parse import urlparse
from creepycrawler import Crawler, FileTree, LinkGraph, Reporting
# make helper functions available as needed
from .helpers import *

# ensure the actual executable path is displayed in help message
USAGE = __doc__.replace("PROGRAM", sys.argv[0])

class CLI:
    __valid_formats = {'json','xml', 'md'}
    __valid_report_types = {'deadlinks', 'unreachable', 'combined', 'all'}
    def __init__(self):
        # load config settings from command line arguments, using docopt for initial parsing
        self.args = docopt(USAGE, version='0.1')

        self.crawl_mode = self.args['crawl']
        self.report_mode = self.args['report']
        self.website = self.args['<website>']
        self.domain = urlparse(self.website).netloc
        self.quiet = self.args['--quiet']
        self.silent = self.args['--silent']
        self.archive_dead_links = self.args['--archive-dead-links']
        self.generate_sitemap = self.args['--sitemap-xml']
        self.ignore_regex = self.args['--ignore'] or r'^\..*'
        
        # set up logger for verbosity levels
        Logger.set(silent=self.args['--silent'], quiet=self.args['--quiet'])
        
        # validate formats and report types
        serial_formats = self.args['--format'] or "json"
        self.serial_formats = [sf.strip() for sf in serial_formats.split(',')]
        for fmt in self.serial_formats:
            if fmt not in self.__valid_formats:
                Logger.eprint(f"Error: unknown format {fmt}.")
                sys.exit(1)
        
        # default all in report mode, none in crawl mode
        report_types = self.args['--report-types'] or ("all" if self.report_mode else None)

        # deal with whitespace
        self.report_types = [rt.strip() for rt in report_types.lower().split(',')] if report_types else []

        for rt in self.report_types:
            if rt not in self.__valid_report_types:
                Logger.eprint(f"Error: unknown report type {rt}.")
                sys.exit(1)

        # validate working directory and link graph file path
        wd_rough = (Path(Path.cwd() / self.args['--working-dir']) if self.args["--working-dir"] else Path(Path.cwd() / f"./{self.domain}"))
        self.working_dir = wd_rough
        lg_rough = Path(self.args['--link-graph'] or wd_rough / f"./{self.domain}_graph.xml") 
        # in crawl mode we need to know two things:
        # 1. can we write to the link graph file?
        # 2. if there are reports, can we write to those?
        # TODO: add continue functionality
        if self.crawl_mode:
            # check if we can write to the absolute path of the link graph file. if not, we will need to use the working directory.
            lgf = valid_path(lg_rough, dir=False, mode="r")
            # if we need to use the working directory, check that we can do so (or create it)
            if self.report_types or self.generate_sitemap or not lgf:
                wd = valid_path(wd_rough, dir=True, mode="w", fatal=True)
            # if we didn't find a valid lgf to write to before, try within the wd
            self.link_graph_file = (lgf or valid_path(wd / lg_rough, dir=False, mode="w", fatal=True)).resolve()
        else:
            # in report mode, we need to READ the lgf and write to the working directory
            lgf = valid_path(lg_rough, dir=False, mode="r")
            # if the lgf does not exist, the working directory must be readable to look for it

            wd = valid_path(wd_rough, dir=True, mode=("rw" if lgf else "w"), fatal=True)
            self.working_dir = wd
            # now, ensure we have a valid lgf to read - either from before or inside the wd
            self.link_graph_file = (lgf or valid_path(wd / lg_rough, dir=False, mode="r") or valid_path(wd / f"{self.domain}_graph.md", dir=False, mode="r") or valid_path(wd / f"{self.domain}_graph.json", dir=False, mode="r", fatal=True)).resolve()
        
        Logger.print(2,f"Set working directory to {self.working_dir}")
        # finally, tell the file helper where our WD is
        RWTool.cwd(self.working_dir)

        

    def run(self):
        webroot = self.args['<webroot>']
        if self.args['crawl']:
            Logger.print(1,f"Starting crawl on: {self.website}")
            crawler = Crawler(
                self.website,
                ignore=self.ignore_regex,
                archive_dead=self.archive_dead_links
            )
            # run the crawler and save the resulting graph to a file
            link_graph = crawler.run()

            Logger.print(1, f"Crawl complete! Saving serialized output...")

            # serialize to all requested formats and save
            for fmt in self.serial_formats:
                Logger.print(2,f"Serializing to to {fmt}...")
                serialized = link_graph.serialize(fmt)
                with RWTool.open(self.link_graph_file.with_suffix(f".{fmt}"),'w') as f:
                    f.write(serialized)

            self._process_graph(link_graph, webroot)

        elif self.args['report']:
            webroot = self.args['<webroot>']
            if not self.link_graph_file:
                Logger.eprint("Error: --link-graph is required in report mode.")
                sys.exit(1)

            Logger.print(2,f"Loading link graph from: {self.link_graph_file}")
            with RWTool.open(self.link_graph_file, 'r') as f:
                lg_str = f.readlines()

            link_graph = LinkGraph.load(lg_str)

            # now we've loaded the graph, let's process it
            self._process_graph(link_graph, webroot)

        else:
            Logger.eprint("Invalid command. Use --help to see available options.")
            sys.exit(1)
        
        Logger.print(1, "All done!")


    def _process_graph(self, link_graph, webroot):

        if self.generate_sitemap:
            Logger.print(1,"Generating site map!")
            with RWTool.open("sitemap.xml", "w") as f:
                f.write(link_graph.generate_sitemap())
        
        # store directory tree here to be compared in the report generator
        file_tree = None
        if webroot:
            Logger.print(1,"Beginning index of webroot...")
            # initialize the file tree and build it
            file_tree = FileTree(webroot, ignore=self.ignore_regex)
            file_tree.Build()
            Logger.print(1,"Done!")
                
        for rtype in self.report_types:
            Logger.print(1,f"Generating {rtype} report...")
            for fmt in self.serial_formats:
                r = Reporting.generate(link_graph, file_tree, rtype, fmt)
                with RWTool.open(f"{rtype}.{fmt}", "w") as f:
                    f.write(r)

def signal_handler(sig, frame):
    Logger.eprint("CTRL-C detected; quitting.")
    sys.exit(1);
signal.signal(signal.SIGINT, signal_handler)
