import paramiko
from pathlib import Path

class FileTree:
   # here i essentially cheat, and use the output of the `find` command.
   # I will then compare each line by line to see what is in the hashmap of visited pages.
   #  if the webroot is on a remote server, log in via ssh and then run the command over tere instead

    def __init__(self, webroot, ignore=None):
        self._webroot = webroot
        self.ignore = ignore
        self.tree = {}
