import urllib
import rdflib
import tempfile
import os
import abc


class resource_link(abc.ABC):
    @abc.abstractmethod
    def update_change(self) -> bool:
        pass


class _iri_repr_class:
    def __repr__( self ):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{self.iri}>"
        #try:
        #except AttributeError as err:
        #   raise Exception(type(self))

class filelink(_iri_repr_class): #also resource_link but that doesnt work
    """This object is an interface for files. So if a program has to work
    on or with a file, this object enables this.

    :TODO: implement plugins for scheme
    :var filepath: (str) filepath
    :var inputstring: asdf
    """
    filepath: str
    inputstring: str
    _exist_last_check: bool
    """Use this if you want open the link as file as open(filepath, mode)"""
    _lastupdated: float
    """Last time, the filelink was updated"""
    def __init__( self, iri ):
        self.iri = iri
        split: urllib.parse.SplitResult = urllib.parse.urlsplit( iri )
        if isinstance( iri, rdflib.BNode ):
            self._tempfile = tempfile.NamedTemporaryFile()
            self.filepath = self._tempfile.name
        elif split.scheme == "file":
            assert not (split.query and split.fragment)
            self.filepath = split.netloc + split.path
        self.update_change()

    def exists(self) -> bool:
        """Checks if file exists"""
        return os.path.exists(self.filepath)

    def update_change(self):
        """Tests if the file was since changed, since the last time this
        was checked.
        """
        try:
            last = self._lastupdated
        except AttributeError:
            last = 0.0
        try:
            self._lastupdated = os.stat( self.filepath ).st_mtime
        except FileNotFoundError:
            self._lastupdated = 0.0
        return self._lastupdated > last

    def as_inputstring( self ):
        """Enables interfacing, with the file, through a filepath.
        The file itself can be written or read through typical fileoperations.
        """
        return self.filepath

    def __del__( self ):
        try:
            self._tempfile.close()
        except AttributeError:
            pass

