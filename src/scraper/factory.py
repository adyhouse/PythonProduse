"""
Factory pentru scraper-uri furnizori.
Încarcă config din suppliers/<name>/config.json și returnează instanța corespunzătoare.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseScraper
from .mobilesentrix import MobileSentrixScraper
from .componentidigitali import ComponentidigitaliScraper
from .mmsmobile import MmsmobileScraper
from .mpsmobile import MpsmobileScraper
from .mobileparts import MobilepartsScraper
from .foneday import FonedayScraper

_SUPPLIERS_DIR = Path(__file__).resolve().parent.parent.parent / "suppliers"
_SCRAPER_CLASSES = {
    "mobilesentrix": MobileSentrixScraper,
    "foneday": FonedayScraper,
    "mobileparts": MobilepartsScraper,
    "mmsmobile": MmsmobileScraper,
    "mpsmobile": MpsmobileScraper,
    "componentidigitali": ComponentidigitaliScraper,
}


def load_supplier_config(supplier_name: str) -> Optional[Dict]:
    """Încarcă config.json pentru un furnizor. Returnează None dacă nu există."""
    path = _SUPPLIERS_DIR / supplier_name / "config.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class ScraperFactory:
    @classmethod
    def load_supplier_config(cls, supplier_name: str) -> Optional[Dict]:
        """Încarcă config.json pentru un furnizor."""
        return load_supplier_config(supplier_name)

    @classmethod
    def get_scraper(cls, supplier_name: str, app: Any) -> Optional[BaseScraper]:
        """
        Creează scraper pentru furnizorul dat.
        supplier_name: nume din folder (mobilesentrix, foneday, etc.)
        app: instanță ImportProduse
        """
        config = load_supplier_config(supplier_name)
        if not config or not config.get("enabled", True):
            return None
        scraper_class = _SCRAPER_CLASSES.get(supplier_name)
        if not scraper_class:
            return None
        return scraper_class(config, app)

    @classmethod
    def list_available_suppliers(cls) -> List[Dict]:
        """Listează furnizorii care au config.json și enabled=true."""
        result = []
        if not _SUPPLIERS_DIR.exists():
            return result
        for path in sorted(_SUPPLIERS_DIR.iterdir()):
            if not path.is_dir():
                continue
            config_path = path / "config.json"
            if not config_path.exists():
                continue
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                continue
            if not config.get("enabled", True):
                continue
            result.append({
                "name": config.get("name", path.name),
                "display_name": config.get("display_name", config.get("name", path.name)),
            })
        return result

    @classmethod
    def get_sku_list_path(cls, supplier_name: str) -> Optional[Path]:
        """Returnează calea către sku_list.txt pentru furnizor (din config sau default)."""
        config = load_supplier_config(supplier_name)
        if not config:
            return None
        rel = config.get("sku_list_file", f"suppliers/{supplier_name}/sku_list.txt")
        # path poate fi relativ la rădăcina proiectului
        root = Path(__file__).resolve().parent.parent.parent
        return root / rel
