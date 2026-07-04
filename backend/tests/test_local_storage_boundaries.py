import shutil
from pathlib import Path

import pytest

from app.services.storage_local import LocalStorageAdapter


def test_local_storage_rejects_path_traversal():
    root = Path(__file__).resolve().parents[1] / ".test-local-storage-boundaries"
    shutil.rmtree(root, ignore_errors=True)
    adapter = LocalStorageAdapter(root)

    try:
        with pytest.raises(ValueError):
            adapter.exists(object_key="../secret.txt")

        with pytest.raises(ValueError):
            adapter.open_stream(object_key="../secret.txt")
    finally:
        shutil.rmtree(root, ignore_errors=True)
