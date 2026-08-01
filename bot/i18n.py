import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_locale_dir = Path(__file__).resolve().parent.parent / "locales"
_locales: dict[str, dict[str, str]] = {}
_active_locale: str = "vi"


def load_locales() -> None:
    global _locales
    _locales = {}
    for path in _locale_dir.glob("*.json"):
        lang = path.stem
        try:
            with open(path, encoding="utf-8") as f:
                _locales[lang] = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load locale %s: %s", path, e)
    if "vi" not in _locales:
        logger.warning("Locale 'vi' not found, using empty fallback")
        _locales.setdefault("vi", {})
    _locales.setdefault("en", {})


def set_locale(lang: str) -> bool:
    global _active_locale
    if lang in _locales:
        _active_locale = lang
        return True
    return False


def get_locale() -> str:
    return _active_locale


def get_available_locales() -> list[str]:
    return list(_locales.keys())


def localized_name(name: str, name_vi: str | None = None) -> str:
    if _active_locale == "vi":
        return name_vi or name
    return name


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _(key: str, **kwargs) -> str:
    val = _locales.get(_active_locale, {}).get(key)
    if val is None:
        val = _locales.get("en", {}).get(key)
    if val is None:
        val = key
    if kwargs:
        val = val.format_map(_SafeDict(kwargs))
    return val
