"""
Scraper MMS Mobile (mmsmobile.de). Odoo-based.
Prețuri necesită login (exportăm 0 dacă nu sunt vizibile). SKU/EAN din tabele.
"""
import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper


class MmsmobileScraper(BaseScraper):
    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.config.get("headers", {}).get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self.config.get("headers", {}).get(
                "Accept-Language", "en-US,en;q=0.9,de;q=0.8"
            ),
            "Referer": self.config.get("base_url", "https://www.mmsmobile.de") + "/",
        }

    def _find_product_url(self, sku_or_query: str) -> Optional[str]:
        base_url = self.config.get("base_url", "https://www.mmsmobile.de").rstrip("/")
        lang = self.config.get("default_language", "en")
        search_url = f"{base_url}/{lang}/shop?search={requests.utils.quote(sku_or_query)}"
        self.log(f"   🔍 Căutare: {search_url}", "INFO")
        try:
            r = requests.get(search_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            for a in soup.select('a[href*="/shop/"]'):
                href = (a.get("href") or "").strip()
                if href and "/shop/" in href and href.count("-") >= 1:
                    if not href.startswith("http"):
                        href = base_url + href if href.startswith("/") else base_url + "/" + href
                    if "search" not in href:
                        self.log(f"   ✓ Produs găsit: {href[:80]}...", "INFO")
                        return href
        except Exception as e:
            self.log(f"   ✗ Căutare eșuată: {e}", "ERROR")
        return None

    def scrape_product(self, sku_or_url: str) -> Optional[Dict]:
        if not sku_or_url or not sku_or_url.strip():
            return None
        sku_or_url = sku_or_url.strip()
        base_url = self.config.get("base_url", "https://www.mmsmobile.de").rstrip("/")

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
            # Salvează HTML pentru debugging
            self._save_debug_html(soup, product_url)
        except Exception as e:
            self.log(f"   ✗ Eroare descărcare: {e}", "ERROR")
            return None

        selectors = self.config.get("selectors", {})

        name = ""
        for sel in selectors.get("name", ["h1", ".product-title"]):
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                name = el.get_text(strip=True)
                break
        if not name:
            name = "Produs MMS Mobile"

        price = 0.0
        for sel in selectors.get("price", ["h4", ".price", "[class*='price']"]):
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(strip=True)
                if "login" in txt.lower() or "register" in txt.lower():
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
        for sel in selectors.get("description", [
            "section[aria-labelledby*='description']",
            ".tab-content",
            ".product-description",
            "#description",
        ]):
            el = soup.select_one(sel)
            if el:
                description = el.get_text(separator="\n", strip=True)[:3000]
                if len(description) > 30:
                    break
        if not description:
            description = name

        sku_furnizor = self._table_value_by_header(soup, selectors.get("sku_table_header", "SKU"))
        ean_real = self._table_value_by_header(soup, selectors.get("ean_table_header", "EAN"))
        if not sku_furnizor:
            m = re.search(r"[\d]+", product_url.split("-")[-1])
            if m:
                sku_furnizor = m.group(0)
        if not sku_furnizor:
            sku_furnizor = re.sub(r"[^a-zA-Z0-9]", "", product_url[-40:]) or "MMS-unknown"

        img_urls = []
        if not self.skip_images:
            # Găsește blocul produsului care conține SKU-ul pentru a exclude produse similare
            product_block = None
            if sku_furnizor and sku_furnizor != "MMS-unknown":
                for elem in soup.find_all(string=re.compile(re.escape(sku_furnizor), re.I)):
                    parent = elem.find_parent(['main', 'article', 'div', 'section'])
                    if parent:
                        product_block = parent
                        break
            
            if not product_block:
                product_block = (
                    soup.select_one("main") or soup.select_one("[class*='product-detail']")
                    or soup.select_one(".product-detail") or soup.select_one("#product-detail")
                    or soup.select_one("[class*='product-content']") or soup.select_one("article.product")
                    or soup.select_one(".product") or soup.select_one("#product")
                )
            
            # Exclude secțiuni de produse similare
            if product_block:
                for section in product_block.find_all(['section', 'div'], class_=re.compile(r'similar|related|recommend|also|other', re.I)):
                    section.decompose()
                for sidebar in product_block.find_all(['aside', 'div'], class_=re.compile(r'sidebar|related|recommend', re.I)):
                    sidebar.decompose()
            
            search_soup = product_block if product_block else soup
            
            img_selectors = selectors.get("images", ["img[src*='/web/image/product.template/']", "img[src*='/web/image/']"]) or ["img[src]"]
            if isinstance(img_selectors, str):
                img_selectors = [img_selectors]
            for sel in img_selectors:
                for img in search_soup.select(sel):
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
