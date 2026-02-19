"""
Scraper MobileSentrix.eu – deleghează la logica din import_gui (scrape_product).
Respectă skip_images din config (watermark).
"""
from typing import Dict, Optional

from .base import BaseScraper


class MobileSentrixScraper(BaseScraper):
    """Wrapper peste app.scrape_product() cu config și skip_images."""

    def scrape_product(self, sku_or_url: str) -> Optional[Dict]:
        skip = self.config.get("skip_images", False)
        if skip:
            self.log("   ⚠️ Imagini oprite pentru acest furnizor (skip_images / watermark)", "INFO")
        return self.app.scrape_product(
            sku_or_url,
            skip_images=skip,
            supplier_name=self.name,
        )
