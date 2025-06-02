import sys, os
from pathlib import Path
from contextlib import contextmanager


# file rw helper: stores working dir and handles reading and writing
class RWTool:
    __working_dir = ""

    @staticmethod
    def cwd(d):
        RWTool.__working_dir = Path(d)
    
    # this allows easier file reading without worrying about the path, and it's also pretty cool!
    @contextmanager
    @staticmethod
    def open(fname, mode):
        p = Path(fname)
        if not p.is_absolute():
            p = RWTool.__working_dir / p

        # if writing, create parent directory if it doesn't yet exist
        if mode=='w': 
            os.makedirs(p.parent, exist_ok=True)
            Logger.print(2, f"{p.parent} created")

        with open(p, mode) as f:
        # hand file back to caller
            yield f
            if mode=='r':
                Logger.print(2, f"{p} read")
            else:
                Logger.print(1, f"{p} written")

class Logger:
    __verbosity_level = 2

    @staticmethod
    def set(silent, quiet):
        # level 0: silent
        # level 1: important stuff
        # level 2: verbose
        Logger.__verbosity_level = 0 if silent else 1 if quiet else 2

    # print to stderr
    @staticmethod
    def eprint(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

    @staticmethod
    def print(level=2, *args, **kwargs):
        # don't print if below level
        if level < Logger.__verbosity_level: return
        print(*args, **kwargs)
        


    

def valid_path(p_str, dir=True, mode="rw", fatal=False):
    """
    Takes a path string or Path object, checks if it meets requirements, returns it if so or None otherwise. 
    If fatal=true is passed in, then crash upon validation failure.
    If reading is not required, will consider a path valid if it can be created in its parent directory.
    """
    p = Path(p_str)
    require_read = 'r' in mode
    require_write = 'w' in mode
    try:
        # check the path exists, if we need to read from it
        if not p.exists(): 
            assert not require_read ,'does not exist.'
            assert valid_path(p.parent), 'could not be created.'
        # otherwise, check if we can create the path
        else:
            # verbose = fatal because if this fails, the program will terminate, so we want to print the reason it failed.
            # check other requirements
            if dir: assert p.is_dir(), 'is not a directory.'
            assert os.access(p, os.W_OK) or not require_write, 'is not writable!'
            assert os.access(p, os.R_OK) or not require_read, 'is not readable!'
        return p
    except AssertionError as e:
        if fatal: Logger.eprint(f"Error: {p} {e}")
        if not fatal: return None
        sys.exit(1)
