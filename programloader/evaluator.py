"""The evaluator class here introduced, is a pure generator for
axioms. To describe its function very rough, if it succeeds all axioms
defined for a placeholder-resources are also valid for the program input.
"""
import abc
import subprocess
import typing as typ
import urllib
import os
import mimetypes
from . import PROLOA_NS
from rdfloader import extension_classes as extc


class ProgramFailed(Exception):
    pass


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


class _iri_repr_class:
    def __repr__(self):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{str(self.iri)}>"

    def __str__(self):
        name = f"{type(self).__name__}"
        return f"<{name}:{str(self.iri)}>"


class evaluator(_iri_repr_class):
    def __init__(self, iri, app_args, program_container:_program ):
        self.uri = iri
        self.app_args = app_args
        self.program_container = program_container

    @classmethod
    def from_rdf(cls, iri,
                 app_args: extc.info_attr_list(PROLOA_NS.hasArgument),
                 ):
        split: urllib.parse.SplitResult = urllib.parse.urlsplit( iri )
        if split.scheme == "file":
            filepath = os.path.abspath( split.netloc + split.path )
            if not os.path.exists( filepath ):
                raise TypeError( filepath, "File must exist" )
            mtype, encoding = mimetypes.guess_type(filepath)
            if mtype=="text/x-python":
                programcontainer = python_program_container(filepath)
        else:
            raise NotImplementedError("only scheme file is implemented")
        return cls(iri, app_args, programcontainer)

    def __call__(self, input_args: typ.Dict):
        kwargs, args = {},{}
        for arg, val in input_args.items():
            try:
                if isinstance(arg.id, str):
                    kwargs[arg.id] = val
                elif isinstance(arg.id, int):
                    args[arg.id] = val
                else:
                    raise TypeError(arg, arg.id)
            except (AttributeError, TypeError) as err:
                raise TypeError(input_args) from err
        args = [args[x] for x in sorted(args.keys())]
        return self.program_container(*args, **kwargs)


class python_program_container(_program):
    """
    """
    def __init__(self, filepath):
        assert os.path.exists( filepath )
        self.filepath = filepath


    def __call__(self, *args, **kwargs) -> str:
        commandarray = ["python", str(self.filepath)]
        for x in it.chain(args, it.chain.from_iterable(kwargs.items())):
            try:
                commandarray.append(x.as_inputstring())
            except AttributeError:
                commandarray.append(str(x))
        q = subprocess.run(commandarray, capture_output=True)
        try:
            asdf = q.check_returncode()
            program_return_str = q.stdout.decode()
        except subprocess.CalledProcessError as err:
            print(f"failed to execute {self.filepath}", file=sys.stderr)
            print(q.stderr.decode(), file=sys.stderr)
            raise ProgramFailed(self.filepath) from err
        return program_return_str

