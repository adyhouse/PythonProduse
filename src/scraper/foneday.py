"""
Scraper Foneday.shop. Site SPA/API – încercare scraping pagină produs (link direct sau căutare).
Dacă conținutul e doar JS, returnează None.
"""
import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper


class FonedayScraper(BaseScraper):
    def _headers(self) -> Dict[str, str]:
        base = self.config.get("base_url", "https://foneday.shop").rstrip("/")
        return {
            "User-Agent": self.config.get("headers", {}).get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": base + "/",
        }

    def _find_product_url(self, sku_or_query: str) -> Optional[str]:
        base_url = self.config.get("base_url", "https://foneday.shop").rstrip("/")
        search_url = f"{base_url}/catalog"
        self.log(f"   🔍 Catalog: {search_url}", "INFO")
        try:
            r = requests.get(search_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            for a in soup.select('a[href*="/article/"], a[href*="/product/"], a[href*="/shop/"]'):
                href = (a.get("href") or "").strip()
                if href and sku_or_query.lower() in href.lower():
                    if not href.startswith("http"):
                        href = base_url + href if href.startswith("/") else base_url + "/" + href
                    self.log(f"   ✓ Produs găsit: {href[:80]}...", "INFO")
                    return href
            for a in soup.select("a[href]"):
                href = (a.get("href") or "").strip()
                if href and ("article" in href or "product" in href) and not href.startswith("#"):
                    if not href.startswith("http"):
                        href = base_url + href if href.startswith("/") else base_url + "/" + href
                    return href
        except Exception as e:
            self.log(f"   ✗ Căutare eșuată: {e}", "ERROR")
        return None

    def scrape_product(self, sku_or_url: str) -> Optional[Dict]:
        if not sku_or_url or not sku_or_url.strip():
            return None
        sku_or_url = sku_or_url.strip()
        base_url = self.config.get("base_url", "https://foneday.shop").rstrip("/")

        if sku_or_url.startswith("http://") or sku_or_url.startswith("https://"):
            product_url = sku_or_url
            self.log("   ✓ Link direct detectat", "INFO")
        else:
            product_url = self._find_product_url(sku_or_url)
            if not product_url:
                self.log("   ✗ Nu s-a găsit niciun produs (Foneday: încercați link direct).", "ERROR")
                return None

        try:
            r = requests.get(product_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            page_text = soup.get_text(separator="\n")
        except Exception as e:
            self.log(f"   ✗ Eroare descărcare: {e}", "ERROR")
            return None

        if len(page_text.strip()) < 200 and "article" not in page_text.lower():
            self.log("   ⚠️ Pagina pare SPA (conținut JS) – Foneday poate necesita link direct.", "WARNING")

        selectors = self.config.get("selectors", {})

        name = ""
        for sel in selectors.get("name", ["h1", "h2", ".product-title", ".article-title", "[data-product-name]"]):
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                name = el.get_text(strip=True)
                break
        if not name:
            name = "Produs Foneday"

        price = 0.0
        for sel in selectors.get("price", [".price", ".product-price", "[data-price]", "[class*='price']"]):
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(strip=True)
                m = re.search(r"[\d.,]+", txt.replace(",", "."))
                if m:
                    try:
                        price = float(m.group(0).replace(",", "."))
                    except ValueError:
                        pass
                    if price > 0:
                        break
        if price == 0.0:
            m = re.search(r"[\d.,]+\s*€|€\s*([\d.,]+)", page_text)
            if m:
                g = m.group(1) or m.group(0).replace("€", "").strip()
                try:
                    price = float(g.replace(",", "."))
                except ValueError:
                    pass

        description = ""
        for sel in selectors.get("description", [".description", ".product-description", "[itemprop=description]"]):
            el = soup.select_one(sel)
            if el:
                description = el.get_text(separator="\n", strip=True)[:3000]
                if len(description) > 30:
                    break
        if not description:
            description = name

        sku_furnizor = re.sub(r"[^a-zA-Z0-9]", "", (sku_or_url if not sku_or_url.startswith("http") else product_url)[:50]) or "FD-unknown"
        ean_real = sku_furnizor if sku_or_url.isdigit() or (sku_or_url.replace("-", "").isalnum() and len(sku_or_url) >= 6) else ""

        img_urls = []
        if not self.skip_images:
            for img in soup.select("img[src]"):
                src = img.get("src") or img.get("data-src")
                if src and ("product" in src.lower() or "image" in src.lower() or "article" in src.lower() or "cdn" in src.lower()):
                    if not src.startswith("http"):
                        src = base_url + src if src.startswith("/") else base_url + "/" + src
                    img_urls.append(src)
            img_urls = list(dict.fromkeys(img_urls))[:10]

        product_id = re.sub(r"[^a-zA-Z0-9_-]", "_", (sku_furnizor or product_url)[:50])
        images_data = self._download_images(img_urls, product_id, self._headers()) if img_urls else []

        tags = []
        return self._build_product_data(
            name=name,
            price=price,
            description=description,
            images=images_data,
            sku_furnizor=sku_furnizor,
            ean_real=ean_real or sku_furnizor,
            source_url=product_url,
            tags=tags,
            soup=soup,
            page_text=page_text,
        )
