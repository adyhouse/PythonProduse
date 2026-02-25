"""
Scraper MPS Mobile (mpsmobile.de). B2B, prețuri cu login.
SKU/EAN din tabele (Art-Nr., GTIN). Preț 0 dacă nu e vizibil.
"""
import json
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
            # Folosește session dacă există (după login), altfel requests normal
            if self.session:
                r = self.session.get(product_url, headers=self._headers(), timeout=30)
            else:
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
            self.log("   🖼️ Descarc imagini MARI...", "INFO")
            # Aceeași ordine și logică ca la MobileSentrix: og:image → JSON-LD → galerie → fallback
            # Rădăcina site-ului fără limbă (imagini sunt mereu la /data/product/images/)
            site_root = "https://mpsmobile.de"

            def _normalize(u):
                if not u or not u.strip():
                    return None
                u = u.strip().split()[0]
                if not u.startswith("http"):
                    u = site_root + u if u.startswith("/") else site_root + "/" + u
                return u

            # MPS: varianta mare e mereu la .../data/product/images/detail/normal/UUID.ext
            _LARGE_PATH = "detail/normal"

            def _canonical_mps_image_url(url):
                """Forțează URL imagine MPS la formă canonică: .../data/product/images/detail/normal/...
                Elimină /en/, /de/. Thumbnail/small devin detail/normal = o singură URL mare, fără duplicate."""
                if not url:
                    return url
                # Extrage UUID + extensie (sau path după data/product/images/)
                for marker in ("data/product/images/", "product/images/"):
                    if marker in url:
                        idx = url.find(marker)
                        suffix = url[idx + len(marker):].split("?")[0].strip()
                        if suffix and ".." not in suffix:
                            # Dacă e thumbnail/small/mini/zoom, folosim detail/normal (o singură variantă per imagine)
                            lower = suffix.lower()
                            if any(lower.startswith(p) for p in ("thumbnail/", "thumb/", "small/", "mini/", "tiny/", "preview/", "small_image/", "detail/zoom/")):
                                filename = suffix.split("/")[-1]
                                if filename and "." in filename:
                                    suffix = _LARGE_PATH + "/" + filename
                            elif "/" not in suffix or not suffix.startswith(_LARGE_PATH):
                                # path necunoscut – dacă avem doar UUID.ext, punem detail/normal
                                if re.match(r"[0-9A-Fa-f-]{36}\.(?:jpg|jpeg|png|webp|gif)$", suffix, re.I):
                                    suffix = _LARGE_PATH + "/" + suffix
                            return site_root + "/data/product/images/" + suffix
                match = re.search(r"([0-9A-Fa-f-]{36}\.(?:jpg|jpeg|png|webp|gif))", url)
                if match:
                    return site_root + "/data/product/images/" + _LARGE_PATH + "/" + match.group(1)
                return url

            def _is_icon_or_logo(url):
                """Exclude icoane, logo-uri (ca la MobileSentrix)."""
                u = url.lower()
                return any(x in u for x in [
                    "logo", "icon", "pixel", "tracking", "avatar", "banner", "sprite",
                    "favicon", "placeholder", "/icons/", "/logo/", "/static/", "/assets/"
                ])

            def _is_image_url(url):
                """Extensie imagine și nu e icoană/logo."""
                if _is_icon_or_logo(url):
                    return False
                u = url.lower()
                return any(ext in u for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])

            def _is_thumbnail_or_small(url):
                """Exclude thumbnail-uri și variante mici – păstrăm doar imaginile mari."""
                if not url:
                    return True
                u = url.lower()
                return any(x in u for x in [
                    "thumbnail", "/thumb/", "/thumbs/", "/small/", "/mini/", "/tiny/",
                    "_thumb", "-thumb", "_s.", "-s.", "small_image", "preview", "/resize/"
                ])

            def _is_product_gallery_image(url):
                """Doar imagini din galeria produsului – exclude block/triple (related), suitable-for (compatibilitate)."""
                if not url:
                    return False
                u = url.lower()
                if "suitable-for" in u or "/block/" in u or "block/triple" in u:
                    return False
                return "data/product/images" in u or "product/images" in u

            seen = set()

            def _add(u):
                u = _canonical_mps_image_url(u) if u else None
                if not u or u in seen:
                    return
                if not _is_image_url(u) or _is_thumbnail_or_small(u):
                    return
                if not _is_product_gallery_image(u):
                    return
                seen.add(u)
                img_urls.append(u)

            # 1. og:image (meta tags – imaginea principală, ca la MobileSentrix)
            og_images = soup.find_all("meta", property="og:image")
            for og_img in og_images:
                content = og_img.get("content")
                if content:
                    u = _normalize(content)
                    if u and not _is_icon_or_logo(u):
                        _add(u)
            if og_images and any(og.get("content") for og in og_images):
                self.log("      ✓ Găsită imagine în og:image", "INFO")

            # 2. JSON-LD (array de imagini produs – ca la MobileSentrix, fără filtru path)
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string or "{}")
                    if isinstance(data, dict) and "image" in data:
                        images = data["image"]
                        if isinstance(images, str):
                            images = [images]
                        elif not isinstance(images, list):
                            continue
                        for img in images[:5]:
                            url = img.get("url", img) if isinstance(img, dict) else img
                            if isinstance(url, str):
                                _add(_normalize(url))
                        if images:
                            self.log(f"      ✓ Găsite {len(images) if isinstance(images, list) else 1} imagini în JSON-LD", "INFO")
                except Exception:
                    pass

            # 2b. Imagini cu data-src/data-image (galeria MPS – thumbnails care au URL mare în atribut)
            for img in soup.find_all("img"):
                for attr in ("data-src", "data-image", "data-image-large-src", "data-zoom-image", "src"):
                    src = img.get(attr)
                    if src and ("detail/normal" in src or "detail/zoom" in src):
                        _add(_normalize(src))
                        break

            # 3. Galerie produs – selectori extinși pentru PrestaShop (toate imaginile)
            img_selectors = selectors.get("images", [
                ".product-image img", ".product-gallery img",
                ".product-images img", ".product-cover img", ".product-thumbnails img",
                "[class*='product-image'] img", "[class*='product-gallery'] img",
                "[class*='gallery'] img", ".images-container img",
                "main img[src*='product/images']", "article img[src*='product/images']",
            ])
            if isinstance(img_selectors, str):
                img_selectors = [img_selectors]
            for sel in img_selectors:
                for img in soup.select(sel):
                    for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-image-large-src", "data-zoom-image", "data-image"):
                        src = img.get(attr)
                        if src:
                            _add(_normalize(src))
                            break
                    srcset = img.get("data-srcset") or img.get("srcset")
                    if srcset:
                        for part in srcset.split(","):
                            _add(_normalize(part.split()[0] if part.strip() else part))
            # Link-uri către imagini mari (PrestaShop uneori pune full-size în href)
            for a in soup.select('a[href*="product/images"], a[href*="data/product"]'):
                href = a.get("href")
                if href and _is_image_url(href):
                    _add(_normalize(href))

            # 4. Fallback: doar în zona produsului (evită imaginile de la "produse similare")
            # Caută blocul care conține SKU-ul produsului pentru a exclude produse similare
            n_before_fallback = len(img_urls)
            product_block = None
            if sku_furnizor and sku_furnizor != "MPS-unknown":
                # Găsește elementul care conține SKU-ul produsului
                for elem in soup.find_all(string=re.compile(re.escape(sku_furnizor), re.I)):
                    parent = elem.find_parent(['main', 'article', 'div', 'section'])
                    if parent:
                        product_block = parent
                        break
            
            # Fallback: caută blocul principal de produs
            if not product_block:
                product_block = (
                    soup.select_one("main") or soup.select_one("[class*='product-detail']")
                    or soup.select_one(".product-detail") or soup.select_one("#product-detail")
                    or soup.select_one("[class*='product-content']") or soup.select_one("article.product")
                    or soup.select_one(".product") or soup.select_one("#product")
                )
            
            # Exclude secțiuni de produse similare/related
            if product_block:
                # Șterge secțiuni care conțin "similar", "related", "recommend", "also"
                for section in product_block.find_all(['section', 'div'], class_=re.compile(r'similar|related|recommend|also|other', re.I)):
                    section.decompose()
                # Șterge sidebar-uri care nu sunt parte din produsul principal
                for sidebar in product_block.find_all(['aside', 'div'], class_=re.compile(r'sidebar|related|recommend', re.I)):
                    sidebar.decompose()
            
            raw_html = str(product_block) if product_block else ""
            # Doar detail/normal și detail/zoom – exclude block/triple (produse related)
            for pattern in [
                r'https?://[^"\')\s]*mpsmobile\.de/data/product/images/detail/(?:normal|zoom)/[^"\')\s]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\')\s]*)?',
                r'"(https?://[^"]*mpsmobile\.de/data/product/images/detail/(?:normal|zoom)/[^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"',
                r'"(/data/product/images/detail/(?:normal|zoom)/[^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"',
                r"'(/data/product/images/detail/(?:normal|zoom)/[^']+\.(?:jpg|jpeg|png|webp|gif)[^']*)'",
            ]:
                for m in re.finditer(pattern, raw_html, re.I):
                    u = m.group(1) if m.lastindex else m.group(0)
                    u = _normalize(u)
                    if u and u not in seen and _is_image_url(u):
                        _add(u)
            if len(img_urls) > n_before_fallback:
                self.log("      ✓ Imagini din path /data/product/images/", "INFO")

            # MPS: până la 10 imagini per produs (toate din galerie)
            img_urls = list(dict.fromkeys(img_urls))[:10]
            if img_urls:
                self.log(f"   🔍 Total imagini găsite: {len(img_urls)}", "INFO")
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
