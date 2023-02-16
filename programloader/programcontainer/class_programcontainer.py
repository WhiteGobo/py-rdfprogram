import urllib
import abc
import os.path
import mimetypes


class _program(abc.ABC):
    """programcontainer so that you can implement a simple callable with
    args and kwargs
    """
    @abc.abstractmethod
    def __call__(self, *args, **kwargs) -> str:
        """Executes the program with given positional arguments args
        and keyword argument kwargs

        :raises ProgramFailed: if program breaks with error
        :returns: stdout of program execution will be forwarded
        """
        pass

from . import python_container

def iri_to_programcontainer(iri) -> _program:
    split: urllib.parse.SplitResult = urllib.parse.urlsplit( iri )
    if split.scheme == "file":
        filepath = os.path.abspath( split.netloc + split.path )
        if not os.path.exists( filepath ):
            raise TypeError( filepath, "File must exist" )
        mtype, encoding = mimetypes.guess_type(filepath)
        if mtype=="text/x-python":
            return python_container.python_program_container(filepath)
    else:
        raise NotImplementedError("only scheme file is implemented")
