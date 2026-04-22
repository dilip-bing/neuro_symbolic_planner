"""
key_manager.py
Gemini API key rotation manager.

Loads keys from api_keys.txt (one per line, # = comment).
On quota exhaustion (429 daily limit), automatically rotates to the next key.
All callers use KeyManager.get_current_key() and call .mark_exhausted() on failure.
"""

import os
import pathlib
import logging

logger = logging.getLogger(__name__)

_KEYS_FILE = pathlib.Path(__file__).parent.parent / "api_keys.txt"


def _load_keys() -> list:
    keys = []
    # First: keys from file
    if _KEYS_FILE.exists():
        for line in _KEYS_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                keys.append(line)
    # Fallback: key from environment (always available as last resort)
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key and env_key not in keys:
        keys.append(env_key)
    return keys


class KeyManager:
    """
    Singleton-style key rotation manager.

    Usage:
        km = KeyManager()
        key = km.current_key
        if key_failed_with_quota_error:
            km.mark_exhausted(key)
            key = km.current_key  # automatically next key
    """

    def __init__(self):
        self._keys = _load_keys()
        self._exhausted = set()

        if not self._keys:
            raise RuntimeError(
                "No Gemini API keys found.\n"
                "Add keys to api_keys.txt or set GEMINI_API_KEY in .env"
            )

    @property
    def current_key(self) -> str:
        available = [k for k in self._keys if k not in self._exhausted]
        if not available:
            raise RuntimeError(
                f"All {len(self._keys)} API key(s) exhausted.\n"
                "Add more keys to api_keys.txt and re-run."
            )
        return available[0]

    def mark_exhausted(self, key: str):
        self._exhausted.add(key)
        remaining = len(self._keys) - len(self._exhausted)
        logger.warning(f"Key ending ...{key[-6:]} exhausted. {remaining} key(s) remaining.")

    @property
    def has_keys(self) -> bool:
        return len(self._keys) - len(self._exhausted) > 0

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    @property
    def remaining_keys(self) -> int:
        return len(self._keys) - len(self._exhausted)

    def status(self) -> str:
        return f"{self.remaining_keys}/{self.total_keys} keys available"
