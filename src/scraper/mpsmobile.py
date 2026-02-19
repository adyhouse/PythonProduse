"""
Scraper MPS Mobile (mpsmobile.de). B2B, prețuri cu login.
SKU/EAN din tabele (Art-Nr., GTIN). Preț 0 dacă nu e vizibil.
"""
import re
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper


class MpsmobileScraper(BaseScraper):
    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.config.get("headers", {}).get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self.config.get("headers", {}).get(
                "Accept-Language", "de-DE,de;q=0.9"
            ),
            "Referer": self.config.get("base_url", "https://mpsmobile.de") + "/",
        }

    def _find_product_url(self, sku_or_query: str) -> Optional[str]:
        base_url = self.config.get("base_url", "https://mpsmobile.de").rstrip("/")
        lang = self.config.get("default_language", "de")
        search_url = f"{base_url}/{lang}/all-categories-c-0/search/{requests.utils.quote(sku_or_query)}"
        self.log(f"   🔍 Căutare: {search_url}", "INFO")
        try:
            r = requests.get(search_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            for a in soup.select('a[href*="-p-"]'):
                href = (a.get("href") or "").strip()
                if href and "-p-" in href:
                    if not href.startswith("http"):
                        href = base_url + href if href.startswith("/") else base_url + "/" + href
                    self.log(f"   ✓ Produs găsit: {href[:80]}...", "INFO")
                    return href
        except Exception as e:
            self.log(f"   ✗ Căutare eșuată: {e}", "ERROR")
        return None

    def scrape_product(self, sku_or_url: str) -> Optional[Dict]:
        if not sku_or_url or not sku_or_url.strip():
            return None
        sku_or_url = sku_or_url.strip()
        base_url = self.config.get("base_url", "https://mpsmobile.de").rstrip("/")

        if sku_or_url.startswith("http://") or sku_or_url.startswith("https://"):
            product_url = sku_or_url
            self.log("   ✓ Link direct detectat", "INFO")
        else:
            product_url = self._find_product_url(sku_or_url)
            if not product_url:
                self.log("   ✗ Nu s-a găsit niciun produs.", "ERROR")
                return None

        try:
            r = requests.get(product_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            page_text = soup.get_text(separator="\n")
        except Exception as e:
            self.log(f"   ✗ Eroare descărcare: {e}", "ERROR")
            return None

        selectors = self.config.get("selectors", {})

        name = ""
        for sel in selectors.get("name", ["h1", ".product-title", ".product-name"]):
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                name = el.get_text(strip=True)
                break
        if not name:
            name = "Produs MPS Mobile"

        price = 0.0
        for sel in selectors.get("price", [".price", ".product-price", "td"]):
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(strip=True)
                if "preis anzeigen" in txt.lower() or "acceso" in txt.lower():
                    continue
                m = re.search(r"[\d.,]+", txt.replace(",", "."))
                if m:
                    try:
                        price = float(m.group(0).replace(",", "."))
                    except ValueError:
                        pass
                    if price > 0:
                        break

        description = ""
        for sel in selectors.get("description", [".product-description", "#description", ".tab-content"]):
            el = soup.select_one(sel)
            if el:
                description = el.get_text(separator="\n", strip=True)[:3000]
                if len(description) > 30:
                    break
        if not description:
            description = name

        sku_furnizor = self._table_value_by_header(soup, selectors.get("sku_table_header", "Art-Nr."))
        if not sku_furnizor:
            sku_furnizor = self._table_value_by_header(soup, "Artículo Nro.")
        ean_real = self._table_value_by_header(soup, selectors.get("ean_table_header", "GTIN"))
        if not ean_real:
            ean_real = self._table_value_by_header(soup, "GTIN:")
        if not sku_furnizor:
            m = re.search(r"-p-([A-Za-z0-9]+)", product_url)
            if m:
                sku_furnizor = m.group(1)
        if not sku_furnizor:
            sku_furnizor = re.sub(r"[^a-zA-Z0-9]", "", product_url[-40:]) or "MPS-unknown"

        img_urls = []
        if not self.skip_images:
            img_selectors = selectors.get("images", [
                ".product-image img", ".product-gallery img", "img.product-image",
                ".product-main-image", ".gallery img", "[class*='product'] img",
                "[class*='gallery'] img", "[class*='image'] img", ".main img", "img[src]"
            ]) or ["img"]
            if isinstance(img_selectors, str):
                img_selectors = [img_selectors]
            def _normalize(u):
                if not u or not u.strip():
                    return None
                u = u.strip().split()[0]  # srcset: "url 1x, url2 2x" -> take first
                if not u.startswith("http"):
                    u = base_url + u if u.startswith("/") else base_url + "/" + u
                return u

            seen = set()
            for sel in img_selectors:
                for img in soup.select(sel):
                    for attr in ("src", "data-src", "data-lazy-src", "data-original"):
                        src = img.get(attr)
                        if src:
                            src = _normalize(src)
                            if src and src not in seen:
                                src_lower = src.lower()
                                if any(x in src_lower for x in ["logo", "icon", "pixel", "tracking", "avatar", "banner", "sprite"]):
                                    continue
                                if "mpsmobile" in src or "/media/" in src or "/images/" in src or "/img/" in src or any(ext in src_lower for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                                    seen.add(src)
                                    img_urls.append(src)
                                    break
                    srcset = img.get("data-srcset") or img.get("srcset")
                    if srcset:
                        for part in srcset.split(","):
                            u = _normalize(part)
                            if u and u not in seen and ("mpsmobile" in u or "/media/" in u or ".jpg" in u or ".png" in u or ".webp" in u):
                                seen.add(u)
                                img_urls.append(u)
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
