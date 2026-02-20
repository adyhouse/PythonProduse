"""
Scraper MobileParts.shop.
Selectori din config. Căutare / link direct.
"""
import re
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper


class MobilepartsScraper(BaseScraper):
    def _headers(self, referer: Optional[str] = None, minimal: bool = False) -> Dict[str, str]:
        base = self.config.get("base_url", "https://mobileparts.shop").rstrip("/")
        if not base.startswith("http"):
            base = "https://" + base.replace("https://", "").replace("http://", "")
        ua = self.config.get("headers", {}).get(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        ref = referer or (base + "/")
        if minimal:
            return {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": ref,
            }
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Referer": ref,
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _find_product_url(self, sku_or_query: str) -> Optional[str]:
        base_url = self.config.get("base_url", "https://mobileparts.shop").rstrip("/")
        search_url = self.config.get("search_url_template", "{base_url}/search?q={sku}").format(
            base_url=base_url, sku=requests.utils.quote(sku_or_query)
        )
        self.log(f"   🔍 Căutare: {search_url}", "INFO")
        try:
            r = requests.get(search_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            for a in soup.select('a[href*="/product/"], a[href*="/p/"], a.product-link, .product-item-link'):
                href = (a.get("href") or "").strip()
                if href and ("product" in href or "/p/" in href):
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
        base_url = self.config.get("base_url", "https://mobileparts.shop").rstrip("/")

        if sku_or_url.startswith("http://") or sku_or_url.startswith("https://"):
            product_url = sku_or_url
            self.log("   ✓ Link direct detectat", "INFO")
        else:
            product_url = self._find_product_url(sku_or_url)
            if not product_url:
                self.log("   ✗ Nu s-a găsit niciun produs.", "ERROR")
                return None

        # Session + homepage apoi produs; la 403 încercăm header-e minime
        parsed = urlparse(product_url)
        site_root = f"{parsed.scheme}://{parsed.netloc}"
        session = requests.Session()
        session.headers.update(self._headers(referer=site_root + "/"))
        try:
            session.get(site_root + "/", timeout=15)
            time.sleep(1)
        except Exception:
            pass
        last_error = None
        for use_minimal in (False, True):
            try:
                h = self._headers(referer=site_root + "/", minimal=use_minimal)
                r = session.get(product_url, headers=h, timeout=30, allow_redirects=True)
                if r.status_code == 403 and not use_minimal:
                    self.log("   ⚠️ 403 – reîncerc cu header-e minime...", "INFO")
                    continue
                r.raise_for_status()
                soup = BeautifulSoup(r.content, "html.parser")
                page_text = soup.get_text(separator="\n")
                self._save_debug_html(soup, product_url)
                last_error = None
                break
            except requests.HTTPError as e:
                last_error = e
                if e.response.status_code == 403:
                    if not use_minimal:
                        continue
                else:
                    raise
            except Exception as e:
                last_error = e
                if not use_minimal:
                    continue
                raise
        if last_error is not None:
            self.log(f"   ✗ Eroare descărcare: {last_error}", "ERROR")
            return None

        selectors = self.config.get("selectors", {})

        name = ""
        for sel in selectors.get("name", ["h1", ".product-title", ".product-name", "[itemprop=name]"]):
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                name = el.get_text(strip=True)
                break
        if not name:
            name = "Produs MobileParts"

        price = 0.0
        for sel in selectors.get("price", [".price", ".product-price", "span.price", "[data-price]"]):
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

        description = ""
        for sel in selectors.get("description", [".product-description", ".description", "[itemprop=description]"]):
            el = soup.select_one(sel)
            if el:
                description = el.get_text(separator="\n", strip=True)[:3000]
                if len(description) > 30:
                    break
        if not description:
            description = name

        sku_furnizor = ""
        ean_real = ""
        for sel in selectors.get("sku", [".sku", ".product-sku", "[itemprop=sku]"]):
            el = soup.select_one(sel)
            if el:
                sku_furnizor = el.get_text(strip=True) or el.get("content") or ""
                if sku_furnizor and re.match(r"^[\dA-Za-z-]+$", sku_furnizor):
                    ean_real = sku_furnizor
                    break
        if not sku_furnizor:
            sku_furnizor = re.sub(r"[^a-zA-Z0-9]", "", product_url[-40:]) or "MP-unknown"

        img_urls = []
        if not self.skip_images:
            for sel in selectors.get("images", [".product-images img", ".product-gallery img", ".product-image img", "img[alt*='product']"]):
                for img in soup.select(sel):
                    src = img.get("src") or img.get("data-src")
                    if src:
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
