"""
Scraper MobileParts.shop.
Selectori din config. Căutare / link direct.
"""
import os
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

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
        base_url = site_root  # folosim același domeniu ca în URL (ex. www.mobileparts.shop)
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
            # Fallback: Playwright (browser real) – site-ul dă 403 la requests și afișează „security verification”
            try:
                from playwright.sync_api import sync_playwright
                self.log("   🌐 Încerc cu browser (Playwright)...", "INFO")
                with sync_playwright() as p:
                    # headless=False poate trece verificarea (setează MOBILEPARTS_HEADLESS=0 în .env dacă e nevoie)
                    headless = os.environ.get("MOBILEPARTS_HEADLESS", "1") != "0"
                    browser = p.chromium.launch(headless=headless)
                    page = browser.new_page()
                    page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
                    # Așteptăm să treacă verificarea anti-bot („Performing security verification”)
                    self.log("   ⏳ Aștept verificare securitate site...", "INFO")
                    try:
                        page.wait_for_function(
                            "!document.body.innerText.includes('Performing security verification')",
                            timeout=25000,
                        )
                    except Exception:
                        page.wait_for_timeout(12000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    html = page.content()
                    # Dacă tot e pagina de verificare, mai așteptăm o dată
                    if "Performing security verification" in html or "security verification" in html.lower():
                        page.wait_for_timeout(10000)
                        html = page.content()
                    browser.close()
                soup = BeautifulSoup(html, "html.parser")
                page_text = soup.get_text(separator="\n")
                self._save_debug_html(soup, product_url)
            except ImportError:
                self.log("   ✗ Site-ul MobileParts blochează accesul (403). Pentru a folosi acest furnizor:", "ERROR")
                self.log("      1. În terminal: pip install playwright", "ERROR")
                self.log("      2. Apoi: python -m playwright install chromium", "ERROR")
                self.log("   După instalare rulează din nou procesarea.", "ERROR")
                return None
            except Exception as e:
                self.log(f"   ✗ Eroare descărcare (și Playwright): {e}", "ERROR")
                return None

        selectors = self.config.get("selectors", {})

        name = ""
        for sel in selectors.get("name", ["h1", ".product-title", ".product-name", "[itemprop=name]", "h1[class*='title']", "[class*='product'] h1", ".article-title", ".page-title"]):
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                name = el.get_text(strip=True)
                break
        if not name:
            # Fallback: din textul paginii – linie tip "Battery (Original), Apple iPhone Air"
            skip = ("available for", "here available", "Read more", "Description", "Specifications", "€", "Log in", "Register", "What are you looking")
            for line in page_text.split("\n"):
                line = line.strip()
                if 20 < len(line) < 120 and "Apple" in line and ("," in line or "Original" in line):
                    if not any(s in line for s in skip):
                        name = line[:200]
                        break
        if not name:
            # Fallback: din URL slug (ex. battery-original-apple-iphone-air)
            path = parsed.path.strip("/").split("/")
            for part in reversed(path):
                if part and "article" not in part.lower() and "parts" not in part.lower() and len(part) > 4:
                    name = part.replace("-", " ").title()
                    break
        if not name:
            name = "Produs MobileParts"
        # Curățare: fără prefix SKU și fără " - Mobileparts.shop" la final
        name = re.sub(r"^\d+-\d+\s*-\s*", "", name)
        name = re.sub(r"\s*-\s*Mobileparts?\.shop\s*$", "", name, flags=re.I)
        name = name.strip() or "Produs MobileParts"

        price = 0.0
        for sel in selectors.get("price", [".price", ".product-price", "span.price", "[data-price]", "[class*='price']", "[itemprop=price]"]):
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
        if price <= 0:
            # Fallback: € 63.00 în textul paginii
            m = re.search(r"€\s*([\d]+[.,]\d{2})", page_text)
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
                if len(description) > 30:
                    break
        if not description or len(description) < 20:
            # Fallback: bloc după "Description" sau "Description by manufacturer"
            for marker in ("Description by manufacturer", "Description\n"):
                idx = page_text.find(marker)
                if idx >= 0:
                    rest = page_text[idx + len(marker):].strip().split("\n")
                    for line in rest:
                        line = line.strip()
                        if len(line) > 20 and "€" not in line and "Log in" not in line:
                            description = line[:2000]
                            break
                    if description:
                        break
        if not description:
            description = name

        sku_furnizor = ""
        ean_real = ""
        for sel in selectors.get("sku", [".sku", ".product-sku", "[itemprop=sku]", "[class*='sku']", "[class*='article']", "[data-sku]"]):
            el = soup.select_one(sel)
            if el:
                sku_furnizor = el.get_text(strip=True) or el.get("content") or el.get("data-sku") or ""
                sku_furnizor = str(sku_furnizor).strip()
                if sku_furnizor and re.match(r"^[\dA-Za-z-]+$", sku_furnizor) and len(sku_furnizor) >= 4:
                    ean_real = sku_furnizor
                    break
        if not sku_furnizor:
            # Din URL: /article/parts/661-55235/ sau /parts/661-55235/
            m = re.search(r"/parts?/([0-9]+-[0-9]+)", parsed.path, re.I)
            if m:
                sku_furnizor = m.group(1)
                ean_real = sku_furnizor
            else:
                m = re.search(r"/([0-9]{3,}-[0-9]{2,})[/?]", product_url)
                if m:
                    sku_furnizor = m.group(1)
                    ean_real = sku_furnizor
                else:
                    sku_furnizor = re.sub(r"[^a-zA-Z0-9]", "", product_url[-40:]) or "MP-unknown"

        img_urls = []
        if not self.skip_images:
            seen = set()
            def add_img_url(src):
                if not src or "logo" in src.lower() or "icon" in src.lower() or "pixel" in src.lower():
                    return
                if not src.startswith("http"):
                    src = base_url + src if src.startswith("/") else base_url + "/" + src
                if src not in seen and (".jpg" in src.lower() or ".jpeg" in src.lower() or ".png" in src.lower() or ".webp" in src.lower() or "image" in src.lower()):
                    seen.add(src)
                    img_urls.append(src)

            for sel in selectors.get("images", [
                ".product-images img", ".product-gallery img", ".product-image img",
                "[class*='product'] img", "[class*='article'] img", "[class*='gallery'] img",
                "main img", ".article img", "img[alt*='product']", "img[alt*='Battery']", "img[alt*='Apple']"
            ]):
                for img in soup.select(sel):
                    for attr in ("src", "data-src", "data-lazy-src", "data-srcset"):
                        val = img.get(attr)
                        if not val:
                            continue
                        if attr == "data-srcset":
                            for part in val.split(","):
                                part = part.strip().split()[0]
                                add_img_url(part)
                        else:
                            add_img_url(val)

            if not img_urls:
                for img in soup.select("img"):
                    src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                    if src and ("article" in (img.get("class") or []) or "product" in str(img.get("class") or "").lower() or not any(skip in (img.get("src") or "") for skip in ("logo", "icon", "avatar", "banner", "trusted"))):
                        add_img_url(src)

            if not img_urls:
                raw = str(soup)
                for m in re.finditer(r'["\'](https?://[^"\']*mobileparts\.shop[^"\']*\.(?:jpg|jpeg|png|webp|gif)[^"\']*)["\']', raw, re.I):
                    add_img_url(m.group(1))
                for m in re.finditer(r'["\'](/[^"\']*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\']*)?)["\']', raw, re.I):
                    add_img_url(m.group(1))

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
