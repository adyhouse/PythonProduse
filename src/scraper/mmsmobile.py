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

    def _enlarge_odoo_image_url(self, url: str) -> str:
        """Cere imagine mare la Odoo: în path Odoo folosește image_128, image_256, image_1920."""
        if "/web/image/" not in url:
            return url
        # Odoo: dimensiunea e în numele câmpului din path (image_128 → thumbnail, image_1920 → mare)
        for small in ("image_128", "image_256", "image_512", "image_64"):
            if small in url:
                return url.replace(small, "image_1920", 1)
        # Dacă există doar "image" fără _128, adaugă ?size=1024x1024
        if "?" in url:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            qs["size"] = ["1024x1024"]
            return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
        if "/image" in url and "image_1920" not in url:
            return url.rstrip("/") + "?size=1024x1024"
        return url

    def _find_product_url(self, sku_or_query: str) -> Optional[str]:
        base_url = self.config.get("base_url", "https://www.mmsmobile.de").rstrip("/")
        lang = self.config.get("default_language", "en")
        search_url = f"{base_url}/{lang}/shop?search={requests.utils.quote(sku_or_query)}"
        self.log(f"   🔍 Căutare: {search_url}", "INFO")
        try:
            # Folosește session dacă există (după login), altfel requests normal
            if self.session:
                r = self.session.get(search_url, headers=self._headers(), timeout=30)
            else:
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

        # Login dacă e necesar
        if not self._login_if_required():
            self.log("   ⚠️ Continuă fără login (conținutul poate fi limitat)", "WARNING")

        if sku_or_url.startswith("http://") or sku_or_url.startswith("https://"):
            product_url = sku_or_url
            self.log("   ✓ Link direct detectat", "INFO")
        else:
            product_url = self._find_product_url(sku_or_url)
            if not product_url:
                self.log("   ✗ Nu s-a găsit niciun produs.", "ERROR")
                return None

        try:
            # Folosește session dacă există (după login), altfel requests normal – doar cu sesiune autentificată se vede prețul
            if self.session:
                self.log("   📄 Descarc pagina produsului cu sesiune autentificată (zona client)...", "INFO")
                r = self.session.get(product_url, headers=self._headers(), timeout=30)
            else:
                self.log("   📄 Descarc pagina produsului (fără login – prețul poate fi 0)...", "INFO")
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
        # Fallback: preț din tabel (Odoo – doar pentru clienți autentificați)
        if price <= 0:
            for header in ("Price", "List Price", "Preis", "Verkaufspreis", "Sales Price"):
                raw = self._table_value_by_header(soup, header)
                if raw:
                    m = re.search(r"[\d.,]+", raw.replace(",", "."))
                    if m:
                        try:
                            price = float(m.group(0).replace(",", "."))
                            if price > 0:
                                self.log(f"   💶 Preț extras din tabel (header: {header})", "INFO")
                                break
                        except ValueError:
                            pass
        if price > 0:
            self.log(f"   💶 Preț: {price:.2f} EUR", "INFO")
        else:
            self.log("   ⚠️ Preț: 0 – doar zona client (după login) afișează prețul; verifică autentificarea.", "WARNING")

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
            self.log("   🖼️ Descarc imagini MARI (Odoo), selecție în popup – recomandat 4–5 poze...", "INFO")
            # Toate imaginile din pagină cu /web/image/ – cerem dimensiune mare (Odoo acceptă size=...)
            img_selectors = selectors.get("images", ["img[src*='/web/image/product.template/']", "img[src*='/web/image/']"])
            if isinstance(img_selectors, str):
                img_selectors = [img_selectors]
            seen = set()
            for sel in img_selectors:
                for img in soup.select(sel):
                    src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                    if src:
                        if not src.startswith("http"):
                            src = base_url + src if src.startswith("/") else base_url + "/" + src
                        if src not in seen:
                            seen.add(src)
                            img_urls.append(self._enlarge_odoo_image_url(src))
            # Fallback: regex în HTML brut
            if not img_urls:
                raw = str(soup)
                for pattern in [
                    r'["\'](https?://[^"\']*mmsmobile\.de[^"\']*/web/image[^"\']+\.(?:webp|jpg|jpeg|png|gif)[^"\']*)["\']',
                    r'["\'](/web/image[^"\']+\.(?:webp|jpg|jpeg|png|gif)[^"\']*)["\']',
                ]:
                    for m in re.finditer(pattern, raw, re.I):
                        u = m.group(1)
                        if not u.startswith("http"):
                            u = base_url.rstrip("/") + ("/" if not u.startswith("/") else "") + u
                        if u not in seen:
                            seen.add(u)
                            img_urls.append(self._enlarge_odoo_image_url(u))
                    if img_urls:
                        break
            # Păstrăm până la 10 imagini – în popup utilizatorul alege 4–5 (dimensiune + KB afișate)
            img_urls = list(dict.fromkeys(img_urls))[:10]
            if img_urls:
                self.log(f"   🔍 Total imagini găsite: {len(img_urls)} (selectează 4–5 în popup – se afișează dimensiunea și KB)", "INFO")
            else:
                self.log("   ⚠️ Nu am găsit imagini pe pagina produsului", "WARNING")

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
