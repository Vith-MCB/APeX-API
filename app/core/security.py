"""Hash de arquivos recebidos, sem aceitar caminho do cliente."""

from hashlib import sha256
from pathlib import Path


def hash_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
