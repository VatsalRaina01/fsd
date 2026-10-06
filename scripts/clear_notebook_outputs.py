"""Clear every code cell's outputs AND execution_count, so a notebook passes the
"committed with outputs cleared" guard in tests/test_notebooks.py.

VS Code's "Clear All Outputs" empties `outputs` but keeps each cell's `execution_count`, which the
guard also rejects. Close the notebook in VS Code first, or its next save writes the counts back.
Keeps key order and the 1-space indent Jupyter and VS Code write, so the diff touches only those
fields. Stdlib only.

Usage: .venv/bin/python scripts/clear_notebook_outputs.py <notebook.ipynb> [...]
"""
import json
import sys


def clear(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        clear(p)
