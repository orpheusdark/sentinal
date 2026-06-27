from pathlib import Path
import sys

ROOT_PATH = Path(__file__).resolve().parent.parent
ROOT_STR = str(ROOT_PATH)
TESTS_PATH = Path(__file__).resolve().parent

# Ensure project root is first on sys.path so top-level imports resolve correctly.
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

# Remove any sys.path entries that are inside the tests directory to avoid package shadowing.
def _is_within_tests(path: str) -> bool:
    try:
        resolved = Path(path).resolve()
    except Exception:
        return False
    return resolved == TESTS_PATH or resolved.is_relative_to(TESTS_PATH)

sys.path[:] = [p for p in sys.path if p and not _is_within_tests(p)]
