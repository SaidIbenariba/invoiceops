import zlib

import numpy as np


def fake_encoder(texts: list[str]) -> np.ndarray:
    """Deterministic character-trigram hashing encoder, L2-normalised. No model download."""
    out = np.zeros((len(texts), 64))
    for r, t in enumerate(texts):
        padded = f"  {t} "
        for k in range(len(padded) - 2):
            out[r, zlib.crc32(padded[k : k + 3].encode()) % 64] += 1
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return out / norms
