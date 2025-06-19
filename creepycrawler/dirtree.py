import subprocess
import os
from pathlib import Path
import re
from .helpers import Logger
import creepycrawler
import sys
import threading
import re

class FileTree:
   # this is essentially a cheat -  instead of walking the file tree myself, I use the posix find command
   # we'll then compare each line by line to see what is in the hashmap of visited pages and what's missing.
   #  if the webroot is on a remote server, we'll log in via ssh and then run the command over tere instead

    def __init__(self, webroot, ignore=None):
        self.user, self.host, path = self._parse_path(webroot)
        self._root = path
        self._ignore = ignore
        self.files = {}
    
    def generate(self, interactive=true):
        Logger.print(1,f"Taking inventory of {self._root}")

        # if the webroot is on a remote system use ssh to run the command, otherwise use bash
        def run_cmd(sudo=False):
            cmd = f"cd {self._root} && find . -type f -name '*.*'"
            if self.host:
                return ["ssh", f"{self.user}@{self.host}" if self.user else self.host, cmd]
            else:
                return ["bash", "-c", cmd]

            # non-sudo case: just run the command and return the result  
            if not sudo return subprocess.run(cmd, capture_output=True, text=True)

            # sudo case
            cmd = f"sudo -S {cmd}"
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.cwPIPE, stderr=subprocess.PIPE, text=True)

    
        # try running the command. if it works, great!
        result = run_cmd()
        # Otherwise...
        if(result.returncode != 0):
            # try to handle permission error by running with sudo
            if "Permission denied" in result.stderr and interactive:
                logger.print(0,"Permission denied when trying to read {self.__root}. Trying with sudo.")
                result = run_cmd(sudo=True)
                if result.returncode != 0
                    Logger.eprint("Error: command failed even with sudo.")
                    exit(1)
            # die if we got a different error or can't prompt interactively
            else:
                Logger.eprint(f"Error: {result.stderr.strip()}")
                exit(1)

        lines = result.stdout.strip().splitlines()
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
