from __future__ import annotations

import importlib
import inspect
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
TESTS = ROOT / 'tests'

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class MonkeyPatch:
    def __init__(self):
        self._ops = []

    def setattr(self, obj, name=None, value=None):
        if isinstance(obj, str):
            if name is None:
                raise TypeError('string-target setattr requires a value')
            parts = obj.split('.')
            module = None
            attr_parts = []
            for idx in range(len(parts) - 1, 0, -1):
                module_name = '.'.join(parts[:idx])
                try:
                    module = importlib.import_module(module_name)
                except ModuleNotFoundError:
                    continue
                attr_parts = parts[idx:]
                break
            if module is None or not attr_parts:
                raise ModuleNotFoundError(obj)

            target = module
            for attr_name in attr_parts[:-1]:
                target = getattr(target, attr_name)
            return self.setattr(target, attr_parts[-1], name)
        if name is None:
            raise TypeError('setattr requires attribute name')
        original = getattr(obj, name)
        self._ops.append((obj, name, original))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, original in reversed(self._ops):
            setattr(obj, name, original)
        self._ops.clear()


def main() -> int:
    test_modules = sorted(path.stem for path in TESTS.glob('test_*.py'))
    passed = 0
    failed = []

    for mod_name in test_modules:
        mod = importlib.import_module(f'tests.{mod_name}')
        for name, fn in sorted(inspect.getmembers(mod, inspect.isfunction)):
            if not name.startswith('test_'):
                continue
            try:
                mp = MonkeyPatch()
                with ExitStack() as stack:
                    args = []
                    for param in inspect.signature(fn).parameters.values():
                        if param.name == 'monkeypatch':
                            args.append(mp)
                        elif param.name == 'tmp_path':
                            d = stack.enter_context(tempfile.TemporaryDirectory())
                            args.append(Path(d))
                        else:
                            raise RuntimeError(f'unsupported fixture parameter: {param.name}')
                    fn(*args)
                mp.undo()
                print('ok', mod_name, name)
                passed += 1
            except Exception as exc:
                failed.append((mod_name, name, exc))
                print('FAIL', mod_name, name, exc)

    print(f'passed={passed} failed={len(failed)}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
