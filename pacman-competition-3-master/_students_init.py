import importlib as __importlib
import os as __os
import os.path as __path
import re as __re


_IMPORT_ERRORS: list[tuple[str, str]] = []

__module_path: str = __path.dirname(__file__)
_pyfiles: list[str] = []

for _filename in __os.listdir(__module_path):
    if _filename.startswith("."):
        continue
    if _filename.startswith("__"):
        continue
    if _filename.endswith(".py"):
        _pyfiles.append(_filename)

_pyfiles.sort()

# Students may upload the same file multiple times.  This will result in files
# such as "AwesomeBot.py" and "AwesomeBot (1).py". We will overwrite
# "AwesomeBot.py" with its highest numbered version.
_agent_files: set[str] = set()
_duplicate_id: dict[str, int] = {}
_ORIGINAL_ID = -1

for _filename in _pyfiles:
    _canonical_name = __re.sub(r" \(\d+\).py$", ".py", _filename)
    _dup_id = _ORIGINAL_ID
    if _filename != _canonical_name:
        _dup_id = int(__re.search(r"(?<= \()\d+(?=\).py)", _filename).group())
    if _dup_id >= _duplicate_id.get(_canonical_name, _ORIGINAL_ID):
        if _dup_id != _ORIGINAL_ID:
            try:
                __os.remove(__path.join(__module_path, _canonical_name))
            except OSError:
                pass
            __os.rename(__path.join(__module_path, _filename),
                    __path.join(__module_path, _canonical_name))
        _duplicate_id[_canonical_name] = _dup_id
        _agent_files.add(_canonical_name)

def _typename(obj):
    return type(obj).__name__

for _filename in _agent_files:
    _modname = _filename[:-len('.py')]
    try:
        __importlib.import_module(__name__ + "." + _modname)
    except SyntaxError as e:
        msg = "{}: {} on line {}, char {}"
        _IMPORT_ERRORS.append((_modname, msg.format(_typename(e), e.msg, e.lineno, e.offset)))
    except Exception as e:
        msg = "{}: {}"
        if not e.args:
            msg = msg.format(_typename(e), "--")
        elif len(e.args) == 1:
            msg = msg.format(_typename(e), e.args[0])
        else:
            msg = msg.format(_typename(e), e.args)
        _IMPORT_ERRORS.append((_modname, msg))

try:
    del _ORIGINAL_ID, _agent_files, _canonical_name, _dup_id, _duplicate_id, \
            _filename, _modname, _pyfiles, _typename
except NameError:
    pass
