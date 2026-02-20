"""
Scraper Componenti Digitali (componentidigitali.com).
Prețuri vizibile fără login. SKU extras din text (Item no. / Cod. Art.).
"""
import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper


class ComponentidigitaliScraper(BaseScraper):
    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.config.get("headers", {}).get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self.config.get("headers", {}).get(
                "Accept-Language", "it-IT,it;q=0.9,en-US;q=0.8"
            ),
            "Referer": self.config.get("base_url", "https://www.componentidigitali.com") + "/",
        }

    def _find_product_url(self, sku_or_query: str) -> Optional[str]:
        """Caută produs pe site; returnează URL prima pagină produs găsită."""
        base_url = self.config.get("base_url", "https://www.componentidigitali.com").rstrip("/")
        lang = self.config.get("default_language", "en")
        search_url = f"{base_url}/{lang}/shop?search={requests.utils.quote(sku_or_query)}"
        self.log(f"   🔍 Căutare: {search_url}", "INFO")
        try:
            r = requests.get(search_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            for a in soup.select('a[href*="/shop/"], a[href*="/product"], a[href*=".gp."]'):
                href = a.get("href") or ""
                if href and "shop" in href and base_url in href and href != search_url:
                    if not href.startswith("http"):
                        href = base_url + href if href.startswith("/") else base_url + "/" + href
                    self.log(f"   ✓ Produs găsit: {href[:80]}...", "INFO")
                    return href
            for a in soup.select("a[href]"):
                href = (a.get("href") or "").strip()
                if ".gp." in href and "uw" in href:
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
        base_url = self.config.get("base_url", "https://www.componentidigitali.com").rstrip("/")

        if sku_or_url.startswith("http://") or sku_or_url.startswith("https://"):
            product_url = sku_or_url
            self.log("   ✓ Link direct detectat", "INFO")
        else:
            product_url = self._find_product_url(sku_or_url)
            if not product_url:
                self.log("   ✗ Nu s-a găsit niciun produs pentru acest SKU/căutare.", "ERROR")
                return None

        try:
            r = requests.get(product_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            # Salvează HTML pentru debugging
            self._save_debug_html(soup, product_url)
            page_text = soup.get_text(separator="\n")
        except Exception as e:
            self.log(f"   ✗ Eroare descărcare pagină: {e}", "ERROR")
            return None

        selectors = self.config.get("selectors", {})

        # Cuvinte din meniu/navigare de ignorat (nu sunt nume produs)
        skip_titles = {"servizi", "contatti", "shop", "home", "catalogo", "account", "carrello", "login", "registrati", "ricambi", "smartphone", "accessori", "offerte"}
        def is_valid_name(txt):
            t = (txt or "").strip()
            if len(t) < 4:
                return False
            if t.lower() in skip_titles:
                return False
            return True

        name = ""
        # Încearcă mai întâi titluri din zona produs (main, product, page-content)
        for sel in [".product-title", "h1.page-title", "main h1", "[class*='product'] h1", "[class*='product-detail'] h1", ".product-name", "h1"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                cand = el.get_text(strip=True)
                if is_valid_name(cand):
                    name = cand
                    break
        if not name:
            for sel in selectors.get("name", ["h2", "h3", ".product-title", "h1"]):
                for el in soup.select(sel):
                    if not el or not el.get_text(strip=True):
                        continue
                    cand = el.get_text(strip=True)
                    if not is_valid_name(cand):
                        continue
                    # Evită titluri din nav/menu/header
                    in_nav = False
                    for parent in el.parents:
                        if parent.name in ("nav", "header"):
                            in_nav = True
                            break
                        cls = (parent.get("class") or [])
                        if any("menu" in (c or "").lower() or "nav" in (c or "").lower() for c in cls):
                            in_nav = True
                            break
                    if in_nav:
                        continue
                    if len(cand) > len(name or ""):
                        name = cand
                if name:
                    break
        if not name:
            name = "Produs Componenti Digitali"

        price = 0.0
        for sel in selectors.get("price", [".price", ".price-wrapper .price", "span.price"]):
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(strip=True)
                m = re.search(r"[\d.,]+", txt.replace(",", "."))
                if m:
                    try:
                        price = float(m.group(0).replace(".", "").replace(",", ".") or m.group(0))
                    except ValueError:
                        pass
                    if price > 0:
                        break
        if price == 0.0:
            m = re.search(r"€\s*([\d.,]+)", page_text)
            if m:
                try:
                    price = float(m.group(1).replace(",", "."))
                except ValueError:
                    pass

        description = ""
        for sel in selectors.get("description", [".product-description", ".description", "[itemprop=description]"]):
            el = soup.select_one(sel)
            if el:
                description = el.get_text(separator="\n", strip=True)[:3000]
                if len(description) > 50:
                    break
        if not description:
            description = name

        sku_furnizor = ""
        ean_real = ""
        sku_regex = selectors.get("sku_regex", r"Item no\.:\s*(\d+)|Cod\. Art\.:\s*(\d+)")
        for pattern in [r"Item no\.:\s*(\d+)", r"Cod\. Art\.:\s*(\d+)", r"Art\.?\s*no\.?:\s*(\d+)"]:
            m = re.search(pattern, page_text, re.I)
            if m:
                sku_furnizor = m.group(1)
                ean_real = sku_furnizor
                break

        if not sku_furnizor:
            sku_furnizor = re.sub(r"[^a-zA-Z0-9]", "", product_url[-30:]) or "CD-unknown"

        img_urls = []
        if not self.skip_images:
            for sel in selectors.get("images", [".product-image img", ".product-media img", "img[src*='product']"]):
                for img in soup.select(sel):
                    src = img.get("src") or img.get("data-src")
                    if src and ("product" in src.lower() or "image" in src.lower()):
                        if not src.startswith("http"):
                            src = base_url + src if src.startswith("/") else base_url + "/" + src
                        img_urls.append(src)
            img_urls = list(dict.fromkeys(img_urls))

        product_id = re.sub(r"[^a-zA-Z0-9_-]", "_", (sku_furnizor or product_url)[:50])
        images_data = self._download_images(img_urls, product_id, self._headers()) if img_urls else []

        tags = []
        return self._build_product_data(
            name=name,
            price=price,
            description=description,
            images=images_data,
            sku_furnizor=sku_furnizor,
            ean_real=ean_real,
            source_url=product_url,
            tags=tags,
            soup=soup,
            page_text=page_text,
        )
