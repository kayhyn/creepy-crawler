#!/usr/bin/env python3
"""creepy-crawler

Usage:
  PROGRAM [-v | --verbose] [-q | --quiet] WEBSITE [DIRECTORY] [--map-ext FROM TO] [--ignore REGEX] [-r | --report-types REPORTS] [-s | --serial-format FORMAT]
  PROGRAM [-v | --verbose] [-c | --context-graph FILENAME] DIRECTORY [--map-ext FROM TO] [--ignore REGEX] [-r | --report-types REPORTS]
  PROGRAM [-h | --help]
  PROGRAM --version

Notes:
  The DIRECTORY to compare can be on a remote server using scp syntax ([user@]server:path/). An SSH connection will be established.
  
Options:
  -c --context-graph FILENAME       Load an existing context graph to generate reports from
  --ignore REGEX                    Provide regex for files to ignore in directory listing
  -r --report-types REPORTS         Comma-separated list of desired report types. Options are deadlinks, overXdays, stale. Append filename of each report with : eg deadlinks:d.txt
  -s --serial-format FORMAT         Format to output graph in. Options are JSON and XML.
  -m --map-ext FROM TO              Map FROM real life extensions e.g. php, TO de-facto file extensions e.g. html. This example is default behaviour.
  -v --verbose                      Display vebrose output.
  -q --quiet                        Will not output context graph.
  -h --help                         Show this screen.
  --version                         Show version.

"""
from docopt import docopt
import sys

if __name__ == '__main__':
    # parse command line arguments, and replace placeholder in help text with program name
    arguments = docopt(__doc__.replace("PROGRAM", sys.argv[0]), version='0.1')
    print(arguments);