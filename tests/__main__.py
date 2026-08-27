"""Run every check: `python3 -m tests`."""

from __future__ import annotations

import importlib
import traceback

MODULES = ["tests.test_geometry", "tests.test_model", "tests.test_gclc",
           "tests.test_viewer", "tests.test_ui"]


def main() -> int:
    passed, failed = 0, []
    for name in MODULES:
        module = importlib.import_module(name)
        tests = [v for k, v in sorted(vars(module).items()) if k.startswith("test_")]
        print(f"\n{name}  ({len(tests)} checks)")
        for test in tests:
            try:
                test()
            except Exception:
                failed.append(f"{name}.{test.__name__}")
                print(f"FAIL  {test.__name__}")
                traceback.print_exc()
            else:
                passed += 1
                print(f"ok    {test.__name__}")

    print(f"\n{passed} passed, {len(failed)} failed")
    for name in failed:
        print(f"  failed: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
