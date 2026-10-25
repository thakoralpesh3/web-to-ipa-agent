from typing import Dict, Any
from .app_inspector import iOSAppInspector

class URLExtractor:
    """
    URL metadata and logo extraction adapter delegating to iOSAppInspector.
    """
    @classmethod
    def inspect_url(cls, url: str) -> Dict[str, Any]:
        return iOSAppInspector.inspect_url(url)
