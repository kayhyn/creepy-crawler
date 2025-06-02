import subprocess
import os
from pathlib import Path
import re
from .helpers import Logger
import creepycrawler
import sys

class FileTree:
   # this is essentially a cheat -  instead of walking the file tree myself, I use the posix find command
   # we'll then compare each line by line to see what is in the hashmap of visited pages and what's missing.
   #  if the webroot is on a remote server, we'll log in via ssh and then run the command over tere instead

    def __init__(self, webroot, ignore=None):
        self.user, self.host, path = self._parse_path(webroot)
        self._root = path
        self._ignore = ignore
        self.files = {}
    
    def generate(self):
        Logger.print(1,f"Taking inventory of {self._root}")
        local_cmd = f"cd {self._root} && find . -type f -name '*.*'"

        # if the webroot is on a remote system use ssh to run the command, otherwise use bash
        if self.host:
            cmd = ["ssh", f"{self.user}@{self.host}" if self.user else self.host, local_cmd]
        else:
            cmd = ["bash", "-c", local_cmd]

        result = subprocess.run(cmd, capture_output=True, text=True)

        lines = result.stdout.strip().splitlines()

        # die if we got an error
        if result.returncode != 0:
            Logger.eprint(f"Error: {result.stderr.strip()}")
            exit(1)

        self.files = {"/" + line[2:] if line.startswith("./") else "/" + line for line in lines}

    def _parse_path(self,input_str):
        # parses a path of the form ([user@]host:)path/
        # returns a tuple: (user, host, path)
        # yes, I found this regex online too.
        match = re.match(r'(?:(?P<user>[^@]+)@)?(?P<host>[^:]+):(?P<path>.+)', input_str)
        if match:
            return match.group('user'), match.group('host'), match.group('path')
        else:
            # if it's a local file just return the local portion
            return None, None, input_str

    
    def compare(self, linkgraph):
        lg = linkgraph.view("file_path")
        return [p for p in self.files if p not in lg and "{p}.html" not in lg and "{p}.php" not in lg]
