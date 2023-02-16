from . import class_programcontainer
import itertools as it
import os.path
import subprocess
from .exceptions import ProgramFailed

class python_program_container(class_programcontainer._program):
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
            #print(f"failed to execute {self.filepath}", file=sys.stderr)
            #print(q.stderr.decode(), file=sys.stderr)
            raise ProgramFailed(q.stdout.decode(), q.stderr.decode()) from err
        return program_return_str

