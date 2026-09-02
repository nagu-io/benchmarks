#!/usr/bin/env python3
"""Write the tiny dataset's page images.

The three page images are a 1x1 PNG each. They exist so that
`load_dataset(..., require_rendered=True)` finds a file where the manifest says
one is, and nothing in the suite reads a pixel from them. They are generated
here rather than committed because this repository carries no binary files:
every artefact in it is text, or is rebuilt from text by a script like this one.

Run directly, or let `tests/conftest.py` call `ensure_pages()` before the suite.
"""

from __future__ import annotations

import base64
from pathlib import Path

# A 1x1 PNG. Not an image of anything; a placeholder with a valid header.
ONE_BY_ONE_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGN48uIVAAVq"
    "Arelm2FgAAAAAElFTkSuQmCC"
)

DOC_IDS = ("tiny-inv-0001", "tiny-inv-0002", "tiny-kyc-0003")


def ensure_pages(root: Path | None = None) -> list[Path]:
    """Write each missing page image. Returns the paths that exist afterwards."""
    base = Path(root) if root is not None else Path(__file__).parent
    payload = base64.b64decode(ONE_BY_ONE_PNG)
    written = []
    for doc_id in DOC_IDS:
        page = base / "documents" / doc_id / "page-01.png"
        page.parent.mkdir(parents=True, exist_ok=True)
        if not page.exists() or page.read_bytes() != payload:
            page.write_bytes(payload)
        written.append(page)
    return written


if __name__ == "__main__":
    for path in ensure_pages():
        print(path)
