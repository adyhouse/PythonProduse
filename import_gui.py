"""
Program Import Produse MobileSentrix → CSV (cu Imagini)
Versiune: 2.0 - cu GUI, download imagini și upload WordPress
"""

import sys
import os

# Fix encoding for Windows
try:
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
except:
    pass

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, colorchooser
import json
import threading
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageTk
from io import BytesIO
from dotenv import load_dotenv, set_key
import re
import html
import uuid
import time
from deep_translator import GoogleTranslator

# Max imagini per produs în CSV. Imagini sunt deja uploadate de script pe WordPress;
# CSV conține doar link-uri către aceste imagini – limitarea reduce volumul per rând la import.
MAX_IMAGES_IN_CSV = 5

# Coduri categorie manuale (sku_list: link | COD) – prioritate față de Ollama
# Ierarhie: PIESE 3 niveluri (Piese > Piese {Brand} > Tip), UNELTE/ACCESORII 2 niveluri
# Slug-uri categorii NU EXISTĂ în site – nu folosi: accesorii-service, accesorii-service-xiaomi,
# baterii-iphone-piese, camere-iphone-piese, ecrane-telefoane, baterii-telefoane
CATEGORY_CODE_MAP = {
    # PIESE (3 nivele)
    'SCR': {'cat': 'Ecrane', 'top': 'Piese', 'prefix': 'SCR'},
    'BAT': {'cat': 'Baterii', 'top': 'Piese', 'prefix': 'BAT'},
    'CAM': {'cat': 'Camere', 'top': 'Piese', 'prefix': 'CAM'},
    'CHG': {'cat': 'Mufe Încărcare', 'top': 'Piese', 'prefix': 'CHG'},
    'FLX': {'cat': 'Flexuri', 'top': 'Piese', 'prefix': 'FLX'},
    'SPK': {'cat': 'Difuzoare', 'top': 'Piese', 'prefix': 'SPK'},
    'CAS': {'cat': 'Carcase', 'top': 'Piese', 'prefix': 'CAS'},
    'STC': {'cat': 'Sticlă', 'top': 'Piese', 'prefix': 'STC'},
    # UNELTE (2 nivele)
    'TOOL': {'cat': 'Unelte', 'sub': 'Șurubelnițe', 'prefix': 'TOOL'},
    'PENS': {'cat': 'Unelte', 'sub': 'Pensete', 'prefix': 'PENS'},
    'SOLD': {'cat': 'Unelte', 'sub': 'Stații Lipit', 'prefix': 'SOLD'},
    'SEP': {'cat': 'Unelte', 'sub': 'Separatoare Ecrane', 'prefix': 'SEP'},
    'MICRO': {'cat': 'Unelte', 'sub': 'Microscoape', 'prefix': 'MICRO'},
    'PROG': {'cat': 'Unelte', 'sub': 'Programatoare', 'prefix': 'PROG'},
    'KIT': {'cat': 'Unelte', 'sub': 'Kituri Complete', 'prefix': 'KIT'},
    'EQP': {'cat': 'Unelte', 'prefix': 'EQP'},
    # ACCESORII (2 nivele)
    'HUSA': {'cat': 'Accesorii', 'sub': 'Huse & Carcase', 'prefix': 'HUSA'},
    'FOIL': {'cat': 'Accesorii', 'sub': 'Folii Protecție', 'prefix': 'FOIL'},
    'CBL': {'cat': 'Accesorii', 'sub': 'Cabluri & Încărcătoare', 'prefix': 'CBL'},
    'CNS': {'cat': 'Accesorii', 'sub': 'Adezivi & Consumabile', 'prefix': 'CNS'},
}

# PIESE: tip piesă (nivel 3) – ordinea contează (cele mai specifice primele)
# SCR, BAT, CAM, CHG, FLX, SPK, CAS conform mapării finale
PIESE_TIP_KEYWORDS = (
    (['screen', 'display', 'lcd', 'oled', 'amoled', 'ecran', 'digitizer', 'touch'], 'Ecrane'),
    (['battery', 'baterie', 'acumulator', 'mah'], 'Baterii'),
    (['camera', 'cameră', 'megapixel', ' mp ', 'lens'], 'Camere'),
    (['charging port', 'mufa', 'dock', 'connector', 'lightning', 'usb-c port', 'usb-c', 'conector încărcare'], 'Mufe Încărcare'),
    (['flex', 'ribbon', 'cable flex', 'flex cable'], 'Flexuri'),
    (['speaker', 'difuzor', 'earpiece', 'buzzer', 'ringer', 'casca'], 'Difuzoare'),
    (['housing', 'frame', 'carcasa', 'back cover', 'back glass', 'chassis', 'carcase'], 'Carcase'),
    (['sticla', 'glass', 'geam'], 'Sticlă'),
    (['buton', 'button', 'power', 'volume', 'home'], 'Butoane'),
)

# UNELTE: subcategorii nivel 2 (Unelte > Subcategorie)
UNELTE_SUBCAT_KEYWORDS = (
    (['screwdriver', 'surubelnita', 'șurubelniță', 'screw driver'], 'Șurubelnițe'),
    (['tweezer', 'penseta', 'pensetă', 'pry', 'spudger'], 'Pensete'),
    (['soldering', 'station', 'lipit', 'hot air', 'rework', 'preheater', 'rework station'], 'Stații Lipit'),
    (['separator', 'separatoare', 'lcd separator', 'screen separator'], 'Separatoare Ecrane'),
    (['microscop', 'microscope', 'magnifier', 'lupa'], 'Microscoape'),
    (['programmer', 'programator', 'box', 'dongle', 'jc', 'jcid'], 'Programatoare'),
    (['kit', 'set', 'tool set', 'repair kit'], 'Kituri Complete'),
)

# Accesorii: subcategorii nivel 2 (Accesorii > Subcategorie)
ACCESORII_SUBCAT_KEYWORDS = (
    (['case', 'husa', 'husă', 'cover', 'bumper', 'carcasă', 'carcasa', 'housing', 'back cover'], 'Huse & Carcase'),
    (['protector', 'folie', 'tempered', 'glass protector', 'screen protector', 'protector ecran', 'uv film', 'film protector', 'matt privacy', 'privacy film'], 'Folii Protecție'),
    (['cable', 'cablu', 'charger', 'încărcător', 'incarcator', 'usb', 'lightning cable', 'adapter', 'adaptor'], 'Cabluri & Încărcătoare'),
    (['adhesive', 'adeziv', 'glue', 'b7000', 't7000', 'oca', 'tape', 'sticker', 'banda', 'consumabil', 'loca'], 'Adezivi & Consumabile'),
)
# Prioritate Folii înainte de Unelte (UV film / film protector → Folii Protecție)
ACCESORII_FOLII_KEYWORDS = ('protector', 'folie', 'tempered', 'glass protector', 'screen protector', 'uv film', 'film protector', 'matt privacy', 'privacy film')

# Fișiere badge: branduri/model/tehnologie custom + ultima confirmare (stil + date)
BADGE_CUSTOM_BRANDS_FILE = 'data/badge_custom_brands.txt'
BADGE_CUSTOM_MODELS_FILE = 'data/badge_custom_models.txt'
BADGE_CUSTOM_TECH_FILE = 'data/badge_custom_tech.txt'
BADGE_LAST_CONFIRMED_FILE = 'data/badge_last_confirmed.json'
BADGE_PRESETS_BY_BRAND_FILE = 'data/badge_presets_by_brand.json'
BADGE_CUSTOM_LIST_FILE = 'data/badge_custom_list.json'
BADGE_DEFAULT_BRANDS = ['', 'JK', 'GX', 'ZY', 'RJ', 'HEX', 'Foxconn', 'Service Pack', 'Apple Original', 'Samsung Original']
BADGE_HZ_OPTIONS = ['', '60Hz', '90Hz', '120Hz', '144Hz', '240Hz']
# Paletă culori rapide (hex)
BADGE_PALETTE = [
    '#4CAF50', '#2196F3', '#FF9800', '#F44336', '#9C27B0', '#607D8B', '#FFD700', '#795548',
    '#00BCD4', '#8BC34A', '#E91E63', '#3F51B5', '#009688', '#CDDC39', '#673AB7', '#000000',
]


def _get_badge_fonts():
    """Fonturi pentru badge-uri (Windows / Linux / fallback)."""
    try:
        if sys.platform == 'win32':
            fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            arial = os.path.join(fonts_dir, 'arialbd.ttf')
            if os.path.exists(arial):
                return (
                    ImageFont.truetype(arial, 32),
                    ImageFont.truetype(arial, 28),
                    ImageFont.truetype(arial, 18),
                )
        for path in [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        ]:
            if os.path.exists(path):
                return (
                    ImageFont.truetype(path, 32),
                    ImageFont.truetype(path, 28),
                    ImageFont.truetype(path, 18),
                )
    except Exception:
        pass
    return ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()


def _draw_text_bbox(draw, xy, text, font):
    """Returnează (width, height) pentru text – compatibil Pillow 8+ (textbbox) sau vechi (textsize)."""
    try:
        bbox = draw.textbbox(xy, text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        w, h = draw.textsize(text, font=font)
        return w, h


def _draw_text_centered(draw, rect, text, font, fill='white'):
    """Desenează text centrat orizontal și vertical în rect. Folosește anchor='mm' pentru aliniere corectă pe înălțime."""
    x0, y0, x1, y1 = rect
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    try:
        draw.text((cx, cy), text, font=font, fill=fill, anchor='mm')
    except TypeError:
        bbox = draw.textbbox((0, 0), text, font=font)
        left, top, right, bottom = bbox
        tw, th = right - left, bottom - top
        text_cx = (left + right) / 2
        text_cy = (top + bottom) / 2
        draw.text((int(cx - text_cx), int(cy - text_cy)), text, font=font, fill=fill)


def _draw_text_vertical_centered(overlay, draw, rect, text, font, fill='white'):
    """Desenează text rotit 90° (vertical), centrat în rect. Spațiu suficient ca textul să nu fie tăiat."""
    x0, y0, x1, y1 = rect
    tw, th = _draw_text_bbox(draw, (0, 0), text, font)
    pad = max(16, min(tw, th) // 2)
    w_canvas = max(int(tw) + pad * 2, 8)
    h_canvas = max(int(th) + pad * 2, 8)
    small = Image.new('RGBA', (w_canvas, h_canvas), (0, 0, 0, 0))
    small_draw = ImageDraw.Draw(small)
    cx_s, cy_s = w_canvas / 2, h_canvas / 2
    try:
        small_draw.text((cx_s, cy_s), text, font=font, fill=fill, anchor='mm')
    except TypeError:
        small_draw.text((pad, pad), text, font=font, fill=fill)
    rotated = small.rotate(90, expand=True)
    rw, rh = rotated.size
    rx0 = int(x0 + (x1 - x0 - rw) / 2)
    ry0 = int(y0 + (y1 - y0 - rh) / 2)
    overlay.paste(rotated, (rx0, ry0), rotated)


def _parse_hex_color(hex_str, default='#666666'):
    """Returnează hex cu E6 (alpha) pentru overlay; dacă invalid, default."""
    s = (hex_str or '').strip()
    if not s:
        return default + 'E6' if len(default) == 7 else default
    if s.startswith('#'):
        s = s[1:]
    if len(s) == 6 and all(c in '0123456789AaBbCcDdEeFf' for c in s):
        return '#' + s + 'E6'
    return default + 'E6' if len(default) == 7 else default


def generate_badge_preview(image_path, badge_data, output_path=None, style=None, script_dir=None):
    """
    Generează imagine cu badge-uri (brand, model, tehnologie, Hz, IC, TrueTone) + badge-uri custom (text/emoji/imagine).
    script_dir: folder pentru căi relative la imaginile custom (badge predefinite).
    """
    style = style or {}
    base_dir = Path(script_dir or Path(image_path or '.').resolve().parent)
    img = Image.open(image_path)
    if img.mode not in ('RGBA', 'LA'):
        img = img.convert('RGBA')
    elif img.mode == 'LA':
        img = img.convert('RGBA')
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = img.size

    def font_with_size(size_key, default_size):
        size = int(style.get(size_key, default_size))
        try:
            if sys.platform == 'win32':
                arial = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arialbd.ttf')
                if os.path.exists(arial):
                    return ImageFont.truetype(arial, min(max(size, 8), 72))
            for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']:
                if os.path.exists(path):
                    return ImageFont.truetype(path, min(max(size, 8), 72))
        except Exception:
            pass
        return ImageFont.load_default()

    font_brand = font_with_size('brand_font_size', 42)
    font_model = font_with_size('model_font_size', 34)
    font_badge = font_with_size('badges_font_size', 24)

    brand_colors = {
        'JK': '#4CAF50', 'GX': '#2196F3', 'ZY': '#FF9800', 'RJ': '#F44336',
        'HEX': '#9C27B0', 'Foxconn': '#607D8B', 'Service Pack': '#FFD700',
        'Apple Original': '#A0A0A0', 'Samsung Original': '#1428A0',
    }

    margin = int(style.get('margin', 20))
    brand_offset_x = int(style.get('brand_offset_x', 0))
    brand_offset_y = int(style.get('brand_offset_y', 0))
    brand_pos = (style.get('brand_pos') or 'top_left').strip().lower()
    brand_shape = (style.get('brand_shape') or 'rounded').strip().lower()
    if badge_data.get('brand'):
        brand = str(badge_data['brand']).strip()
        brand_color = _parse_hex_color(style.get('brand_bg') or brand_colors.get(brand, '#666666'))
        brand_text = brand.upper()
        tw, th = _draw_text_bbox(draw, (0, 0), brand_text, font_brand)
        padding = int(style.get('brand_padding', 14))
        vertical_pill = brand_shape == 'pill_vertical'
        if vertical_pill:
            side = max(tw, th) + padding * 2
            w_rect = side
            h_rect = side
        else:
            w_rect = tw + padding * 2
            h_rect = th + padding * 2
        brand_fx = style.get('brand_x')
        brand_fy = style.get('brand_y')
        if brand_fx is not None and brand_fy is not None:
            try:
                x0 = int(brand_fx) + brand_offset_x
                y0 = int(brand_fy) + brand_offset_y
            except (TypeError, ValueError):
                x0 = margin + brand_offset_x
                y0 = margin + brand_offset_y
        elif 'right' in brand_pos:
            x0 = width - margin - w_rect + brand_offset_x
            y0 = margin + brand_offset_y
        else:
            x0 = margin + brand_offset_x
            y0 = margin + brand_offset_y
        rect = [x0, y0, x0 + w_rect, y0 + h_rect]
        radius = 0 if brand_shape == 'rect' else (min(w_rect, h_rect) // 2 if brand_shape in ('pill', 'pill_vertical') else 10)
        if radius > 0:
            draw.rounded_rectangle(rect, radius=radius, fill=brand_color)
        else:
            draw.rectangle(rect, fill=brand_color)
        if vertical_pill:
            _draw_text_vertical_centered(overlay, draw, rect, brand_text, font_brand, 'white')
        else:
            _draw_text_centered(draw, rect, brand_text, font_brand, 'white')

    model_offset_x = int(style.get('model_offset_x', 0))
    model_offset_y = int(style.get('model_offset_y', 0))
    model_vertical = style.get('model_vertical') or (style.get('model_shape') or '').strip().lower() == 'pill_vertical'
    model_pos = (style.get('model_pos') or 'center').strip().lower()
    model_bg = _parse_hex_color(style.get('model_bg'), '#000000')
    model_padding = int(style.get('model_padding', 18))
    if badge_data.get('model'):
        model = str(badge_data['model']).strip()
        tw, th = _draw_text_bbox(draw, (0, 0), model, font_model)
        if model_vertical:
            side = max(tw, th) + model_padding * 2
            rw, rh = side, side
        else:
            rw, rh = tw + model_padding * 2, th + model_padding * 2
        model_fx, model_fy = style.get('model_x'), style.get('model_y')
        if model_fx is not None and model_fy is not None:
            try:
                x0 = int(model_fx) + model_offset_x
                y0 = int(model_fy) + model_offset_y
            except (TypeError, ValueError):
                x0 = (width - rw) // 2 + model_offset_x
                y0 = (height - rh) // 2 - 20 + model_offset_y
        elif 'center' in model_pos:
            x0 = (width - rw) // 2 + model_offset_x
            y0 = (height - rh) // 2 - 20 + model_offset_y
        elif 'left' in model_pos:
            x0 = margin + model_offset_x
            y0 = (height - rh) // 2 + model_offset_y
        else:
            x0 = width - margin - rw + model_offset_x
            y0 = (height - rh) // 2 + model_offset_y
        rect = [x0, y0, x0 + rw, y0 + rh]
        draw.rounded_rectangle(rect, radius=12, fill=model_bg if len(model_bg) > 7 else model_bg + 'B3')
        if model_vertical:
            _draw_text_vertical_centered(overlay, draw, rect, model, font_model, 'white')
        else:
            _draw_text_centered(draw, rect, model, font_model, 'white')

    badges_offset_x = int(style.get('badges_offset_x', 0))
    badges_offset_y = int(style.get('badges_offset_y', 0))

    badges = []
    if badge_data.get('tehnologie'):
        badges.append(('tech', str(badge_data['tehnologie'])))
    hz_text = (badge_data.get('hz_text') or '').strip() or (badge_data.get('hz_120') and '120Hz' or '')
    if hz_text:
        badges.append(('hz', hz_text))
    if badge_data.get('ic_transferabil'):
        badges.append(('ic', 'IC Transferabil'))
    if badge_data.get('truetone'):
        badges.append(('tt', 'TT ✓'))

    badges_vertical = bool(style.get('badges_vertical'))
    badges_pos = (style.get('badges_pos') or 'bottom_center').strip().lower()
    badge_extra = int(style.get('badges_padding', 14))
    badge_height = int(style.get('badges_font_size', 24)) + badge_extra
    badge_padding = badge_extra
    badge_margin = int(style.get('badges_spacing', 10))
    bottom_margin = int(style.get('bottom_margin', 24))
    badge_colors_map = {'tech': '#2196F3', 'hz': '#9C27B0', 'ic': '#4CAF50', 'tt': '#FF9800'}
    badges_fx, badges_fy = style.get('badges_x'), style.get('badges_y')
    if badges:
        badge_widths = []
        badge_heights = []
        for _, text in badges:
            tw, th = _draw_text_bbox(draw, (0, 0), text, font_badge)
            if badges_vertical:
                side = max(tw, th) + badge_padding * 2
                badge_widths.append(side)
                badge_heights.append(side)
            else:
                badge_widths.append(tw + badge_padding * 2)
                badge_heights.append(badge_height)
        total_width = sum(badge_widths) + badge_margin * (len(badges) - 1)
        row_height = max(badge_heights) if badge_heights else badge_height
        if badges_fx is not None and badges_fy is not None:
            try:
                start_x = int(badges_fx) - total_width // 2
                y = int(badges_fy) - row_height // 2
            except (TypeError, ValueError):
                start_x = (width - total_width) // 2 + badges_offset_x
                y = height - bottom_margin - row_height + badges_offset_y
        else:
            if 'bottom_right' in badges_pos:
                start_x = width - margin - total_width
            elif 'bottom_left' in badges_pos:
                start_x = margin
            else:
                start_x = (width - total_width) // 2
            start_x += badges_offset_x
            y = height - bottom_margin - row_height + badges_offset_y
        current_x = start_x
        override_bg = style.get('badges_bg')
        for i, (badge_type, text) in enumerate(badges):
            w = badge_widths[i]
            h = badge_heights[i] if badges_vertical else badge_height
            color = _parse_hex_color(override_bg) if override_bg else (badge_colors_map.get(badge_type, '#666666') + 'E6')
            if len(color) == 7:
                color = color + 'E6'
            rect = [current_x, y, current_x + w, y + h]
            draw.rounded_rectangle(rect, radius=8, fill=color)
            if badges_vertical:
                _draw_text_vertical_centered(overlay, draw, rect, text, font_badge, 'white')
            else:
                _draw_text_centered(draw, rect, text, font_badge, 'white')
            current_x += w + badge_margin

    custom_badges = style.get('custom_badges') or []
    if custom_badges and isinstance(custom_badges, list):
        for item in custom_badges:
            if not isinstance(item, dict):
                continue
            try:
                kind = (item.get('type') or 'text').strip().lower()
                px = int(item.get('x', 0))
                py = int(item.get('y', 0))
                scale = float(item.get('scale', 1.0))
                if kind == 'image' and item.get('path'):
                    path = Path(item.get('path'))
                    if not path.is_absolute():
                        path = base_dir / path
                    if path.exists():
                        deco = Image.open(path).convert('RGBA')
                        if scale != 1.0:
                            nw, nh = int(deco.width * scale), int(deco.height * scale)
                            deco = deco.resize((nw, nh), Image.Resampling.LANCZOS)
                        overlay.paste(deco, (px, py), deco)
                else:
                    txt = (item.get('text') or '').strip() or item.get('emoji', '')
                    if not txt:
                        continue
                    fsize = int(item.get('font_size', 24))
                    try:
                        if sys.platform == 'win32':
                            arial = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arialbd.ttf')
                            cfont = ImageFont.truetype(arial, min(max(fsize, 8), 72)) if os.path.exists(arial) else font_badge
                        else:
                            cfont = font_badge
                    except Exception:
                        cfont = font_badge
                    tw, th = _draw_text_bbox(draw, (0, 0), txt, cfont)
                    pad = 8
                    vertical = bool(item.get('vertical'))
                    if vertical:
                        side = max(tw, th) + pad * 2
                        wbox, hbox = side, side
                    else:
                        wbox, hbox = tw + pad * 2, th + pad * 2
                    if scale != 1.0:
                        wbox, hbox = int(wbox * scale), int(hbox * scale)
                    bx0 = px
                    by0 = py
                    rect_c = [bx0, by0, bx0 + wbox, by0 + hbox]
                    bg = (item.get('bg') or '').strip()
                    if bg:
                        draw.rounded_rectangle(rect_c, radius=6, fill=_parse_hex_color(bg))
                    if vertical:
                        _draw_text_vertical_centered(overlay, draw, rect_c, txt, cfont, (item.get('color') or 'white'))
                    else:
                        _draw_text_centered(draw, rect_c, txt, cfont, (item.get('color') or 'white'))
            except Exception:
                pass

    img = Image.alpha_composite(img, overlay)
    if output_path:
        img.save(output_path, 'WEBP', quality=90)
        return output_path
    return img


def load_custom_brands(script_dir):
    """Încarcă lista de branduri custom din data/badge_custom_brands.txt."""
    path = Path(script_dir) / BADGE_CUSTOM_BRANDS_FILE
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return []


def save_custom_brand(script_dir, brand_name):
    """Adaugă un brand în data/badge_custom_brands.txt (dacă nu există)."""
    if not (brand_name and brand_name.strip()):
        return
    path = Path(script_dir) / BADGE_CUSTOM_BRANDS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = set(load_custom_brands(script_dir))
    if brand_name.strip() in existing:
        return
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(brand_name.strip() + '\n')
    except Exception:
        pass


def _badge_data_dir(script_dir):
    return Path(script_dir) / 'data'


def load_lines_file(script_dir, filename, default_lines=None):
    """Încarcă linii dintr-un fișier din data/ (ex: modele, tehnologii)."""
    path = _badge_data_dir(script_dir) / filename
    if not path.exists():
        return list(default_lines or [])
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return list(default_lines or [])


def save_line_to_file(script_dir, filename, line):
    """Adaugă o linie în fișier (dacă nu există)."""
    if not (line and str(line).strip()):
        return
    _badge_data_dir(script_dir).mkdir(parents=True, exist_ok=True)
    path = _badge_data_dir(script_dir) / filename
    existing = set(load_lines_file(script_dir, filename, []))
    s = str(line).strip()
    if s in existing:
        return
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(s + '\n')
    except Exception:
        pass


def load_badge_last_confirmed(script_dir):
    """Încarcă ultima confirmare badge (date + style) din data/badge_last_confirmed.json."""
    path = _badge_data_dir(script_dir) / Path(BADGE_LAST_CONFIRMED_FILE).name
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_badge_last_confirmed(script_dir, data_dict, style_dict, apply_badges=True):
    """Salvează ultima confirmare (pentru Reset)."""
    path = _badge_data_dir(script_dir) / Path(BADGE_LAST_CONFIRMED_FILE).name
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'data': data_dict, 'style': style_dict or {}, 'apply_badges': apply_badges}, f, indent=2)
    except Exception:
        pass


def load_badge_presets_by_brand(script_dir):
    """Încarcă preseturi per brand (data + style) din data/badge_presets_by_brand.json."""
    path = _badge_data_dir(script_dir) / Path(BADGE_PRESETS_BY_BRAND_FILE).name
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_badge_preset_for_brand(script_dir, brand_key, data_dict, style_dict, apply_badges=True):
    """Salvează preset complet pentru un brand (folosit la încărcare și la Reset per brand)."""
    path = _badge_data_dir(script_dir) / Path(BADGE_PRESETS_BY_BRAND_FILE).name
    path.parent.mkdir(parents=True, exist_ok=True)
    presets = load_badge_presets_by_brand(script_dir)
    key = (brand_key or '').strip() or '_fara_brand'
    presets[key] = {'data': data_dict, 'style': style_dict or {}, 'apply_badges': apply_badges}
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2)
    except Exception:
        pass


class BadgePreviewWindow:
    """Fereastră badge-uri: Skip poză / următoarea, 120Hz editabil, IC Transferabil, preset per brand, Reset la preset brand."""

    def __init__(self, parent, image_path, detected_data, callback, script_dir=None, image_index=0, total_images=1):
        self.window = tk.Toplevel(parent)
        self.window.title("Preview Badge-uri - WebGSM")
        self.window.geometry("1120x840")
        self.window.minsize(920, 660)
        self.window.transient(parent)
        self.window.grab_set()
        self.image_path = image_path
        self.callback = callback
        self.script_dir = script_dir or Path(__file__).resolve().parent
        self.badge_data = dict(detected_data) if detected_data else {}
        self.image_index = image_index
        self.total_images = total_images
        self._last_confirmed = load_badge_last_confirmed(self.script_dir)
        self._presets_by_brand = load_badge_presets_by_brand(self.script_dir)
        self.setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.on_skip)
        self.window.lift()
        self.window.focus_force()
        self.window.after(100, self._delayed_preview)

    def _make_scroll_frame(self, parent, width=380):
        canvas = tk.Canvas(parent, width=width, highlightthickness=0, bg='#f5f5f5')
        scrollbar = ttk.Scrollbar(parent)
        frame = ttk.Frame(canvas)
        scr_window = canvas.create_window((0, 0), window=frame, anchor=tk.NW)
        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox(tk.ALL))
        def _on_canvas_configure(e):
            canvas.itemconfig(scr_window, width=max(width, e.width))
        frame.bind('<Configure>', _on_frame_configure)
        canvas.bind('<Configure>', _on_canvas_configure)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=canvas.yview)
        return frame

    def _color_palette_frame(self, parent, var, label_text):
        f = ttk.Frame(parent)
        ttk.Label(f, text=label_text).pack(anchor=tk.W)
        row = ttk.Frame(f)
        row.pack(anchor=tk.W)
        for i, hex_color in enumerate(BADGE_PALETTE):
            btn = tk.Button(row, width=2, bg=hex_color, activebackground=hex_color,
                            command=lambda c=hex_color: self._set_color_var(var, c))
            btn.pack(side=tk.LEFT, padx=1, pady=2)
            if (i + 1) % 8 == 0:
                row = ttk.Frame(f)
                row.pack(anchor=tk.W)
        sub = ttk.Frame(f)
        sub.pack(anchor=tk.W, pady=2)
        ttk.Button(sub, text="Alege culoare...", width=14, command=lambda: self._pick_color(var)).pack(side=tk.LEFT, padx=(0, 6))
        entry = ttk.Entry(sub, textvariable=var, width=10)
        entry.pack(side=tk.LEFT)
        var.trace_add('write', lambda *a: self.update_preview())
        return f

    def _set_color_var(self, var, hex_color):
        var.set(hex_color)
        self.update_preview()

    def _pick_color(self, var):
        c = colorchooser.askcolor(color=var.get() or '#666666', title='Alege culoare')
        if c and c[1]:
            var.set(c[1])
            self.update_preview()

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        left_frame = ttk.LabelFrame(main_frame, text="Preview imagine", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.preview_label = tk.Label(left_frame, bg='#2d2d2d', fg='#e0e0e0', text='Se încarcă...', font=('', 11))
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(12, 0))
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # —— Tab Conținut ——
        tab_content = ttk.Frame(notebook, padding=8)
        notebook.add(tab_content, text="Conținut")
        rf = self._make_scroll_frame(tab_content)

        title_text = f"Imagine {self.image_index + 1} din {self.total_images}"
        ttk.Label(rf, text=title_text, font=('', 11, 'bold')).pack(anchor=tk.W, pady=(0, 4))
        self.apply_badges_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(rf, text="Aplică badge-uri pe această imagine", variable=self.apply_badges_var, command=self.update_preview).pack(anchor=tk.W, pady=(0, 8))
        ttk.Separator(rf, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 8))

        ttk.Label(rf, text="Brand piesa (sau introduce manual):").pack(anchor=tk.W)
        brand_values = BADGE_DEFAULT_BRANDS + load_custom_brands(self.script_dir)
        self.brand_var = tk.StringVar(value=self.badge_data.get('brand', '') or '')
        self.brand_combo = ttk.Combobox(rf, textvariable=self.brand_var, width=26)
        self.brand_combo['values'] = list(dict.fromkeys([''] + [b for b in brand_values if b]))
        self.brand_combo.pack(fill=tk.X, pady=(0, 2))
        self.brand_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        self.brand_combo.bind('<KeyRelease>', lambda e: self.update_preview())
        ttk.Button(rf, text="Salvează brand în listă", command=self._save_current_brand).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(rf, text="Model compatibil (sau introduce manual):").pack(anchor=tk.W)
        model_defaults = ['', 'iPhone 17 Pro Max', 'iPhone 17 Pro', 'iPhone 16 Pro Max', 'iPhone 16 Pro', 'iPhone 15 Pro Max', 'iPhone 15 Pro', 'iPhone 14 Pro Max', 'iPhone 14', 'iPhone 13', 'iPhone 12', 'Galaxy S24 Ultra', 'Galaxy S24', 'Galaxy S23 Ultra']
        model_values = list(dict.fromkeys(model_defaults + load_lines_file(self.script_dir, Path(BADGE_CUSTOM_MODELS_FILE).name, [])))
        self.model_var = tk.StringVar(value=self.badge_data.get('model', '') or '')
        self.model_combo = ttk.Combobox(rf, textvariable=self.model_var, width=26)
        self.model_combo['values'] = model_values
        self.model_combo.pack(fill=tk.X, pady=(0, 2))
        self.model_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        self.model_combo.bind('<KeyRelease>', lambda e: self.update_preview())
        ttk.Button(rf, text="Salvează model în listă", command=self._save_current_model).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(rf, text="Tehnologie (sau introduce manual):").pack(anchor=tk.W)
        tech_defaults = ['', 'Soft OLED', 'Hard OLED', 'OLED', 'Incell', 'LCD', 'TFT', 'AMOLED']
        tech_values = list(dict.fromkeys(tech_defaults + load_lines_file(self.script_dir, Path(BADGE_CUSTOM_TECH_FILE).name, [])))
        self.tech_var = tk.StringVar(value=self.badge_data.get('tehnologie', '') or '')
        self.tech_combo = ttk.Combobox(rf, textvariable=self.tech_var, width=26)
        self.tech_combo['values'] = tech_values
        self.tech_combo.pack(fill=tk.X, pady=(0, 2))
        self.tech_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        self.tech_combo.bind('<KeyRelease>', lambda e: self.update_preview())
        ttk.Button(rf, text="Salvează tehnologie în listă", command=self._save_current_tech).pack(anchor=tk.W, pady=(0, 12))

        ttk.Separator(rf, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(rf, text="Frecvență (Hz) – text pe badge:").pack(anchor=tk.W)
        self.hz_text_var = tk.StringVar(value=self.badge_data.get('hz_text') or ('120Hz' if self.badge_data.get('hz_120') else ''))
        hz_combo = ttk.Combobox(rf, textvariable=self.hz_text_var, width=14)
        hz_combo['values'] = BADGE_HZ_OPTIONS
        hz_combo.pack(fill=tk.X, pady=(0, 4))
        hz_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        hz_combo.bind('<KeyRelease>', lambda e: self.update_preview())
        ttk.Label(rf, text="(ex: 60Hz, 90Hz, 120Hz sau gol)").pack(anchor=tk.W)
        self.ic_var = tk.BooleanVar(value=bool(self.badge_data.get('ic_transferabil')))
        ttk.Checkbutton(rf, text="IC Transferabil (text pe badge)", variable=self.ic_var, command=self.update_preview).pack(anchor=tk.W, pady=(6, 0))
        self.tt_var = tk.BooleanVar(value=bool(self.badge_data.get('truetone')))
        ttk.Checkbutton(rf, text="TrueTone", variable=self.tt_var, command=self.update_preview).pack(anchor=tk.W)

        # —— Tab Aspect ——
        tab_style = ttk.Frame(notebook, padding=8)
        notebook.add(tab_style, text="Aspect")
        sf = self._make_scroll_frame(tab_style)

        def _spin(parent, label, var, from_, to, default):
            ttk.Label(parent, text=label).pack(anchor=tk.W)
            s = ttk.Spinbox(parent, from_=from_, to=to, textvariable=var, width=6, command=self.update_preview)
            s.pack(fill=tk.X, pady=(0, 6))
            var.trace_add('write', lambda *a: self.update_preview())

        ttk.Label(sf, text="Brand", font=('', 10, 'bold')).pack(anchor=tk.W, pady=(4, 2))
        self.brand_bg_var = tk.StringVar(value='')
        self._color_palette_frame(sf, self.brand_bg_var, "Culoare fundal (gol = automat):").pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(sf, text="Poziție:").pack(anchor=tk.W)
        self.brand_pos_var = tk.StringVar(value='top_left')
        ttk.Combobox(sf, textvariable=self.brand_pos_var, width=14, values=['top_left', 'top_right']).pack(fill=tk.X, pady=(0, 2))
        self.brand_pos_var.trace_add('write', lambda *a: self.update_preview())
        ttk.Label(sf, text="Formă:").pack(anchor=tk.W)
        self.brand_shape_var = tk.StringVar(value='rounded')
        ttk.Combobox(sf, textvariable=self.brand_shape_var, width=18, values=['rounded', 'rect', 'pill', 'pill_vertical']).pack(fill=tk.X, pady=(0, 2))
        self.brand_shape_var.trace_add('write', lambda *a: self.update_preview())
        ttk.Label(sf, text="(pill_vertical = pill cu text pe verticală)").pack(anchor=tk.W)
        self.brand_font_var = tk.StringVar(value='42')
        _spin(sf, "Font brand (px):", self.brand_font_var, 12, 96, 42)
        self.brand_padding_var = tk.StringVar(value='14')
        _spin(sf, "Padding brand (px):", self.brand_padding_var, 4, 40, 14)
        self.brand_offset_x_var = tk.StringVar(value='0')
        _spin(sf, "Offset X brand (px):", self.brand_offset_x_var, -300, 300, 0)
        self.brand_offset_y_var = tk.StringVar(value='0')
        _spin(sf, "Offset Y brand (px):", self.brand_offset_y_var, -300, 300, 0)
        ttk.Label(sf, text="Poziție liberă (gol = automat):").pack(anchor=tk.W)
        self.brand_x_var = tk.StringVar(value='')
        ttk.Entry(sf, textvariable=self.brand_x_var, width=8).pack(fill=tk.X, pady=(0, 2))
        self.brand_x_var.trace_add('write', lambda *a: self.update_preview())
        self.brand_y_var = tk.StringVar(value='')
        ttk.Entry(sf, textvariable=self.brand_y_var, width=8).pack(fill=tk.X, pady=(0, 6))
        self.brand_y_var.trace_add('write', lambda *a: self.update_preview())
        ttk.Label(sf, text="X, Y brand (px din colțul stânga-sus)").pack(anchor=tk.W)

        ttk.Label(sf, text="Model (centru)", font=('', 10, 'bold')).pack(anchor=tk.W, pady=(8, 2))
        self.model_bg_var = tk.StringVar(value='')
        self._color_palette_frame(sf, self.model_bg_var, "Culoare (gol = negru):").pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(sf, text="Poziție model:").pack(anchor=tk.W)
        self.model_pos_var = tk.StringVar(value='center')
        ttk.Combobox(sf, textvariable=self.model_pos_var, width=14, values=['center', 'top_left', 'top_right']).pack(fill=tk.X, pady=(0, 6))
        self.model_pos_var.trace_add('write', lambda *a: self.update_preview())
        self.model_vertical_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(sf, text="Model vertical (text rotit 90°)", variable=self.model_vertical_var, command=self.update_preview).pack(anchor=tk.W)
        self.model_font_var = tk.StringVar(value='34')
        _spin(sf, "Font model (px):", self.model_font_var, 12, 72, 34)
        self.model_padding_var = tk.StringVar(value='18')
        _spin(sf, "Padding model (px):", self.model_padding_var, 6, 48, 18)
        self.model_offset_x_var = tk.StringVar(value='0')
        _spin(sf, "Offset X model (px):", self.model_offset_x_var, -300, 300, 0)
        self.model_offset_y_var = tk.StringVar(value='0')
        _spin(sf, "Offset Y model (px):", self.model_offset_y_var, -300, 300, 0)
        ttk.Label(sf, text="Poziție liberă (gol = automat):").pack(anchor=tk.W)
        self.model_x_var = tk.StringVar(value='')
        ttk.Entry(sf, textvariable=self.model_x_var, width=8).pack(fill=tk.X, pady=(0, 2))
        self.model_x_var.trace_add('write', lambda *a: self.update_preview())
        self.model_y_var = tk.StringVar(value='')
        ttk.Entry(sf, textvariable=self.model_y_var, width=8).pack(fill=tk.X, pady=(0, 6))
        self.model_y_var.trace_add('write', lambda *a: self.update_preview())
        ttk.Label(sf, text="X, Y model (px din colțul stânga-sus)").pack(anchor=tk.W)

        ttk.Label(sf, text="Badge-uri jos (120Hz, IC, TT, tehnologie)", font=('', 10, 'bold')).pack(anchor=tk.W, pady=(8, 2))
        self.badges_bg_var = tk.StringVar(value='')
        self._color_palette_frame(sf, self.badges_bg_var, "Culoare comună (gol = per tip):").pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(sf, text="Poziție:").pack(anchor=tk.W)
        self.badges_pos_var = tk.StringVar(value='bottom_center')
        ttk.Combobox(sf, textvariable=self.badges_pos_var, width=14, values=['bottom_center', 'bottom_left', 'bottom_right']).pack(fill=tk.X, pady=(0, 6))
        self.badges_pos_var.trace_add('write', lambda *a: self.update_preview())
        self.badges_font_var = tk.StringVar(value='24')
        _spin(sf, "Font badge-uri (px):", self.badges_font_var, 10, 48, 24)
        self.badges_padding_var = tk.StringVar(value='14')
        _spin(sf, "Padding badge (px):", self.badges_padding_var, 6, 32, 14)
        self.badges_spacing_var = tk.StringVar(value='10')
        _spin(sf, "Spațiu între badge-uri (px):", self.badges_spacing_var, 2, 24, 10)
        self.badges_vertical_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(sf, text="Badge-uri jos verticale (text rotit 90°)", variable=self.badges_vertical_var, command=self.update_preview).pack(anchor=tk.W)
        self.badges_offset_x_var = tk.StringVar(value='0')
        _spin(sf, "Offset X badge-uri (px):", self.badges_offset_x_var, -300, 300, 0)
        self.badges_offset_y_var = tk.StringVar(value='0')
        _spin(sf, "Offset Y badge-uri (px):", self.badges_offset_y_var, -300, 300, 0)
        ttk.Label(sf, text="Poziție liberă centru rând (gol = automat):").pack(anchor=tk.W)
        self.badges_x_var = tk.StringVar(value='')
        ttk.Entry(sf, textvariable=self.badges_x_var, width=8).pack(fill=tk.X, pady=(0, 2))
        self.badges_x_var.trace_add('write', lambda *a: self.update_preview())
        self.badges_y_var = tk.StringVar(value='')
        ttk.Entry(sf, textvariable=self.badges_y_var, width=8).pack(fill=tk.X, pady=(0, 6))
        self.badges_y_var.trace_add('write', lambda *a: self.update_preview())
        self.bottom_margin_var = tk.StringVar(value='24')
        _spin(sf, "Margine jos (px):", self.bottom_margin_var, 8, 60, 24)
        self.margin_var = tk.StringVar(value='20')
        _spin(sf, "Margine generală (px):", self.margin_var, 8, 60, 20)

        # —— Tab Badge-uri extra (text/emoji/imagine, poziție liberă) ——
        tab_extra = ttk.Frame(notebook, padding=8)
        notebook.add(tab_extra, text="Badge-uri extra")
        ef = self._make_scroll_frame(tab_extra)
        ttk.Label(ef, text="Badge-uri predefinite (text, emoji sau imagine) poziționabile oriunde.", font=('', 10, 'bold')).pack(anchor=tk.W, pady=(0, 6))
        self.custom_badges_list = getattr(self, 'custom_badges_list', [])
        self._custom_badges_listbox_var = tk.Variable(value=[f"{i.get('type','')} @ ({i.get('x',0)},{i.get('y',0)})" for i in self.custom_badges_list])
        lb_frame = ttk.Frame(ef)
        lb_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        listbox = tk.Listbox(lb_frame, listvariable=self._custom_badges_listbox_var, height=4, selectmode=tk.SINGLE)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(lb_frame, command=listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=sb.set)
        self._custom_badges_listbox = listbox
        btn_row = ttk.Frame(ef)
        btn_row.pack(fill=tk.X, pady=4)
        ttk.Button(btn_row, text="+ Text/Emoji", command=self._add_custom_text_badge).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="+ Imagine", command=self._add_custom_image_badge).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Șterge", command=self._remove_custom_badge).pack(side=tk.LEFT, padx=4)
        ttk.Button(ef, text="Încarcă listă din fișier...", command=self._load_custom_badges_file).pack(anchor=tk.W, pady=4)
        ttk.Button(ef, text="Salvează listă în fișier...", command=self._save_custom_badges_file).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(ef, text="Fișier: data/badge_custom_list.json (căi relative la folderul scriptului)").pack(anchor=tk.W)

        # Butoane acțiuni (sub notebook)
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        if self.total_images > 1:
            ttk.Button(btn_frame, text="⏭ Skip → următoarea poză", command=self.on_skip_image).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="↩ Reset (setare brand)", command=self._reset_to_brand_preset).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="✓ Confirmă", command=self.on_confirm).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="⟳ Batch", command=self.on_batch).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="⊘ Fără Badge", command=self.on_skip).pack(side=tk.LEFT, padx=4)

    def _delayed_preview(self):
        """Apelează update_preview după ce fereastra e afișată (evită grayout pe unele sisteme)."""
        self.window.update_idletasks()
        self._apply_last_confirmed_if_first()
        self.update_preview()

    def _get_preset_for_current_brand(self):
        """Returnează presetul salvat pentru brandul curent (din combobox)."""
        brand = (self.brand_var.get() or '').strip() or '_fara_brand'
        return self._presets_by_brand.get(brand)

    def _apply_last_confirmed_if_first(self):
        """La prima afișare: aplică presetul pentru brandul curent dacă există; altfel ultima confirmare globală."""
        if getattr(self, '_style_applied', False):
            return
        self._style_applied = True
        preset = self._get_preset_for_current_brand()
        if preset:
            data = preset.get('data') or {}
            style = preset.get('style') or {}
            self.apply_badges_var.set(preset.get('apply_badges', True))
            self.brand_var.set(data.get('brand', '') or '')
            self.model_var.set(data.get('model', '') or '')
            self.tech_var.set(data.get('tehnologie', '') or '')
            self.hz_text_var.set(data.get('hz_text') or '')
            self.ic_var.set(data.get('ic_transferabil', False))
            self.tt_var.set(data.get('truetone', False))
            self._apply_style_dict(style)
            self.update_preview()
            return
        if not self._last_confirmed:
            return
        style = self._last_confirmed.get('style') or {}
        self.apply_badges_var.set(self._last_confirmed.get('apply_badges', True))
        self._apply_style_dict(style)

    def _apply_style_dict(self, style):
        """Aplică un dict style la toate variabilele de aspect."""
        if not style:
            return
        self.brand_bg_var.set(style.get('brand_bg') or '')
        self.brand_pos_var.set(style.get('brand_pos', 'top_left'))
        self.brand_shape_var.set(style.get('brand_shape', 'rounded'))
        self.brand_font_var.set(str(style.get('brand_font_size', 42)))
        self.brand_padding_var.set(str(style.get('brand_padding', 14)))
        self.brand_offset_x_var.set(str(style.get('brand_offset_x', 0)))
        self.brand_offset_y_var.set(str(style.get('brand_offset_y', 0)))
        self.brand_x_var.set('' if 'brand_x' not in style else str(style['brand_x']))
        self.brand_y_var.set('' if 'brand_y' not in style else str(style['brand_y']))
        self.model_bg_var.set(style.get('model_bg') or '')
        self.model_pos_var.set(style.get('model_pos', 'center'))
        self.model_vertical_var.set(style.get('model_vertical', False))
        self.model_font_var.set(str(style.get('model_font_size', 34)))
        self.model_padding_var.set(str(style.get('model_padding', 18)))
        self.model_offset_x_var.set(str(style.get('model_offset_x', 0)))
        self.model_offset_y_var.set(str(style.get('model_offset_y', 0)))
        self.model_x_var.set('' if 'model_x' not in style else str(style['model_x']))
        self.model_y_var.set('' if 'model_y' not in style else str(style['model_y']))
        self.badges_bg_var.set(style.get('badges_bg') or '')
        self.badges_pos_var.set(style.get('badges_pos', 'bottom_center'))
        self.badges_vertical_var.set(style.get('badges_vertical', False))
        self.badges_font_var.set(str(style.get('badges_font_size', 24)))
        self.badges_padding_var.set(str(style.get('badges_padding', 14)))
        self.badges_spacing_var.set(str(style.get('badges_spacing', 10)))
        self.badges_offset_x_var.set(str(style.get('badges_offset_x', 0)))
        self.badges_offset_y_var.set(str(style.get('badges_offset_y', 0)))
        self.badges_x_var.set('' if 'badges_x' not in style else str(style['badges_x']))
        self.badges_y_var.set('' if 'badges_y' not in style else str(style['badges_y']))
        self.bottom_margin_var.set(str(style.get('bottom_margin', 24)))
        self.margin_var.set(str(style.get('margin', 20)))
        if 'custom_badges' in style and isinstance(style['custom_badges'], list):
            self.custom_badges_list = list(style['custom_badges'])
            self._refresh_custom_badges_listbox()

    def _reset_to_brand_preset(self):
        """Resetează la ultima setare salvată pentru brandul curent (preset per brand)."""
        preset = self._get_preset_for_current_brand()
        if not preset:
            messagebox.showinfo("Reset", "Nu există setare salvată pentru acest brand. Confirmă sau Batch pentru a salva presetul la acest brand.")
            return
        data = preset.get('data') or {}
        style = preset.get('style') or {}
        self.apply_badges_var.set(preset.get('apply_badges', True))
        self.brand_var.set(data.get('brand', '') or '')
        self.model_var.set(data.get('model', '') or '')
        self.tech_var.set(data.get('tehnologie', '') or '')
        self.hz_text_var.set(data.get('hz_text') or '')
        self.ic_var.set(data.get('ic_transferabil', False))
        self.tt_var.set(data.get('truetone', False))
        self._apply_style_dict(style)
        self.update_preview()

    def _reset_to_last_confirmed(self):
        """Resetează la ultima confirmare globală (folosește Reset (brand) pentru preset per brand)."""
        if not self._last_confirmed:
            messagebox.showinfo("Reset", "Nu există o confirmare salvată. Confirmă o dată pentru a putea folosi Reset.")
            return
        data = self._last_confirmed.get('data') or {}
        style = self._last_confirmed.get('style') or {}
        self.apply_badges_var.set(self._last_confirmed.get('apply_badges', True))
        self.brand_var.set(data.get('brand', '') or '')
        self.model_var.set(data.get('model', '') or '')
        self.tech_var.set(data.get('tehnologie', '') or '')
        self.hz_text_var.set(data.get('hz_text') or '')
        self.ic_var.set(data.get('ic_transferabil', False))
        self.tt_var.set(data.get('truetone', False))
        self._apply_style_dict(style)
        self.update_preview()

    def _save_current_brand(self):
        b = (self.brand_var.get() or '').strip()
        if b:
            save_custom_brand(self.script_dir, b)
            vals = list(self.brand_combo['values'])
            if b not in vals:
                self.brand_combo['values'] = vals + [b]

    def _save_current_model(self):
        m = (self.model_var.get() or '').strip()
        if m:
            save_line_to_file(self.script_dir, Path(BADGE_CUSTOM_MODELS_FILE).name, m)
            vals = list(self.model_combo['values'])
            if m not in vals:
                self.model_combo['values'] = vals + [m]

    def _save_current_tech(self):
        t = (self.tech_var.get() or '').strip()
        if t:
            save_line_to_file(self.script_dir, Path(BADGE_CUSTOM_TECH_FILE).name, t)
            vals = list(self.tech_combo['values'])
            if t not in vals:
                self.tech_combo['values'] = vals + [t]

    def _refresh_custom_badges_listbox(self):
        if getattr(self, '_custom_badges_listbox_var', None) is None:
            return
        lines = []
        for i in self.custom_badges_list:
            t = i.get('type', 'text')
            if t == 'image':
                lines.append(f"img @ ({i.get('x',0)},{i.get('y',0)}) {i.get('path','')[:20]}")
            else:
                lines.append(f"txt @ ({i.get('x',0)},{i.get('y',0)}) {(i.get('text') or i.get('emoji') or '')[:20]}")
        self._custom_badges_listbox_var.set(lines)

    def _add_custom_text_badge(self):
        d = {'type': 'text', 'text': '✓', 'x': 50, 'y': 50, 'scale': 1.0, 'vertical': False, 'font_size': 24}
        self.custom_badges_list.append(d)
        self._refresh_custom_badges_listbox()
        self.update_preview()

    def _add_custom_image_badge(self):
        path = filedialog.askopenfilename(title="Alege imagine (PNG cu transparență)", filetypes=[("PNG", "*.png"), ("Toate", "*.*")])
        if path:
            rel = Path(path)
            try:
                rel = rel.relative_to(Path(self.script_dir))
            except ValueError:
                rel = Path(path).name
            d = {'type': 'image', 'path': str(rel), 'x': 50, 'y': 50, 'scale': 1.0}
            self.custom_badges_list.append(d)
            self._refresh_custom_badges_listbox()
            self.update_preview()

    def _remove_custom_badge(self):
        lb = getattr(self, '_custom_badges_listbox', None)
        if not lb or not self.custom_badges_list:
            return
        sel = lb.curselection()
        if sel:
            idx = int(sel[0])
            self.custom_badges_list.pop(idx)
            self._refresh_custom_badges_listbox()
            self.update_preview()

    def _load_custom_badges_file(self):
        path = _badge_data_dir(self.script_dir) / Path(BADGE_CUSTOM_LIST_FILE).name
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.custom_badges_list = data if isinstance(data, list) else data.get('badges', [])
            except Exception:
                self.custom_badges_list = []
        else:
            path = filedialog.askopenfilename(title="Încarcă listă badge-uri", filetypes=[("JSON", "*.json"), ("Toate", "*.*")])
            if path:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.custom_badges_list = data if isinstance(data, list) else data.get('badges', [])
                except Exception:
                    pass
        self._refresh_custom_badges_listbox()
        self.update_preview()

    def _save_custom_badges_file(self):
        path = _badge_data_dir(self.script_dir) / Path(BADGE_CUSTOM_LIST_FILE).name
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.custom_badges_list, f, indent=2)
        except Exception:
            pass
        self._refresh_custom_badges_listbox()

    def get_current_style(self):
        def _int(v, default):
            try:
                return int(v.get() if hasattr(v, 'get') else v)
            except (ValueError, TypeError):
                return default
        def _opt_int(v, default=None):
            s = (v.get() if hasattr(v, 'get') else v) or ''
            s = str(s).strip()
            if not s:
                return default
            try:
                return int(s)
            except (ValueError, TypeError):
                return default

        style = {
            'brand_bg': (self.brand_bg_var.get() or '').strip() or None,
            'brand_pos': (self.brand_pos_var.get() or 'top_left').strip(),
            'brand_shape': (self.brand_shape_var.get() or 'rounded').strip(),
            'brand_font_size': _int(self.brand_font_var, 42),
            'brand_padding': _int(self.brand_padding_var, 14),
            'brand_offset_x': _int(self.brand_offset_x_var, 0),
            'brand_offset_y': _int(self.brand_offset_y_var, 0),
            'model_pos': (self.model_pos_var.get() or 'center').strip(),
            'model_vertical': self.model_vertical_var.get(),
            'model_bg': (self.model_bg_var.get() or '').strip() or None,
            'model_font_size': _int(self.model_font_var, 34),
            'model_padding': _int(self.model_padding_var, 18),
            'model_offset_x': _int(self.model_offset_x_var, 0),
            'model_offset_y': _int(self.model_offset_y_var, 0),
            'badges_pos': (self.badges_pos_var.get() or 'bottom_center').strip(),
            'badges_vertical': self.badges_vertical_var.get(),
            'badges_bg': (self.badges_bg_var.get() or '').strip() or None,
            'badges_font_size': _int(self.badges_font_var, 24),
            'badges_padding': _int(self.badges_padding_var, 14),
            'badges_spacing': _int(self.badges_spacing_var, 10),
            'badges_offset_x': _int(self.badges_offset_x_var, 0),
            'badges_offset_y': _int(self.badges_offset_y_var, 0),
            'bottom_margin': _int(self.bottom_margin_var, 24),
            'margin': _int(self.margin_var, 20),
        }
        bx = _opt_int(self.brand_x_var)
        if bx is not None:
            style['brand_x'] = bx
        by = _opt_int(self.brand_y_var)
        if by is not None:
            style['brand_y'] = by
        mx = _opt_int(self.model_x_var)
        if mx is not None:
            style['model_x'] = mx
        my = _opt_int(self.model_y_var)
        if my is not None:
            style['model_y'] = my
        bbx = _opt_int(self.badges_x_var)
        if bbx is not None:
            style['badges_x'] = bbx
        bby = _opt_int(self.badges_y_var)
        if bby is not None:
            style['badges_y'] = bby
        style['custom_badges'] = getattr(self, 'custom_badges_list', [])
        return style

    def get_current_badge_data(self):
        hz_t = (self.hz_text_var.get() or '').strip()
        data = {
            'brand': (self.brand_var.get() or '').strip() or None,
            'model': (self.model_var.get() or '').strip() or None,
            'tehnologie': (self.tech_var.get() or '').strip() or None,
            'hz_120': bool(hz_t),
            'hz_text': hz_t or None,
            'ic_transferabil': self.ic_var.get(),
            'truetone': self.tt_var.get(),
        }
        data['_style'] = self.get_current_style()
        return data

    def update_preview(self):
        img_path = getattr(self, 'image_path', None)
        if not img_path or not Path(img_path).exists():
            self.preview_label.configure(image='', text='Imagine indisponibilă.\nVerifică calea: ' + str(img_path or ''))
            return
        apply_badges = getattr(self, 'apply_badges_var', None) and self.apply_badges_var.get()
        try:
            if not apply_badges:
                preview_img = Image.open(img_path).convert('RGB')
            else:
                badge_data = self.get_current_badge_data()
                style = badge_data.pop('_style', None)
                preview_img = generate_badge_preview(img_path, badge_data, style=style, script_dir=getattr(self, 'script_dir', None))
            if preview_img is None:
                return
            preview_img = preview_img.copy()
            preview_img.thumbnail((500, 500), Image.Resampling.LANCZOS)
            if preview_img.mode == 'RGBA':
                preview_img = preview_img.convert('RGB')
            self.photo = ImageTk.PhotoImage(preview_img)
            self.preview_label.configure(image=self.photo, text='')
        except Exception as e:
            self.preview_label.configure(image='', text=f'Eroare preview:\n{e}')

    def on_confirm(self):
        apply_badges = self.apply_badges_var.get()
        d = self.get_current_badge_data()
        d.pop('_style', None)
        style = self.get_current_style()
        save_badge_last_confirmed(self.script_dir, d, style, apply_badges=apply_badges)
        brand_key = (d.get('brand') or '').strip()
        if brand_key:
            save_badge_preset_for_brand(self.script_dir, brand_key, d, style, apply_badges=apply_badges)
            self._presets_by_brand = load_badge_presets_by_brand(self.script_dir)
        self.callback('confirm', {'data': d, 'style': style, 'apply_badges': apply_badges})
        self.window.destroy()

    def on_batch(self):
        apply_badges = self.apply_badges_var.get()
        d = self.get_current_badge_data()
        d.pop('_style', None)
        style = self.get_current_style()
        brand_key = (d.get('brand') or '').strip()
        if brand_key:
            save_badge_preset_for_brand(self.script_dir, brand_key, d, style, apply_badges=apply_badges)
            self._presets_by_brand = load_badge_presets_by_brand(self.script_dir)
        self.callback('batch', {'data': d, 'style': style, 'apply_badges': apply_badges})
        self.window.destroy()

    def on_skip_image(self):
        self.callback('skip_image', None)
        self.window.destroy()

    def on_skip(self):
        self.callback('skip', None)
        self.window.destroy()


class ImportProduse:
    def __init__(self, root):
        self.root = root
        self.root.title("Export Produse MobileSentrix → CSV (cu Imagini)")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Variabile – .env din același folder cu scriptul (nu din cwd), ca pe Windows să fie găsit mereu
        self._script_dir = Path(__file__).resolve().parent
        self.env_file = self._script_dir / ".env"
        self.config = {}
        self.running = False
        
        # Creare directoare (în folderul scriptului)
        (self._script_dir / "logs").mkdir(exist_ok=True)
        (self._script_dir / "images").mkdir(exist_ok=True)
        (self._script_dir / "data").mkdir(exist_ok=True)
        
        # Load config
        self.load_config()
        
        # Load category rules (keyword → category path)
        self.category_rules = self.load_category_rules()
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Creează interfața grafică"""
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Export CSV
        tab_import = ttk.Frame(notebook)
        notebook.add(tab_import, text='📦 Export CSV')
        
        # Tab 2: Configurare
        tab_config = ttk.Frame(notebook)
        notebook.add(tab_config, text='⚙ Configurare')
        
        # Tab 3: Log
        tab_log = ttk.Frame(notebook)
        notebook.add(tab_log, text='📋 Log')
        
        self.setup_import_tab(tab_import)
        self.setup_config_tab(tab_config)
        self.setup_log_tab(tab_log)
        
    def setup_import_tab(self, parent):
        """Setup tab Import"""
        
        # Frame SKU/LINK
        frame_sku = ttk.LabelFrame(parent, text="Selectează fișier cu link-uri sau EAN-uri", padding=10)
        frame_sku.pack(fill='x', padx=10, pady=10)
        
        # Info box despre modul CSV
        info_frame = ttk.Frame(frame_sku)
        info_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 10))
        info_label = ttk.Label(info_frame, text="ℹ️ MOD CSV: Pune link-uri directe din MobileSentrix în sku_list.txt (ex: https://www.mobilesentrix.eu/product-name/) SAU EAN-uri. Program extrage: Nume, Preț EUR/RON, Descriere, Pozele MARI + cont. CSV cu tot.", 
                              foreground="blue", wraplength=800)
        info_label.pack(anchor='w')
        
        self.sku_file_var = tk.StringVar(value="sku_list.txt")
        
        ttk.Label(frame_sku, text="Fișier:").grid(row=1, column=0, sticky='w', padx=5)
        ttk.Entry(frame_sku, textvariable=self.sku_file_var, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(frame_sku, text="Răsfoire...", command=self.browse_sku_file).grid(row=1, column=2, padx=5)
        
        # Opțiuni import
        frame_options = ttk.LabelFrame(parent, text="Opțiuni Import", padding=10)
        frame_options.pack(fill='x', padx=10, pady=10)
        
        self.download_images_var = tk.BooleanVar(value=True)
        self.optimize_images_var = tk.BooleanVar(value=False)  # ❌ DEZACTIVAT - descarcă pozele MARI
        self.convert_price_var = tk.BooleanVar(value=True)
        self.extract_description_var = tk.BooleanVar(value=True)
        self.badge_preview_var = tk.BooleanVar(value=False)
        
        # Text roșu de avertizare – vizibil doar când bifa de badge e activată
        self._badge_warning_label = tk.Label(
            frame_options,
            text="⚠️ Mod badge-uri activ: la fiecare produs cu imagini se deschide fereastra de preview badge (poți confirma, modifica sau sări peste poză).",
            fg='#c00',
            wraplength=750,
            font=('', 10),
            justify=tk.LEFT
        )
        def _toggle_badge_warning(*args):
            if self.badge_preview_var.get():
                self._badge_warning_label.grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=(0, 8))
            else:
                self._badge_warning_label.grid_remove()
        self.badge_preview_var.trace_add('write', _toggle_badge_warning)
        
        ttk.Checkbutton(frame_options, text="Descarcă toate imaginile produsului", 
                       variable=self.download_images_var).grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Optimizează imaginile (resize)", 
                       variable=self.optimize_images_var).grid(row=2, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Adaugă badge-uri pe produse (opțional – la fiecare produs parcurgi preview badge)", 
                       variable=self.badge_preview_var, command=lambda: _toggle_badge_warning()).grid(row=3, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Convertește prețul EUR → RON", 
                       variable=self.convert_price_var).grid(row=4, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Extrage descriere în română", 
                       variable=self.extract_description_var).grid(row=5, column=0, sticky='w', padx=5, pady=2)
        
        # Progress
        frame_progress = ttk.Frame(parent)
        frame_progress.pack(fill='x', padx=10, pady=10)
        
        self.progress_var = tk.StringVar(value="Pregătit pentru export CSV")
        ttk.Label(frame_progress, textvariable=self.progress_var).pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(frame_progress, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=5)
        
        # Butoane
        frame_buttons = ttk.Frame(parent)
        frame_buttons.pack(fill='x', padx=10, pady=10)
        
        self.btn_start = ttk.Button(frame_buttons, text="🚀 START EXPORT CSV", 
                                     command=self.start_import, style='Accent.TButton')
        self.btn_start.pack(side='left', padx=5)
        
        self.btn_stop = ttk.Button(frame_buttons, text="⛔ STOP", 
                                    command=self.stop_import, state='disabled')
        self.btn_stop.pack(side='left', padx=5)
        
        ttk.Button(frame_buttons, text="📄 Deschide sku_list.txt", 
                  command=lambda: os.startfile("sku_list.txt")).pack(side='right', padx=5)
        
    def setup_config_tab(self, parent):
        """Setup tab Configurare"""
        
        frame = ttk.LabelFrame(parent, text="Configurare WooCommerce API", padding=20)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # WooCommerce URL
        ttk.Label(frame, text="URL WooCommerce:").grid(row=0, column=0, sticky='w', pady=10)
        self.wc_url_var = tk.StringVar(value=self.config.get('WOOCOMMERCE_URL', 'https://webgsm.ro'))
        ttk.Entry(frame, textvariable=self.wc_url_var, width=50).grid(row=0, column=1, pady=10, padx=10)
        
        # Consumer Key
        ttk.Label(frame, text="Consumer Key:").grid(row=1, column=0, sticky='w', pady=10)
        self.wc_key_var = tk.StringVar(value=self.config.get('WOOCOMMERCE_CONSUMER_KEY', ''))
        ttk.Entry(frame, textvariable=self.wc_key_var, width=50, show='*').grid(row=1, column=1, pady=10, padx=10)
        
        # Consumer Secret
        ttk.Label(frame, text="Consumer Secret:").grid(row=2, column=0, sticky='w', pady=10)
        self.wc_secret_var = tk.StringVar(value=self.config.get('WOOCOMMERCE_CONSUMER_SECRET', ''))
        ttk.Entry(frame, textvariable=self.wc_secret_var, width=50, show='*').grid(row=2, column=1, pady=10, padx=10)
        
        # Curs EUR/RON
        ttk.Label(frame, text="Curs EUR → RON:").grid(row=3, column=0, sticky='w', pady=10)
        self.exchange_rate_var = tk.StringVar(value=self.config.get('EXCHANGE_RATE', '4.97'))
        ttk.Entry(frame, textvariable=self.exchange_rate_var, width=20).grid(row=3, column=1, sticky='w', pady=10, padx=10)
        
        # Butoane
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="💾 Salvează Configurare", 
                  command=self.save_config).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔍 Test Conexiune", 
                  command=self.test_connection).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔄 Reîncarcă Config", 
                  command=self.reload_config).pack(side='left', padx=5)
        
        # Info box
        info_frame = ttk.LabelFrame(frame, text="ℹ️ Informații", padding=10)
        info_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky='ew')
        
        info_text = """
📍 Cum obții API Keys:
   1. WordPress Admin → WooCommerce → Settings
   2. Tab "Advanced" → Sub-tab "REST API"
   3. Click "Add key"
   4. Description: "Import Produse"
   5. Permissions: "Read/Write"
   6. Generate și copiază Consumer Key și Secret

⚠️ URL fără / la final: https://webgsm.ro (corect)
        """
        ttk.Label(info_frame, text=info_text.strip(), justify='left', 
                 font=('Consolas', 8)).pack(anchor='w')
        
    def setup_log_tab(self, parent):
        """Setup tab Log"""
        
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, 
                                                   font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Butoane
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="🗑 Șterge Log", 
                  command=lambda: self.log_text.delete(1.0, tk.END)).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="📁 Deschide Folder Logs", 
                  command=lambda: os.startfile(str(self._script_dir / "logs"))).pack(side='left', padx=5)
        
    def log(self, message, level='INFO'):
        """Adaugă mesaj în log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update()
    
    def cleanup_orphans(self):
        """Curăță produse orfane din WooCommerce (înainte de import)"""
        try:
            self.log("=" * 70, "INFO")
            self.log("🧹 CURĂȚARE ORFANE - Găsire și ștergere produse incomplete", "INFO")
            self.log("=" * 70, "INFO")
            
            if not self.wc_api:
                # Inițializează API
                self.wc_api = API(
                    url=self.config['WOOCOMMERCE_URL'],
                    consumer_key=self.config['WOOCOMMERCE_CONSUMER_KEY'],
                    consumer_secret=self.config['WOOCOMMERCE_CONSUMER_SECRET'],
                    version="wc/v3",
                    timeout=30
                )
            
            # Caută TOATE produsele (cu pagina mare)
            self.log("📊 Descarcă lista completă de produse din WooCommerce...", "INFO")
            all_products = []
            page = 1
            per_page = 100
            max_pages = 50  # Safety limit
            
            while page <= max_pages:
                try:
                    response = self.wc_api.get("products", params={"page": page, "per_page": per_page, "status": "any"})
                    
                    if response.status_code != 200:
                        self.log(f"⚠️ Status {response.status_code} la pagina {page} - Opresc descărcarea", "WARNING")
                        break
                    
                    products = response.json()
                    if not products or len(products) == 0:
                        self.log(f"  📖 Pagina {page}: 0 produse - Am ajuns la final", "INFO")
                        break
                    
                    all_products.extend(products)
                    self.log(f"  📖 Pagina {page}: {len(products)} produse", "INFO")
                    page += 1
                    
                except Exception as page_error:
                    self.log(f"⚠️ Eroare la pagina {page}: {page_error}", "WARNING")
                    break
            
            if len(all_products) == 0:
                self.log("⚠️ API-ul returnează 0 produse! Posibil probleme cu API sau autentificare.", "WARNING")
                self.log("🔍 Voi incerca să identific orfane prin alt metod...", "INFO")
                
                # Fallback: Încearcă o cerere simplă
                try:
                    simple_response = self.wc_api.get("products")
                    simple_products = simple_response.json()
                    if simple_products and len(simple_products) > 0:
                        all_products = simple_products
                        self.log(f"✓ Am găsit {len(all_products)} produse cu metoda alternativă", "INFO")
                except:
                    pass
            
            # Dacă inca nu au produse, încearcă fără parametri
            if len(all_products) == 0:
                self.log("⚠️ Curățare orfane nu a putut descărca produse. Continuez importul...", "WARNING")
                self.log("💡 Dacă apare 'Duplicate entry', programul va curăța automat.", "INFO")
                return
            
            self.log(f"✓ Total descărcat: {len(all_products)} produse", "INFO")
            
            # Identifică produse problematice (fără SKU valid sau cu meta_data incompletă)
            orphans_to_delete = []
            
            for prod in all_products:
                product_id = prod.get('id')
                product_sku = prod.get('sku', '')
                product_status = prod.get('status', '')
                product_name = prod.get('name', 'N/A')
                
                # Verifică dacă e produs incomplet:
                has_ean = any(m.get('key') == '_ean' for m in prod.get('meta_data', []))
                
                if product_sku.startswith('WEBGSM-') and (product_status in ['trash', 'draft'] or not has_ean):
                    orphans_to_delete.append({
                        'id': product_id,
                        'sku': product_sku,
                        'status': product_status,
                        'name': product_name
                    })
            
            if not orphans_to_delete:
                self.log("✅ Nu sunt orfane! Baza de date e curată.", "SUCCESS")
                return
            
            self.log(f"⚠️ Găsite {len(orphans_to_delete)} produse incomplete/orfane:", "WARNING")
            
            for orphan in orphans_to_delete:
                self.log(f"   ID: {orphan['id']} | SKU: {orphan['sku']} | Status: {orphan['status']}", "WARNING")
            
            # Șterge orfanele
            deleted_count = 0
            for orphan in orphans_to_delete:
                try:
                    response = self.wc_api.delete(f"products/{orphan['id']}", params={"force": True})
                    if response.status_code in [200, 204]:
                        deleted_count += 1
                        self.log(f"   ✓ Șters ID {orphan['id']}", "SUCCESS")
                    else:
                        self.log(f"   ✗ Nu s-a putut șterge ID {orphan['id']} (status {response.status_code})", "ERROR")
                except Exception as e:
                    self.log(f"   ✗ Eroare la ștergere ID {orphan['id']}: {e}", "ERROR")
            
            self.log(f"🧹 Curățare completă: {deleted_count}/{len(orphans_to_delete)} orfane șterse", "INFO")
            self.log("=" * 70, "INFO")
            
        except Exception as e:
            self.log(f"❌ Eroare curățare: {e}", "ERROR")
    
    def load_config(self):
        """Încarcă configurația din .env"""
        # Setări default
        self.config = {
            'WOOCOMMERCE_URL': 'https://webgsm.ro',
            'WOOCOMMERCE_CONSUMER_KEY': '',
            'WOOCOMMERCE_CONSUMER_SECRET': '',
            'EXCHANGE_RATE': '4.97',
            'OLLAMA_URL': '',
            'OLLAMA_MODEL': 'llama3.2',
            'OLLAMA_TIMEOUT': 300
        }
        
        # Încarcă din .env dacă există
        if self.env_file.exists():
            try:
                load_dotenv(self.env_file)
                _ollama_timeout = os.getenv('OLLAMA_TIMEOUT', '300').strip()
                try:
                    _ollama_timeout = int(_ollama_timeout)
                except ValueError:
                    _ollama_timeout = 300
                self.config = {
                    'WOOCOMMERCE_URL': os.getenv('WOOCOMMERCE_URL', 'https://webgsm.ro'),
                    'WOOCOMMERCE_CONSUMER_KEY': os.getenv('WOOCOMMERCE_CONSUMER_KEY', ''),
                    'WOOCOMMERCE_CONSUMER_SECRET': os.getenv('WOOCOMMERCE_CONSUMER_SECRET', ''),
                    'EXCHANGE_RATE': os.getenv('EXCHANGE_RATE', '4.97'),
                    'OLLAMA_URL': os.getenv('OLLAMA_URL', '').strip(),
                    'OLLAMA_MODEL': os.getenv('OLLAMA_MODEL', 'llama3.2').strip() or 'llama3.2',
                    'OLLAMA_TIMEOUT': max(120, min(_ollama_timeout, 600))
                }
                print(f"✓ Config încărcat din .env: {self.config}")
            except Exception as e:
                print(f"✗ Eroare la încărcarea config: {e}")
        else:
            print("ℹ Fișierul .env nu există, folosim valori default")
        # Debug: arată dacă Ollama e configurat (pentru loguri pe Windows)
        self._ollama_local_checked = None
        self._ollama_local_url = None
        ollama_url = self.config.get('OLLAMA_URL', '')
        if ollama_url:
            print(f"✓ Ollama din .env: {ollama_url}")
        else:
            print("ℹ OLLAMA_URL gol în .env – se va încerca Ollama pe local (localhost:11434) dacă rulează")
        
    def save_config(self):
        """Salvează configurația în .env"""
        try:
            # Validare date
            url = self.wc_url_var.get().strip()
            key = self.wc_key_var.get().strip()
            secret = self.wc_secret_var.get().strip()
            rate = self.exchange_rate_var.get().strip()
            
            if not url:
                messagebox.showwarning("Atenție", "URL-ul WooCommerce este obligatoriu!")
                return
            
            if not key or not secret:
                messagebox.showwarning("Atenție", "Consumer Key și Secret sunt obligatorii!")
                return
            
            # Verifică URL (elimină / de la final dacă există)
            if url.endswith('/'):
                url = url[:-1]
                self.wc_url_var.set(url)
            
            # Validare curs valutar
            try:
                float(rate)
            except ValueError:
                messagebox.showwarning("Atenție", "Cursul valutar trebuie să fie un număr valid!")
                return
            
            # Crează sau actualizează .env (păstrăm OLLAMA_* ca să nu se piardă la Salvează Config)
            ollama_url = self.config.get('OLLAMA_URL', '')
            ollama_model = self.config.get('OLLAMA_MODEL', 'llama3.1:latest') or 'llama3.1:latest'
            ollama_timeout = self.config.get('OLLAMA_TIMEOUT', 300)
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(f"WOOCOMMERCE_URL={url}\n")
                f.write(f"WOOCOMMERCE_CONSUMER_KEY={key}\n")
                f.write(f"WOOCOMMERCE_CONSUMER_SECRET={secret}\n")
                f.write(f"EXCHANGE_RATE={rate}\n")
                f.write("\n# Ollama (traducere nume slug / Componentă)\n")
                f.write(f"OLLAMA_URL={ollama_url}\n")
                f.write(f"OLLAMA_MODEL={ollama_model}\n")
                f.write(f"OLLAMA_TIMEOUT={ollama_timeout}\n")
            
            # Actualizează config intern
            self.config = {
                'WOOCOMMERCE_URL': url,
                'WOOCOMMERCE_CONSUMER_KEY': key,
                'WOOCOMMERCE_CONSUMER_SECRET': secret,
                'EXCHANGE_RATE': rate,
                'OLLAMA_URL': ollama_url,
                'OLLAMA_MODEL': ollama_model,
                'OLLAMA_TIMEOUT': ollama_timeout
            }
            
            # Resetează API pentru a folosi noile credențiale
            self.wc_api = None
            
            self.log("✓ Configurație salvată cu succes!", "SUCCESS")
            self.log(f"   URL: {url}", "INFO")
            self.log(f"   Curs: {rate} RON/EUR", "INFO")
            messagebox.showinfo("Succes", "Configurația a fost salvată!\n\nPoți testa conexiunea acum.")
            
        except Exception as e:
            self.log(f"✗ Eroare salvare configurație: {e}", "ERROR")
            import traceback
            self.log(f"   Traceback: {traceback.format_exc()}", "ERROR")
            messagebox.showerror("Eroare", f"Nu s-a putut salva configurația:\n{e}")
    
    def reload_config(self):
        """Reîncarcă configurația din .env"""
        try:
            self.load_config()
            
            # Actualizează câmpurile GUI
            self.wc_url_var.set(self.config.get('WOOCOMMERCE_URL', 'https://webgsm.ro'))
            self.wc_key_var.set(self.config.get('WOOCOMMERCE_CONSUMER_KEY', ''))
            self.wc_secret_var.set(self.config.get('WOOCOMMERCE_CONSUMER_SECRET', ''))
            self.exchange_rate_var.set(self.config.get('EXCHANGE_RATE', '4.97'))
            
            self.log("🔄 Configurație reîncărcată din .env", "INFO")
            messagebox.showinfo("Succes", "Configurația a fost reîncărcată din fișier!")
            
        except Exception as e:
            self.log(f"✗ Eroare reîncarcare config: {e}", "ERROR")
            messagebox.showerror("Eroare", f"Nu s-a putut reîncărca configurația:\n{e}")

    def calculate_selling_price(self, price_eur, exchange_rate=5.0, markup=0.40, vat=0.19):
        """
        Calculează prețul de vânzare B2C cu TVA.

        Args:
            price_eur: Preț achiziție în EUR (fără TVA)
            exchange_rate: Curs EUR/RON (default 5.0)
            markup: Adaos comercial (default 40% = 0.40)
            vat: TVA (default 19% = 0.19)

        Returns:
            Preț de vânzare în RON cu TVA inclus
        """
        price_ron = price_eur * exchange_rate
        price_with_markup = price_ron * (1 + markup)
        final_price = price_with_markup * (1 + vat)
        return round(final_price, 2)

    def detect_availability(self, soup, page_text):
        """
        Detectează dacă produsul e în stoc, preorder sau out of stock.

        Returns:
            'in_stock' | 'preorder' | 'out_of_stock'
        """
        text_lower = (page_text or '').lower()
        if hasattr(soup, 'get_text'):
            text_lower = (soup.get_text() + ' ' + text_lower).lower()

        preorder_indicators = [
            'pre-order', 'preorder', 'pre order', 'coming soon',
            'available for pre-order', 'expected to ship', 'estimated arrival', 'backorder'
        ]
        for indicator in preorder_indicators:
            if indicator in text_lower:
                return 'preorder'

        oos_indicators = [
            'out of stock', 'sold out', 'currently unavailable', 'not available'
        ]
        for indicator in oos_indicators:
            if indicator in text_lower:
                return 'out_of_stock'

        return 'in_stock'

    def generate_unique_sku(self, ean):
        """LEGACY - păstrat pentru compatibilitate. Folosește generate_webgsm_sku() pentru SKU-uri noi."""
        ean_int = int(ean) if ean.isdigit() else int(''.join(c for c in ean if c.isdigit()))
        sequential_id = (ean_int % 100000)
        sku = f"890{sequential_id:05d}00000"
        return sku

    def generate_webgsm_sku(self, product_name, brand_piesa, counter, calitate=None, manual_code=None):
        """
        Generează SKU unic format: WG-{TIP}-{MODEL}-{BRAND}-{ID}
        Exemple: WG-BAT-IP17-PULL-01, WG-CP-IP17-OEM-01, WG-ECR-IP13-JK-01
        Dacă manual_code este setat (din sku_list: link | COD), prefixul vine din CATEGORY_CODE_MAP.
        """
        type_code = None
        if manual_code and isinstance(manual_code, str):
            manual_code = manual_code.strip().upper()
            if manual_code in CATEGORY_CODE_MAP:
                type_code = CATEGORY_CODE_MAP[manual_code].get('prefix', manual_code)

        if type_code is None:
            # CODURI TIP PIESA - ORDINEA CONTEAZĂ (cele mai specifice primele)
            type_map = {
            'ECR': ['display', 'screen', 'oled', 'lcd', 'digitizer', 'ecran'],
            'BAT': ['battery', 'baterie', 'acumulator'],
            'CP': ['charging port'],  # Conector Încărcare
            'CAM': ['camera', 'lens'],
            'CRC': ['housing', 'back glass', 'frame', 'back cover', 'rear glass', 'carcasa'],
            'DIF': ['speaker', 'earpiece', 'buzzer', 'difuzor'],
            'BTN': ['button', 'power button', 'volume', 'buton'],
            'SNZ': ['sensor', 'proximity', 'face id'],
            'TAP': ['taptic', 'vibrator', 'motor'],
            'SIM': ['sim tray', 'sim card'],
            'ANT': ['antenna', 'wifi', 'gps'],
            'FOL': ['folie', 'tempered', 'screen protector'],
            'FLX': ['flex', 'cable', 'connector', 'dock'],
            'ACC': ['screwdriver', 'electric screwdriver', 'șurubelniță', 'unealtă', 'tester', 'diagnostic', 'test tool', 'analysis tester'],
        }

        name_lower = product_name.lower()

        if type_code is None:
            # Detectează tipul piesei
            type_code = 'PIS'  # default = Piesă
            for code, keywords in type_map.items():
                if any(kw in name_lower for kw in keywords):
                    type_code = code
                    break

        # CODURI MODEL TELEFON
        model_map = {
            'iphone 17 pro max': 'IP17PM',
            'iphone 17 pro': 'IP17P',
            'iphone 17 plus': 'IP17PL',
            'iphone 17 air': 'IP17A',
            'iphone 17': 'IP17',
            'iphone 16 pro max': 'IP16PM',
            'iphone 16 pro': 'IP16P',
            'iphone 16 plus': 'IP16PL',
            'iphone 16': 'IP16',
            'iphone 15 pro max': 'IP15PM',
            'iphone 15 pro': 'IP15P',
            'iphone 15 plus': 'IP15PL',
            'iphone 15': 'IP15',
            'iphone 14 pro max': 'IP14PM',
            'iphone 14 pro': 'IP14P',
            'iphone 14 plus': 'IP14PL',
            'iphone 14': 'IP14',
            'iphone 13 pro max': 'IP13PM',
            'iphone 13 pro': 'IP13P',
            'iphone 13 mini': 'IP13M',
            'iphone 13': 'IP13',
            'iphone 12 pro max': 'IP12PM',
            'iphone 12 pro': 'IP12P',
            'iphone 12 mini': 'IP12M',
            'iphone 12': 'IP12',
            'iphone 11 pro max': 'IP11PM',
            'iphone 11 pro': 'IP11P',
            'iphone 11': 'IP11',
            'iphone xs max': 'IPXSM',
            'iphone xs': 'IPXS',
            'iphone xr': 'IPXR',
            'iphone x': 'IPX',
            'iphone se': 'IPSE',
            'iphone 8 plus': 'IP8P',
            'iphone 8': 'IP8',
            'iphone 7 plus': 'IP7P',
            'iphone 7': 'IP7',
            'galaxy s24 ultra': 'S24U',
            'galaxy s24+': 'S24P',
            'galaxy s24 plus': 'S24P',
            'galaxy s24': 'S24',
            'galaxy s23 ultra': 'S23U',
            'galaxy s23+': 'S23P',
            'galaxy s23 plus': 'S23P',
            'galaxy s23': 'S23',
            'galaxy s22 ultra': 'S22U',
            'galaxy s22+': 'S22P',
            'galaxy s22': 'S22',
            'galaxy s21 ultra': 'S21U',
            'galaxy s21+': 'S21P',
            'galaxy s21': 'S21',
            'galaxy z fold 5': 'ZF5',
            'galaxy z fold 4': 'ZF4',
            'galaxy z flip 5': 'ZFL5',
            'galaxy z flip 4': 'ZFL4',
            'galaxy a54': 'A54',
            'galaxy a53': 'A53',
            'galaxy a52': 'A52',
            'galaxy a51': 'A51',
            'galaxy a34': 'A34',
            'galaxy a33': 'A33',
            'galaxy a14': 'A14',
            'pixel 8 pro': 'PX8P',
            'pixel 8': 'PX8',
            'pixel 7 pro': 'PX7P',
            'pixel 7': 'PX7',
        }

        model_code = 'UNK'
        for model, code in model_map.items():
            if model in name_lower:
                model_code = code
                break

        # BRAND code: PULL (Original din Dezmembrări), OEM (Premium OEM), sau JK/GX/ZY/RJ etc.
        if calitate == 'Original din Dezmembrări':
            brand_code = 'PULL'
        elif brand_piesa == 'Premium OEM':
            brand_code = 'OEM'
        elif brand_piesa:
            brand_code = brand_piesa.upper().replace(' ', '')[:4]  # JK, GX, ZY, AppleOriginal -> APPL
            if len(brand_code) < 2:
                brand_code = brand_code.ljust(2, 'X')
        else:
            brand_code = 'XX'

        return f"WG-{type_code}-{model_code}-{brand_code}-{counter:02d}"

    def extract_product_attributes(self, product_name, description='', product_url=''):
        """
        Extrage atributele WooCommerce din titlul produsului (și opțional din URL slug).
        Returnează: pa_model, pa_calitate, pa_brand-piesa, pa_tehnologie
        """
        text = f"{product_name} {description}".lower()

        # MODEL COMPATIBIL (ordinea contează - cele mai specifice primele)
        model = ''
        model_patterns = [
            ('iphone 17 pro max', 'iPhone 17 Pro Max'),
            ('iphone 17 pro', 'iPhone 17 Pro'),
            ('iphone 17 plus', 'iPhone 17 Plus'),
            ('iphone 17 air', 'iPhone 17 Air'),
            ('iphone 17', 'iPhone 17'),
            ('iphone 16 pro max', 'iPhone 16 Pro Max'),
            ('iphone 16 pro', 'iPhone 16 Pro'),
            ('iphone 16 plus', 'iPhone 16 Plus'),
            ('iphone 16', 'iPhone 16'),
            ('iphone 15 pro max', 'iPhone 15 Pro Max'),
            ('iphone 15 pro', 'iPhone 15 Pro'),
            ('iphone 15 plus', 'iPhone 15 Plus'),
            ('iphone 15', 'iPhone 15'),
            ('iphone 14 pro max', 'iPhone 14 Pro Max'),
            ('iphone 14 pro', 'iPhone 14 Pro'),
            ('iphone 14 plus', 'iPhone 14 Plus'),
            ('iphone 14', 'iPhone 14'),
            ('iphone 13 pro max', 'iPhone 13 Pro Max'),
            ('iphone 13 pro', 'iPhone 13 Pro'),
            ('iphone 13 mini', 'iPhone 13 Mini'),
            ('iphone 13', 'iPhone 13'),
            ('iphone 12 pro max', 'iPhone 12 Pro Max'),
            ('iphone 12 pro', 'iPhone 12 Pro'),
            ('iphone 12 mini', 'iPhone 12 Mini'),
            ('iphone 12', 'iPhone 12'),
            ('iphone 11 pro max', 'iPhone 11 Pro Max'),
            ('iphone 11 pro', 'iPhone 11 Pro'),
            ('iphone 11', 'iPhone 11'),
            ('iphone xs max', 'iPhone XS Max'),
            ('iphone xs', 'iPhone XS'),
            ('iphone xr', 'iPhone XR'),
            ('iphone x', 'iPhone X'),
            ('iphone se', 'iPhone SE'),
            ('galaxy s24 ultra', 'Galaxy S24 Ultra'),
            ('galaxy s24+', 'Galaxy S24+'),
            ('galaxy s24', 'Galaxy S24'),
            ('galaxy s23 ultra', 'Galaxy S23 Ultra'),
            ('galaxy s23+', 'Galaxy S23+'),
            ('galaxy s23', 'Galaxy S23'),
            ('galaxy s22 ultra', 'Galaxy S22 Ultra'),
            ('galaxy s22', 'Galaxy S22'),
            ('galaxy s21 ultra', 'Galaxy S21 Ultra'),
            ('galaxy s21', 'Galaxy S21'),
            ('galaxy z fold 5', 'Galaxy Z Fold 5'),
            ('galaxy z fold 4', 'Galaxy Z Fold 4'),
            ('galaxy z flip 5', 'Galaxy Z Flip 5'),
            ('galaxy z flip 4', 'Galaxy Z Flip 4'),
            ('galaxy a54', 'Galaxy A54'),
            ('galaxy a53', 'Galaxy A53'),
            ('galaxy a52', 'Galaxy A52'),
            ('galaxy a51', 'Galaxy A51'),
            ('galaxy a34', 'Galaxy A34'),
            ('galaxy a14', 'Galaxy A14'),
            ('pixel 8 pro', 'Pixel 8 Pro'),
            ('pixel 8', 'Pixel 8'),
            ('pixel 7 pro', 'Pixel 7 Pro'),
            ('pixel 7', 'Pixel 7'),
        ]
        for pattern, value in model_patterns:
            if pattern in text:
                model = value
                break

        # Fallback: extrage model din URL slug (ex: .../iphone-17-aftermarket-plus-soft...)
        if not model and product_url:
            slug_lower = product_url.rstrip('/').split('/')[-1].replace('-', ' ')
            for pattern, value in model_patterns:
                if pattern in slug_lower:
                    model = value
                    break

        # Fallback obligatoriu iPhone: dacă titlul conține "iPhone" + cifre/termeni, extrage modelul
        if not model and 'iphone' in text:
            iphone_match = re.search(
                r'iphone\s+(\d+\s*(?:pro\s*max|pro|plus|mini|air)?|\d+)',
                f"{product_name} {description}", re.I
            )
            if iphone_match:
                model_raw = iphone_match.group(0).strip()  # "iPhone 17" sau "iPhone 14 Pro Max"
                for pattern, value in model_patterns:
                    if pattern in model_raw.lower():
                        model = value
                        break
                if not model:
                    model = model_raw.title()

        # Fallback final: extract_phone_model() pentru iPhone/Galaxy neacoperite de listă
        if not model:
            model = self.extract_phone_model(product_name)

        # CALITATE (Logică WebGSM: Genuine OEM -> Service Pack, Used OEM Pull -> Original din Dezmembrări)
        calitate = 'Aftermarket'
        if 'used oem pull' in text or 'oem pull' in text:
            calitate = 'Original din Dezmembrări'
        elif 'service pack' in text or ('original' in text and 'genuine' in text):
            calitate = 'Service Pack'
        elif 'genuine oem' in text or 'genuine' in text:
            calitate = 'Service Pack'
        elif 'aftermarket plus' in text:
            calitate = 'Aftermarket Plus'
        elif 'premium' in text or ('oem' in text and 'premium' in text):
            calitate = 'Premium OEM'
        elif 'oem' in text:
            calitate = 'Premium OEM'
        elif 'refurbished' in text or 'refurb' in text:
            calitate = 'Refurbished'

        # BRAND PIESA - extragere din titlul original (EN): Ampsentrix, JK, ZY, GX, Hex, Genuine
        brand_piesa = ''
        brand_patterns = [
            ('Qianli', ['qianli', '(qianli)']),
            ('iBridge', ['ibridge']),
            ('Mijia', ['mijia']),
            ('Xiaomi', ['xiaomi', '(xiaomi)']),
            ('Ampsentrix', ['ampsentrix']),
            ('JK', [' jk ', ' jk-', '(jk)', 'jk incell', 'jk soft']),
            ('ZY', [' zy ', ' zy-', '(zy)', 'zy soft']),
            ('GX', [' gx ', ' gx-', '(gx)', 'gx soft', 'gx hard']),
            ('Hex', [' hex ', ' hex-', '(hex)', 'hex ']),
            ('Genuine', ['genuine']),
            ('RJ', [' rj ', ' rj-', '(rj)', 'rj incell']),
            ('Foxconn', ['foxconn']),
            ('BOE', [' boe ', '(boe)']),
            ('Tianma', ['tianma']),
        ]
        padded_name = f' {product_name} '.lower()
        padded_text = f' {product_name} {description} '.lower()
        for brand, keywords in brand_patterns:
            if any(kw in padded_text for kw in keywords):
                brand_piesa = brand
                break
        if not brand_piesa:
            if 'apple' in text and ('original' in text or 'genuine' in text or 'service pack' in text):
                brand_piesa = 'Apple Original'
            elif 'samsung' in text and ('original' in text or 'genuine' in text or 'service pack' in text):
                brand_piesa = 'Samsung Original'
            elif 'oem' in text or calitate in ('Premium OEM', 'Service Pack'):
                brand_piesa = 'Premium OEM'
        # NU pune "Aftermarket Plus" în brand_piesa - e CALITATE, nu brand. Brand = JK, GX, ZY, RJ sau Premium OEM.

        # TEHNOLOGIE - din titlul original (EN): OLED, Soft OLED, Incell, TFT
        tehnologie = ''
        if any(x in text for x in ['display', 'screen', 'lcd', 'oled', 'ecran', 'assembly']):
            if 'soft' in text and 'oled' in text:
                tehnologie = 'Soft OLED'
            elif 'soft oled' in text:
                tehnologie = 'Soft OLED'
            elif ': soft)' in text or ': soft ' in text or ': soft' in text or ':soft' in text:
                # Pattern MobileSentrix: "(Aftermarket Plus: Soft)"
                tehnologie = 'Soft OLED'
            elif 'hard oled' in text:
                tehnologie = 'Hard OLED'
            elif ': hard)' in text or ': hard ' in text or ':hard' in text:
                # Pattern MobileSentrix: "(Aftermarket Plus: Hard)"
                tehnologie = 'Hard OLED'
            elif 'amoled' in text:
                tehnologie = 'AMOLED'
            elif 'oled' in text and ('original' in text or 'genuine' in text):
                tehnologie = 'OLED Original'
            elif 'oled' in text:
                tehnologie = 'OLED'
            elif 'incell' in text or 'in-cell' in text:
                tehnologie = 'Incell'
            elif 'tft' in text:
                tehnologie = 'TFT'
            elif 'lcd' in text:
                tehnologie = 'LCD'

        # 🎯 Detectare 120Hz / 90Hz din titlu
        self._detected_refresh_rate = ''
        if '120hz' in text or '120 hz' in text:
            self._detected_refresh_rate = '120Hz'
        elif '90hz' in text or '90 hz' in text:
            self._detected_refresh_rate = '90Hz'

        return {
            'pa_model': model,
            'pa_calitate': calitate,
            'pa_brand_piesa': brand_piesa,
            'pa_tehnologie': tehnologie
        }

    def get_webgsm_category(self, product_name, product_type='', description=''):
        """
        Determină slug-ul categoriei WooCommerce conform arborelui WebGSM.
        Returnează doar slug-uri valide: ecrane-iphone, baterii-samsung, mufe-incarcare-iphone,
        surubelnite, folii-protectie, etc. NU folosește: accesorii-service, ecrane-telefoane, baterii-iphone-piese.
        """
        text = ((product_name or '') + ' ' + (description or '') + ' ' + (product_type or '')).lower()

        # === DETECTARE BRAND ===
        brand = None
        if any(x in text for x in ['iphone', 'apple', 'ios']):
            brand = 'iphone'
        elif any(x in text for x in ['samsung', 'galaxy']):
            brand = 'samsung'
        elif any(x in text for x in ['huawei', 'honor', 'mate ', 'p30', 'p40', 'p50', 'p60']):
            brand = 'huawei'
        elif any(x in text for x in ['xiaomi', 'redmi', 'poco', 'mi ']):
            brand = 'xiaomi'
        elif any(x in text for x in ['pixel', 'google']):
            brand = 'google'
        elif any(x in text for x in ['oneplus', 'one plus']):
            brand = 'oneplus'

        # === PIESE: Ecrane / Display ===
        if any(x in text for x in ['ecran', 'display', 'lcd', 'oled', 'screen', 'touchscreen']):
            if brand == 'iphone':
                return 'ecrane-iphone'
            if brand == 'samsung':
                return 'ecrane-samsung'
            if brand == 'huawei':
                return 'ecrane-huawei'
            if brand == 'xiaomi':
                return 'ecrane-xiaomi'
            return 'piese'

        # === PIESE: Baterii ===
        if any(x in text for x in ['baterie', 'battery', 'acumulator', 'accumulator']):
            if brand == 'iphone':
                return 'baterii-iphone'
            if brand == 'samsung':
                return 'baterii-samsung'
            if brand == 'huawei':
                return 'baterii-huawei'
            if brand == 'xiaomi':
                return 'baterii-xiaomi'
            return 'piese'

        # === PIESE: Camere ===
        if any(x in text for x in ['camera', 'cameră', 'foto', 'lens', 'lentila']):
            if brand == 'iphone':
                return 'camere-iphone'
            if brand == 'samsung':
                return 'camere-samsung'
            if brand == 'huawei':
                return 'camere-huawei'
            if brand == 'xiaomi':
                return 'camere-xiaomi'
            return 'piese'

        # === PIESE: Mufe încărcare ===
        if any(x in text for x in ['mufă', 'mufa', 'charging port', 'port încărcare', 'usb-c', 'lightning connector', 'dock connector']):
            if brand == 'iphone':
                return 'mufe-incarcare-iphone'
            if brand == 'samsung':
                return 'mufe-incarcare-samsung'
            return 'piese'

        # === PIESE: Flexuri ===
        if any(x in text for x in ['flex', 'cablu flex', 'ribbon', 'flat cable']):
            if brand == 'iphone':
                return 'flexuri-iphone'
            if brand == 'samsung':
                return 'flexuri-samsung'
            return 'piese'

        # === PIESE: Carcase ===
        if any(x in text for x in ['carcasă', 'carcasa', 'back cover', 'housing', 'back glass', 'capac spate']):
            if brand == 'iphone':
                return 'carcase-iphone'
            return 'piese'

        # === PIESE: Difuzoare ===
        if any(x in text for x in ['difuzor', 'speaker', 'buzzer', 'earpiece', 'loud speaker']):
            if brand == 'iphone':
                return 'difuzoare-iphone'
            return 'piese'

        # === UNELTE ===
        if any(x in text for x in ['șurubelniță', 'surubelnita', 'screwdriver', 'torx', 'pentalobe', 'phillips']):
            return 'surubelnite'
        if any(x in text for x in ['pensetă', 'penseta', 'tweezer', 'pincetă']):
            return 'pensete'
        if any(x in text for x in ['stație lipit', 'statie lipit', 'soldering station', 'hot air', 'pistol aer cald']):
            return 'statii-lipit'
        if any(x in text for x in ['separator', 'lcd separator', 'screen separator']):
            return 'separatoare-ecrane'
        if any(x in text for x in ['microscop', 'microscope', 'lupa', 'magnifier']):
            return 'microscoape'
        if any(x in text for x in ['programator', 'programmer', 'box', 'jc', 'qianli', 'i2c']):
            return 'programatoare'
        if any(x in text for x in ['kit', 'set complet', 'tool kit']):
            return 'kituri-complete'

        # === ACCESORII ===
        if any(x in text for x in ['husă', 'husa', 'case', 'cover', 'protector']):
            return 'huse-carcase'
        if any(x in text for x in ['folie', 'screen protector', 'tempered glass', 'sticlă securizată']):
            return 'folii-protectie'
        if any(x in text for x in ['cablu', 'cable', 'încărcător', 'charger', 'adaptor', 'adapter']):
            return 'cabluri-incarcatoare'
        if any(x in text for x in ['adeziv', 'adhesive', 'b7000', 't7000', 'b8000', 'banda dublu adezivă', 'sticker']):
            return 'adezivi-consumabile'

        # === DISPOZITIVE ===
        if any(x in text for x in ['telefon second', 'second hand', 'folosit', 'used phone']):
            return 'telefoane-folosite'
        if any(x in text for x in ['refurbished', 'recondiționat', 'renewed']):
            return 'telefoane-refurbished'
        if any(x in text for x in ['tabletă', 'tablet', 'ipad']):
            return 'tablete'
        if any(x in text for x in ['smartwatch', 'ceas smart', 'apple watch', 'galaxy watch']):
            return 'smartwatch'

        # === DEFAULT: brand cunoscut → piese-{brand}, altfel piese ===
        if brand == 'iphone':
            return 'piese-iphone'
        if brand == 'samsung':
            return 'piese-samsung'
        if brand == 'huawei':
            return 'piese-huawei'
        if brand == 'xiaomi':
            return 'piese-xiaomi'
        return 'piese'

    def _detect_brand_for_category(self, name_lower):
        """Inferă brandul pentru ramura Piese (Piese > Piese {Brand} > ...). Prioritate: iPhone/Apple, Samsung/Galaxy, Huawei/Honor, Xiaomi/Redmi/Poco, OnePlus."""
        if 'iphone' in name_lower or 'apple' in name_lower:
            return 'iPhone'
        if 'samsung' in name_lower or 'galaxy' in name_lower:
            return 'Samsung'
        if 'huawei' in name_lower or 'honor' in name_lower:
            return 'Huawei'
        if 'xiaomi' in name_lower or 'redmi' in name_lower or 'poco' in name_lower:
            return 'Xiaomi'
        if 'oneplus' in name_lower:
            return 'OnePlus'
        if 'google' in name_lower or 'pixel' in name_lower:
            return 'Google'
        if 'motorola' in name_lower or 'moto ' in name_lower:
            return 'Motorola'
        if 'ipad' in name_lower:
            return 'iPad'
        return None

    def _detect_piese_tip(self, combined):
        """Detectează tipul piesei (nivel 3 sub Piese) din text."""
        for keywords, tip_name in PIESE_TIP_KEYWORDS:
            if any(kw in combined for kw in keywords):
                return tip_name
        return 'Alte Piese'

    def _detect_unelte_sub(self, combined):
        """Detectează subcategoria Unelte (Unelte > Subcategorie)."""
        for keywords, sub_name in UNELTE_SUBCAT_KEYWORDS:
            if any(kw in combined for kw in keywords):
                return sub_name
        return 'Șurubelnițe'  # default

    def _detect_accesorii_sub(self, combined):
        """Detectează subcategoria Accesorii (Accesorii > Subcategorie)."""
        for keywords, sub_name in ACCESORII_SUBCAT_KEYWORDS:
            if any(kw in combined for kw in keywords):
                return sub_name
        return 'Adezivi & Consumabile'  # default

    def get_woo_category(self, product_name, product_type='', manual_code=None, description='', url_slug='', tags=''):
        """
        Returnează categoria WooCommerce. Prioritate detectare: Titlu > URL slug > Descriere > Taguri.
        - PIESE (3 nivele): Piese > Piese {BRAND} > Tip (brand din titlu/descriere)
        - UNELTE (2 nivele): Unelte > Subcategorie
        - ACCESORII (2 nivele): Accesorii > Subcategorie
        - Nimic detectat: Uncategorized + log pentru review.
        """
        name_lower = (product_name or '').lower()
        type_lower = (product_type or '').lower()
        slug_lower = (url_slug or '').replace('-', ' ').lower()
        desc_snippet = (description or '')[:500].lower()
        tags_lower = (tags or '').lower()
        # Prioritate: titlu > slug > descriere > taguri (toate în combined pentru matching)
        combined = ' '.join(filter(None, [name_lower, type_lower, slug_lower, desc_snippet, tags_lower]))

        # —— Prioritate: cod manual din sku_list (link | COD) ——
        if manual_code and isinstance(manual_code, str):
            manual_code = manual_code.strip().upper()
            if manual_code in CATEGORY_CODE_MAP:
                m = CATEGORY_CODE_MAP[manual_code]
                top = m.get('top') or m.get('cat')
                if top == 'Piese':
                    cat_name = m.get('cat', '')
                    brand = self._detect_brand_for_category(name_lower) or self._detect_brand_for_category(combined) or 'iPhone'
                    return f"Piese > Piese {brand} > {cat_name}"
                if m.get('cat') == 'Unelte':
                    sub = m.get('sub') or self._detect_unelte_sub(combined)
                    return f"Unelte > {sub}"
                if m.get('cat') == 'Accesorii':
                    return f"Accesorii > {m.get('sub', 'Adezivi & Consumabile')}"
                if m.get('sub'):
                    return f"Accesorii > {m.get('sub')}"
                return f"Unelte > {self._detect_unelte_sub(combined)}"

        # —— Auto: PIESE (3 nivele) – detectare BRAND + TIP ——
        brand = self._detect_brand_for_category(name_lower) or self._detect_brand_for_category(combined)
        if brand:
            tip = self._detect_piese_tip(combined)
            return f"Piese > Piese {brand} > {tip}"

        # —— Auto: ACCESORII Folii ÎNAINTE de Unelte ——
        if any(kw in combined for kw in ACCESORII_FOLII_KEYWORDS):
            return "Accesorii > Folii Protecție"

        # —— Auto: UNELTE (2 nivele) ——
        for keywords, _ in UNELTE_SUBCAT_KEYWORDS:
            if any(kw in combined for kw in keywords):
                sub = self._detect_unelte_sub(combined)
                return f"Unelte > {sub}"
        if any(x in combined for x in ['tool', 'unealtă', 'unealta', 'statie', 'station', 'preheater', 'separator', 'microscop', 'tester', 'diagnostic', 'programmer', 'programator', 'kit', 'repair kit']):
            sub = self._detect_unelte_sub(combined)
            return f"Unelte > {sub}"

        # —— Auto: ACCESORII (2 nivele) – doar dacă avem keyword accesorii ——
        sub = self._detect_accesorii_sub(combined)
        if sub != 'Adezivi & Consumabile':
            return f"Accesorii > {sub}"
        if any(kw in combined for kw in ['case', 'husa', 'cable', 'charger', 'adeziv', 'tape', 'b7000', 'folie', 'protector', 'cover', 'bumper']):
            return f"Accesorii > {sub}"

        # —— Nimic detectat: Uncategorized + log ——
        try:
            self.log(f"   ⚠ Categorie necunoscută pentru: {product_name[:50]}... → Uncategorized (review manual)", "WARNING")
        except Exception:
            pass
        return "Uncategorized"

    def extract_phone_model(self, product_name):
        """
        Extrage modelul telefonului pentru atributul pa_model (Model Compatibil).
        Folosit ca fallback când extract_product_attributes nu găsește un model din listă.

        Returns:
            String cu modelul (ex: "iPhone 14 Pro Max") sau "" dacă nu găsește
        """
        name = product_name or ''
        # iPhone: iPhone 17 Pro Max, iPhone 14, etc.
        iphone_pattern = r'iPhone\s*(\d+)\s*(Pro\s*Max|Pro|Plus|Mini|Air)?'
        match = re.search(iphone_pattern, name, re.IGNORECASE)
        if match:
            model = f'iPhone {match.group(1)}'
            if match.group(2):
                model += f' {match.group(2)}'
            return model.strip()
        # Samsung Galaxy: Galaxy S24 Ultra, Galaxy A54, etc.
        galaxy_pattern = r'Galaxy\s*(S|A|Z|Note|M)?\s*(\d+)\s*(Ultra|Plus|\+|FE|Fold|Flip)?'
        match = re.search(galaxy_pattern, name, re.IGNORECASE)
        if match:
            model = 'Galaxy'
            if match.group(1):
                model += f' {match.group(1)}{match.group(2)}'
            else:
                model += f' {match.group(2)}'
            if match.group(3):
                model += f' {match.group(3)}'
            return model.strip()
        return ''

    def extract_compatibility_codes(self, description):
        """
        Extrage coduri Apple (A####) din descriere.
        Returnează string cu coduri separate prin virgulă.
        """
        pattern = r'\bA\d{4}\b'
        codes = re.findall(pattern, description)
        return ', '.join(sorted(set(codes))) if codes else ''

    def detect_screen_features(self, product_name, description=''):
        """
        Detectează caracteristici ecran: IC Movable, TrueTone support.
        Doar pentru produse ecran (LCD, OLED, display, screen). La restul nu populăm aceste câmpuri.
        """
        text = f"{product_name} {description}".lower()
        is_screen = any(x in text for x in [
            'display', 'screen', 'oled', 'lcd', 'ecran', 'assembly', 'digitizer', 'amoled'
        ])
        if not is_screen:
            return {'ic_movable': 'false', 'truetone_support': 'false'}

        ic_movable = 'true' if any(x in text for x in [
            'with ic', 'ic installed', 'ic included', 'movable ic',
            'transplant ic', 'ic transferabil', 'ic chip', 'flex with ic'
        ]) else 'false'

        truetone = 'true' if any(x in text for x in [
            'true tone', 'truetone', 'true-tone', 'supports true tone',
            'support truetone', 'true tone supported'
        ]) else 'false'

        return {
            'ic_movable': ic_movable,
            'truetone_support': truetone
        }

    def _detect_tip_produs_ro(self, product_name):
        """
        Detectează tipul produsului în română din titlul EN.
        Mapări WebGSM: Charging Port -> Conector Încărcare, Battery -> Baterie, Folie/UV film -> Folie protecție.
        """
        text = product_name.lower()
        if any(x in text for x in ['folie', 'screen protector', 'protector ecran', 'uv film', 'film protector', 'tempered glass', 'matt privacy', 'privacy film']):
            return 'Folie protecție'
        if 'charging port' in text:
            return 'Conector Încărcare'
        if any(x in text for x in ['battery', 'baterie', 'acumulator']):
            return 'Baterie'
        if any(x in text for x in ['back camera', 'rear camera', 'cameră spate']):
            return 'Cameră Spate'
        if any(x in text for x in ['display', 'screen', 'oled', 'lcd', 'digitizer']):
            return 'Ecran'
        if any(x in text for x in ['camera', 'cameră', 'lens']):
            return 'Cameră'
        if any(x in text for x in ['flex', 'cable', 'connector', 'dock']):
            return 'Flex'
        if any(x in text for x in ['housing', 'back glass', 'frame', 'back cover', 'rear glass']):
            return 'Carcasă'
        if any(x in text for x in ['speaker', 'earpiece', 'buzzer']):
            return 'Difuzor'
        if any(x in text for x in ['button', 'power button', 'volume']):
            return 'Buton'
        if 'screwdriver' in text:
            return 'Șurubelniță'
        if 'screw' in text:
            return 'Șurub'
        if 'seal' in text:
            return 'Garnitură'
        if any(x in text for x in ['tester', 'diagnostic', 'test tool', 'analysis tester']):
            return 'Tester'
        return 'Componentă'

    def generate_seo_title(self, product_name, model, brand_piesa, tehnologie):
        """
        Generează titlu SEO optimizat (max 60 chars pentru Google).
        Format: "{Tip} {Model} {Tehnologie} {Brand} {120Hz} - Garanție | WebGSM"
        Exemplu: "Ecran iPhone 17 Soft OLED 120Hz - Garanție | WebGSM"
        """
        tip_ro = self._detect_tip_produs_ro(product_name)

        parts = [tip_ro]
        if model:
            parts.append(model)
        if tehnologie:
            parts.append(tehnologie)
        if brand_piesa:
            parts.append(brand_piesa)

        # Detectează 120Hz din titlul original
        name_lower = product_name.lower()
        if '120hz' in name_lower or '120 hz' in name_lower:
            parts.append('120Hz')

        title = ' '.join(parts)
        seo = f"{title} - Garanție | WebGSM"

        # Dacă e prea lung (>60 chars), scurtăm sufixul
        if len(seo) > 60:
            seo = f"{title} | WebGSM"
        if len(seo) > 60:
            seo = title[:57] + "..."

        return self.fix_romanian_diacritics(seo)

    def generate_seo_description(self, product_name, model, brand_piesa, tehnologie, calitate):
        """
        Generează meta description SEO (max 155 caractere).
        Exemplu: "Ecran iPhone 17 Soft OLED calitate Aftermarket Plus 120Hz. Garanție 24 luni. Livrare rapidă România."
        """
        tip_ro = self._detect_tip_produs_ro(product_name)

        desc = f"{tip_ro} {model or ''}"
        if tehnologie:
            desc += f" {tehnologie}"
        if brand_piesa:
            desc += f" {brand_piesa}"
        if calitate:
            desc += f" calitate {calitate}"

        # Detectează 120Hz din titlul original
        name_lower = product_name.lower()
        if '120hz' in name_lower or '120 hz' in name_lower:
            desc += " 120Hz"

        desc += ". Garanție 24 luni. Livrare rapidă România."

        # Curăță spații duble
        desc = ' '.join(desc.split())

        if len(desc) > 155:
            desc = desc[:152] + "..."

        return self.fix_romanian_diacritics(desc)

    def generate_focus_keyword(self, product_name, model):
        """
        Generează focus keyword pentru Rank Math SEO.
        Exemplu: "ecran iphone 17 oled"
        """
        tip_map = {
            'display': 'ecran', 'screen': 'ecran', 'oled': 'ecran',
            'lcd': 'ecran', 'digitizer': 'ecran', 'assembly': 'ecran',
            'battery': 'baterie', 'acumulator': 'baterie',
            'camera': 'camera', 'lens': 'camera',
            'flex': 'flex', 'cable': 'flex', 'connector': 'flex',
            'charging port': 'port incarcare',
            'housing': 'carcasa', 'back glass': 'carcasa', 'frame': 'carcasa',
            'speaker': 'difuzor', 'earpiece': 'difuzor',
            'button': 'buton',
        }
        text = product_name.lower()
        tip_ro = 'piesa'
        for en, ro in tip_map.items():
            if en in text:
                tip_ro = ro
                break

        parts = [tip_ro]
        if model:
            parts.append(model.lower())

        # Adaugă tehnologia principală pentru keyword mai precis
        if 'oled' in text:
            parts.append('oled')
        elif 'lcd' in text:
            parts.append('lcd')

        return ' '.join(parts)

    def test_connection(self):
        """Testează conexiunea la WooCommerce"""
        try:
            self.log("Testez conexiunea la WooCommerce...", "INFO")
            
            wcapi = API(
                url=self.wc_url_var.get(),
                consumer_key=self.wc_key_var.get(),
                consumer_secret=self.wc_secret_var.get(),
                version="wc/v3",
                timeout=30
            )
            
            # Test request
            response = wcapi.get("products", params={"per_page": 1})
            
            if response.status_code == 200:
                self.log("✓ Conexiune reușită la WooCommerce!", "SUCCESS")
                messagebox.showinfo("Succes", "Conexiunea la WooCommerce este funcțională!")
                self.wc_api = wcapi
            else:
                self.log(f"✗ Eroare conexiune: Status {response.status_code}", "ERROR")
                messagebox.showerror("Eroare", f"Status Code: {response.status_code}\n{response.text}")
                
        except Exception as e:
            self.log(f"✗ Eroare conexiune: {e}", "ERROR")
            messagebox.showerror("Eroare", f"Nu s-a putut conecta la WooCommerce:\n{e}")
    
    def browse_sku_file(self):
        """Selectează fișier SKU"""
        filename = filedialog.askopenfilename(
            title="Selectează fișierul cu SKU-uri",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filename:
            self.sku_file_var.set(filename)
    
    def start_import(self):
        """Pornește importul"""
        sku_path = Path(self.sku_file_var.get())
        if not sku_path.exists() and not sku_path.is_absolute():
            sku_path = self._script_dir / self.sku_file_var.get()
        if not sku_path.exists():
            messagebox.showerror("Eroare", f"Fișierul {self.sku_file_var.get()} nu există!")
            return
        self._resolved_sku_file = str(sku_path)
        
        self.running = True
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.progress_bar.start()
        
        # Rulează import în thread separat
        thread = threading.Thread(target=self.run_import, daemon=True)
        thread.start()
    
    def stop_import(self):
        """Oprește importul"""
        self.running = False
        self.log("⛔ Import oprit de utilizator", "WARNING")
        self.progress_bar.stop()
        self.btn_start.config(state='normal')
        self.btn_stop.config(state='disabled')
        self.progress_var.set("Import oprit")

    def check_batch_badge_settings(self, product_data):
        """Verifică dacă există setări batch pentru acest produs (model compatibil). Returnează (badge_data, style) sau None."""
        if not getattr(self, 'batch_badge_settings', None):
            return None
        batch = self.batch_badge_settings
        batch_model = (batch.get('model') or '').strip()
        current_model = (product_data.get('pa_model') or '').strip()
        if batch_model and current_model and batch_model in current_model:
            return batch.get('data'), batch.get('style')
        return None

    def _run_badge_preview(self, images_list, image_index, product_data):
        """Rulează pe main thread: deschide fereastra de preview badge-uri pentru imaginea image_index."""
        name = (product_data.get('name') or '').lower()
        detected_data = {
            'brand': product_data.get('pa_brand_piesa') or None,
            'model': product_data.get('pa_model') or None,
            'tehnologie': product_data.get('pa_tehnologie') or None,
            'hz_120': '120hz' in name or '120 hz' in name,
            'hz_text': '120Hz' if ('120hz' in name or '120 hz' in name) else '',
            'ic_transferabil': product_data.get('ic_movable') == 'true',
            'truetone': product_data.get('truetone_support') == 'true',
        }

        def on_done(action, data):
            self._badge_result = {'action': action, 'data': data, 'image_index': image_index}
            if getattr(self, '_badge_event', None):
                self._badge_event.set()

        img_item = images_list[image_index]
        image_path = img_item.get('local_path', img_item) if isinstance(img_item, dict) else img_item
        total = len(images_list)
        BadgePreviewWindow(self.root, image_path, detected_data, on_done, self._script_dir, image_index=image_index, total_images=total)

    def process_images_with_badges(self, images_list, product_data):
        """
        Procesează imaginile: permite Skip pe poză (trece la următoarea imagine) sau Fără Badge (renunță la tot produsul).
        Badge se aplică pe prima imagine pe care userul o confirmă (sau prima dacă batch).
        """
        if not images_list or not self.badge_preview_var.get():
            return images_list

        batch_result = self.check_batch_badge_settings(product_data)
        if batch_result is not None:
            batch_data, batch_style = batch_result
            first = images_list[0]
            first_path = first.get('local_path', first) if isinstance(first, dict) else first
            if first_path and Path(first_path).exists():
                out_path = str(Path(first_path).with_suffix('')) + '_badge.webp'
                generate_badge_preview(first_path, batch_data, out_path, style=batch_style, script_dir=self._script_dir)
                if isinstance(first, dict):
                    images_list[0] = {**first, 'local_path': out_path, 'name': Path(out_path).name}
                else:
                    images_list[0] = out_path
            self.log(f"   🏷️ Badge aplicat (batch) pe prima imagine", "INFO")
            return images_list

        idx = 0
        while idx < len(images_list):
            img_item = images_list[idx]
            img_path = img_item.get('local_path', img_item) if isinstance(img_item, dict) else img_item
            if not img_path or not Path(img_path).exists():
                idx += 1
                continue
            self._badge_event = threading.Event()
            self._badge_result = None
            self.root.after(0, lambda i=idx: self._run_badge_preview(images_list, i, product_data))
            self._badge_event.wait()
            res = self._badge_result
            if not res:
                return images_list
            action = res.get('action')
            if action == 'skip':
                return images_list
            if action == 'skip_image':
                idx += 1
                continue
            payload = res.get('data')
            apply_badges = payload.get('apply_badges', True) if isinstance(payload, dict) else True
            badge_data = payload.get('data') if isinstance(payload, dict) else payload
            style = payload.get('style') if isinstance(payload, dict) else None
            if not apply_badges:
                self.log(f"   🏷️ Fără badge (opțiune debifată) – imagine neschimbată", "INFO")
                return images_list
            first_path = img_path
            first = img_item
            if action == 'confirm' and badge_data:
                out_path = str(Path(first_path).with_suffix('')) + '_badge.webp'
                generate_badge_preview(first_path, badge_data, out_path, style=style, script_dir=self._script_dir)
                if isinstance(first, dict):
                    images_list[idx] = {**first, 'local_path': out_path, 'name': Path(out_path).name}
                else:
                    images_list[idx] = out_path
                self.log(f"   🏷️ Badge confirmat pe imaginea {idx + 1}", "INFO")
                return images_list
            if action == 'batch' and badge_data and apply_badges:
                self.batch_badge_settings = {'model': badge_data.get('model'), 'data': badge_data, 'style': style}
                out_path = str(Path(first_path).with_suffix('')) + '_badge.webp'
                generate_badge_preview(first_path, badge_data, out_path, style=style, script_dir=self._script_dir)
                if isinstance(first, dict):
                    images_list[idx] = {**first, 'local_path': out_path, 'name': Path(out_path).name}
                else:
                    images_list[idx] = out_path
                self.log(f"   🏷️ Badge aplicat (batch) pe imaginea {idx + 1}", "INFO")
                return images_list
            idx += 1
        return images_list

    def run_import(self):
        """Execută exportul în CSV format WebGSM cu upload imagini pe WordPress"""
        try:
            self.log("=" * 70, "INFO")
            self.log(f"🚀 START PROCESARE PRODUSE (Mod: CSV WebGSM + Upload Imagini)", "INFO")
            self.log("=" * 70, "INFO")

            # Citește SKU-uri (listă dict: url, code opțional din "link | COD")
            sku_items = self.read_sku_file(getattr(self, '_resolved_sku_file', None) or self.sku_file_var.get())
            self.log(f"📋 Găsite {len(sku_items)} intrări pentru procesare", "INFO")

            success_count = 0
            error_count = 0
            sku_counter = 0  # Counter global pentru SKU-uri WebGSM
            products_data = []  # Lista pentru CSV

            for idx, item in enumerate(sku_items, 1):
                if not self.running:
                    break

                url_or_sku = item['url']
                manual_code = item.get('code')
                display_label = f"{url_or_sku[:55]}..." if len(url_or_sku) > 58 else url_or_sku
                if manual_code:
                    display_label += f" | {manual_code}"
                    if manual_code.strip().upper() in CATEGORY_CODE_MAP:
                        self.log(f"   📌 Cod manual: {manual_code} → categorie și prefix SKU din legendă", "INFO")
                self.progress_var.set(f"Procesez produs {idx}/{len(sku_items)}: {display_label}")
                self.log(f"\n" + "="*70, "INFO")
                self.log(f"[{idx}/{len(sku_items)}] 🔵 START procesare: {display_label}", "INFO")
                self.log(f"="*70, "INFO")

                try:
                    # Scraping produs de pe MobileSentrix
                    product_data = self.scrape_product(url_or_sku)

                    if product_data:
                        # Cod manual din sku_list (link | COD) are prioritate pentru categorie și prefix SKU
                        product_data['manual_category_code'] = manual_code
                        sku_counter += 1
                        brand_piesa = product_data.get('pa_brand_piesa', '')
                        calitate = product_data.get('pa_calitate', '')
                        webgsm_sku = self.generate_webgsm_sku(
                            product_data.get('name', ''),
                            brand_piesa,
                            sku_counter,
                            calitate=calitate,
                            manual_code=manual_code
                        )

                        # Adaugă date suplimentare
                        product_data['webgsm_sku'] = webgsm_sku
                        # sku_furnizor e deja setat corect în scrape_product()
                        # ean_real e deja setat corect în scrape_product()

                        # Preview badge pe prima imagine (opțional): confirmă/modifică/skip; originalul rămâne backup
                        if product_data.get('images') and self.badge_preview_var.get():
                            product_data['images'] = self.process_images_with_badges(product_data['images'], product_data)

                        success_count += 1
                        self.log(f"✓ Produs procesat! SKU: {webgsm_sku}", "SUCCESS")

                        products_data.append(product_data)
                    else:
                        error_count += 1
                        self.log(f"✗ Nu s-au putut extrage datele produsului", "ERROR")

                except Exception as e:
                    error_count += 1
                    self.log(f"✗ Eroare: {e}", "ERROR")

            # CREARE CSV
            csv_filename = None
            csv_path = None
            if products_data:
                self.log("\n" + "=" * 70, "INFO")
                self.log("📝 CREARE FIȘIER CSV WEBGSM...", "INFO")
                self.log("=" * 70, "INFO")

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = f"export_webgsm_{timestamp}.csv"
                csv_path = self.export_to_csv(products_data, csv_filename)

                if csv_path:
                    self.log(f"\n✅ CSV WebGSM creat: {csv_path}", "SUCCESS")

            # Sumar final
            self.log("\n" + "=" * 70, "INFO")
            self.log(f"📊 SUMAR PROCESARE WEBGSM:", "INFO")
            self.log(f"   ✓ Produse procesate cu succes: {success_count}", "SUCCESS")
            self.log(f"   ✗ Erori scraping: {error_count}", "ERROR")
            self.log(f"   📦 Total intrări: {len(sku_items)}", "INFO")
            self.log(f"   📁 Imagini salvate în: images/", "INFO")
            if products_data:
                self.log(f"   🏷️ SKU-uri generate: WG-...-01 pana la WG-...-{sku_counter:02d}", "INFO")
            self.log("=" * 70, "INFO")

            csv_info = f"\nFișier CSV: {csv_filename}" if csv_filename else ""
            messagebox.showinfo("Finalizat",
                f"Procesare WebGSM finalizată!\n\nProduse procesate: {success_count}\nErori: {error_count}{csv_info}\nFolderul imagini: images/")

            # Deschide folderul data cu CSV-ul
            if csv_path:
                os.startfile(str(self._script_dir / "data"))

        except Exception as e:
            self.log(f"✗ Eroare critică: {e}", "ERROR")
            messagebox.showerror("Eroare", f"Eroare critică:\n{e}")

        finally:
            self.progress_bar.stop()
            self.btn_start.config(state='normal')
            self.btn_stop.config(state='disabled')
            self.progress_var.set("Export finalizat")
            self.running = False
    
    def read_sku_file(self, filepath):
        """Citește link-uri, EAN-uri sau SKU-uri din fișier.
        Acceptă:
        - URL direct: https://www.mobilesentrix.eu/...
        - URL cu cod categorie: https://... | BAT  (pipe + spațiu opțional + COD)
        - SKU: 107182127516 (12-13 cifre)
        - EAN: 888888888888 (12-13 cifre - mai rar)
        Returnează listă de dict: [{'url': str, 'code': str|None}, ...]
        """
        items = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '|' in line:
                    parts = line.split('|', 1)
                    url_part = parts[0].strip()
                    code_part = parts[1].strip().upper() if len(parts) > 1 else None
                    if url_part:
                        items.append({'url': url_part, 'code': code_part or None})
                else:
                    items.append({'url': line, 'code': None})
        return items

    def load_category_rules(self, filepath="category_rules.txt"):
        """Încarcă reguli de categorii (keyword | categorie) din fișier configurabil."""
        rules = []
        path = Path(filepath)
        if not path.exists():
            path = self._script_dir / filepath
        if not path.exists():
            return rules
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) >= 2:
                    keyword = parts[0].strip().lower()
                    category_path = parts[1].strip()
                    if keyword and category_path:
                        rules.append((keyword, category_path))
        return rules

    def detect_category(self, product_name, tags):
        """Returnează categoria pe baza keyword-urilor din nume + tag-uri."""
        haystack = f"{product_name} {' '.join(tags)}".lower()
        for keyword, category_path in self.category_rules:
            if keyword in haystack:
                return category_path
        return "Uncategorized"
    
    def detect_warranty(self, product_name, category):
        """Detectează perioada de garanție pe baza categoriei și numelui produsului"""
        text = f"{product_name} {category}".lower()
        
        # 12 luni - Display/LCD
        if any(x in text for x in ['display', 'lcd', 'ecran', 'ecrane', 'screen']):
            return "12 luni"
        
        # 6 luni - Acumulatori/Baterii
        if any(x in text for x in ['acumulator', 'baterie', 'baterii', 'battery', 'baterija']):
            return "6 luni"
        
        # 6 luni - Cabluri Flex
        if any(x in text for x in ['cablu', 'flex', 'cable', 'ribbon']):
            return "6 luni"
        
        # 3 luni - Carcase
        if any(x in text for x in ['carcasa', 'carcase', 'casing', 'housing', 'case back']):
            return "3 luni"
        
        # 1-3 luni - Accesorii (default)
        if any(x in text for x in ['accesoriu', 'accessory', 'protector', 'folie']):
            return "1-3 luni"
        
        # Default pentru alte categorii
        return "12 luni"
    
    def build_longtail_title(self, translated_name, description="", attributes=None):
        """
        Construiește titlu Long Tail SEO optimizat.

        STRATEGIE: Folosește numele tradus (RO) ca bază principală,
        îmbogățit cu atributele deja extrase de extract_product_attributes().

        Format: "{Tip} {Model} {Tehnologie} {Brand} {Culoare} - {Calitate}"
        Exemplu: "Ecran iPhone 13 OLED JK Negru - Premium OEM"

        Args:
            translated_name: Numele produsului tradus în română
            description: Descrierea produsului (EN sau RO)
            attributes: Dict cu pa_model, pa_calitate, pa_brand_piesa, pa_tehnologie
                       (din extract_product_attributes, disponibil ca product dict keys)
        """
        import re

        if not attributes:
            attributes = {}

        # Folosește atributele deja extrase (sunt corecte, testate)
        pa_model = attributes.get('pa_model', '')
        pa_calitate = attributes.get('pa_calitate', '')
        pa_brand_piesa = attributes.get('pa_brand_piesa', '')
        pa_tehnologie = attributes.get('pa_tehnologie', '')

        # 1. TIP PRODUS (RO) - din titlul original EN, deja testat în _detect_tip_produs_ro
        original_name = attributes.get('original_name', translated_name)
        tip_ro = self._detect_tip_produs_ro(original_name)

        # 2. CULOARE - detectare cu word boundaries (previne false positives)
        color_map = {
            'Negru': [r'\bnegru\b', r'\bblack\b', r'\bnoir\b'],
            'Alb': [r'\balb\b', r'\bwhite\b', r'\bblanc\b'],
            'Gri': [r'\bgri\b', r'\bgray\b', r'\bgrey\b'],
            'Argintiu': [r'\bargintiu\b', r'\bsilver\b', r'\bargent\b'],
            'Auriu': [r'\bauriu\b', r'\bgold\b', r'\bgolden\b'],
            'Albastru': [r'\balbastru\b', r'\bblue\b', r'\bbleu\b'],
            'Roșu': [r'\brosu\b', r'\broșu\b', r'\bred\b', r'\brouge\b'],
            'Verde': [r'\bverde\b', r'\bgreen\b', r'\bvert\b'],
            'Roz': [r'\broz\b', r'\bpink\b', r'\brose\b'],
            'Violet': [r'\bviolet\b', r'\bpurple\b', r'\bdeep purple\b'],
            'Portocaliu': [r'\bportocaliu\b', r'\borange\b'],
            'Coral': [r'\bcoral\b'],
            'Miezul Nopții': [r'\bmidnight\b'],
            'Stelar': [r'\bstarlight\b'],
        }

        text_lower = f"{translated_name} {description}".lower()
        color = ''
        for col, patterns in color_map.items():
            if any(re.search(p, text_lower) for p in patterns):
                color = col
                break

        # 3. Detectare 120Hz/90Hz din titlu original + descriere
        refresh_rate = ''
        combined_lower = f"{original_name} {description}".lower()
        if '120hz' in combined_lower or '120 hz' in combined_lower:
            refresh_rate = '120Hz'
        elif '90hz' in combined_lower or '90 hz' in combined_lower:
            refresh_rate = '90Hz'

        # 4. Titlu WebGSM: [Nume Piesă] [Model] [Calitate] [Brand] [Culoare]
        parts = []
        seen = set()
        for part in [tip_ro, pa_model, pa_calitate, pa_brand_piesa, color]:
            if part and (part not in seen):
                parts.append(part)
                seen.add(part)
        longtail = ' '.join(parts)
        return self.curata_text(longtail)

    def remove_diacritics(self, text):
        """DEZACTIVAT - Păstrăm diacriticele românești corecte.
        Apelează fix_romanian_diacritics() în loc să elimine diacriticele."""
        return self.fix_romanian_diacritics(text)

    def fix_romanian_diacritics(self, text):
        """
        Convertește diacriticele cu sedilă în cele corecte cu virgulă.
        Google Translate uneori returnează sedilă (ş, ţ) în loc de virgulă (ș, ț).

        Corectări:
          ş (U+015F, s with cedilla) → ș (U+0219, s with comma below)
          ţ (U+0163, t with cedilla) → ț (U+021B, t with comma below)
          Ş (U+015E) → Ș (U+0218)
          Ţ (U+0162) → Ț (U+021A)
        """
        if not text:
            return text

        # Sedilă → Virgulă (lowercase)
        text = text.replace('\u015f', '\u0219')  # ş → ș
        text = text.replace('\u0163', '\u021b')  # ţ → ț

        # Sedilă → Virgulă (uppercase)
        text = text.replace('\u015e', '\u0218')  # Ş → Ș
        text = text.replace('\u0162', '\u021a')  # Ţ → Ț

        return text

    def fix_common_translation_errors(self, text):
        """
        Corectează traduceri greșite frecvente: tester (dispozitiv) e tradus uneori „testator”.
        testator = persoana care face testament; tester = dispozitiv de testare.
        """
        if not text or not isinstance(text, str):
            return text
        # Tester (dispozitiv) nu se traduce „testator”
        text = re.sub(r'\btestator\b', 'tester', text, flags=re.IGNORECASE)
        text = re.sub(r'\bTestator\b', 'Tester', text)
        return text

    def curata_text(self, text):
        """
        Curăță text: diacritice ș/ț (sedilă → virgulă), corectări traduceri (testator→tester), elimină spații duble.
        """
        if not text:
            return text
        text = self.fix_romanian_diacritics(text)
        text = self.fix_common_translation_errors(text)
        return re.sub(r'\s+', ' ', text).strip()

    def normalize_text(self, text):
        """
        Pentru nume fișiere SEO: elimină diacritice (ăâîșț → aaist),
        lowercase, non-alfanumeric → cratimă, fără cratime duble/la capete.
        """
        if not text or not str(text).strip():
            return ''
        t = str(text).strip().lower()
        # Diacritice românești → litere simple (ș ț ă â î)
        diac = {'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't', 'ş': 's', 'ţ': 't'}
        for d, r in diac.items():
            t = t.replace(d, r)
        # Non-alfanumeric → cratimă
        t = re.sub(r'[^a-z0-9]+', '-', t)
        # Cratime duble și de la capete
        t = re.sub(r'-+', '-', t).strip('-')
        return t

    def generate_seo_filename(self, title, ext, index=None):
        """
        Nume fișier SEO din titlul tradus: normalizează și returnează {titlu-normalizat}.{ext}.
        Dacă index este dat, returnează {titlu-normalizat}-{index}.{ext} (ex: ecran-iphone-17-1.webp).
        """
        ext = (ext or 'jpg').lstrip('.')
        base = self.normalize_text(title) if title else 'produs'
        if not base:
            base = 'produs'
        if index is not None:
            base = f"{base}-{index}"
        return f"{base}.{ext}"

    # ⚡ Cache traduceri - evită apeluri duplicate la Google Translate
    _translation_cache = {}

    def _looks_like_slug(self, text):
        """True dacă textul arată ca un slug URL (multe cratime, puține spații)."""
        if not text or len(text) < 4:
            return False
        hyphens = text.count('-')
        spaces = text.count(' ')
        # Slug tip: ibridge-a3-tail-plug-comprehensive-analysis-tester-qianli
        return hyphens >= 2 and spaces <= 1

    def translate_via_ollama(self, text, prompt_type='title'):
        """Traduce/adaptează text prin API Ollama local (pentru slug-uri sau Componentă)."""
        base_url = self.config.get('OLLAMA_URL', '').strip()
        if not base_url:
            return None
        model = self.config.get('OLLAMA_MODEL', 'llama3.2') or 'llama3.2'
        url = f"{base_url.rstrip('/')}/api/generate"
        if prompt_type == 'title':
            prompt = (
                "Translate to Romanian and adapt as a short product name (2-6 words). "
                "Output ONLY the Romanian text, nothing else, no quotes.\n\nEnglish: "
            )
        else:
            prompt = "Translate to Romanian. Output ONLY the Romanian text, nothing else.\n\nEnglish: "
        prompt += text.strip()
        timeout_sec = self.config.get('OLLAMA_TIMEOUT', 300)
        try:
            r = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=min(90, timeout_sec)
            )
            r.raise_for_status()
            out = r.json().get("response", "").strip()
            if out:
                out = self.fix_romanian_diacritics(out)
                return out
        except Exception as e:
            self.log(f"⚠ Ollama: {e}", "WARNING")
        return None

    def ollama_generate_product_fields(self, source_url, name_en, description_en, pa_model, pa_calitate, pa_brand_piesa, pa_tehnologie, tags_en=''):
        """
        Generează toate câmpurile text pentru CSV (nume, descriere, SEO, tag-uri) prin Ollama.
        source_url este DOAR pentru context – nu se modifică. tags_en = tag-uri de pe pagină (EN), traduse în TAGS_RO.
        Returnează dict: name_ro, short_desc_ro, desc_ro, seo_title, seo_desc, focus_kw, tip_produs, tags_ro.
        """
        base_url = self.config.get('OLLAMA_URL', '').strip()
        if not base_url:
            return None
        model = self.config.get('OLLAMA_MODEL', 'llama3.2') or 'llama3.2'
        url = f"{base_url.rstrip('/')}/api/generate"
        desc_full = (description_en or '')[:2800].replace('\n', ' ')
        tags_line = f"Product tags from source (EN): {tags_en.strip()[:300]}" if tags_en and tags_en.strip() else "No tags from source."
        prompt = f"""You are a product data specialist for a Romanian e-commerce site (WebGSM). Write ONLY in correct, fluent Romanian (gramatică corectă).

SOURCE PRODUCT URL (read-only): {source_url}

Product name (EN): {name_en}
Description/specs from source (EN): {desc_full}
{tags_line}
Attributes: Model={pa_model or '-'}, Calitate={pa_calitate or '-'}, Brand={pa_brand_piesa or '-'}, Tehnologie={pa_tehnologie or '-'}

Translate and adapt for our CSV. Keep the structure of the description (e.g. Net Weight, Compatibility, Product size, Speed) when present. Important: for diagnostic/testing devices use "tester" in Romanian (dispozitiv de testare), never "testator" (persoana care face testament). Output ONLY these lines, one per line:
NAME_RO: <one line, product name in Romanian, SEO-friendly, grammatically correct>
SHORT_DESC_RO: <one line, short description in Romanian, max 160 chars, fluent>
DESC_RO: <full description in Romanian; KEEP structure (Greutate netă, Compatibilitate, Dimensiuni, Viteză etc.); use | for line breaks; grammatically correct>
SEO_TITLE: <one line, max 60 chars>
SEO_DESC: <one line, max 155 chars>
FOCUS_KW: <one short phrase for SEO>
TIP_PRODUS: <exactly one: Baterie, Ecran, Conector Încărcare, Cameră Spate, Șurub, Șurubelniță, Componentă, Flex, Carcasă, Difuzor, Buton, Garnitură, Tester, Folie protecție>
TAGS_RO: <if tags from source were given, translate them to fluent Romanian (e.g. wholesale screwdrivers -> șurubelnițe en-gros); otherwise suggest max 6 short tags; comma-separated, max 8 tags, grammatically correct Romanian>"""
        timeout_sec = self.config.get('OLLAMA_TIMEOUT', 300)
        for attempt in range(2):
            try:
                r = requests.post(
                    url,
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=timeout_sec
                )
                r.raise_for_status()
                out = r.json().get("response", "").strip()
                if not out:
                    return None
                out = self.fix_romanian_diacritics(out)
                result = {}
                desc_ro_lines = []
                in_desc_ro = False
                key_prefixes = ("NAME_RO:", "SHORT_DESC_RO:", "DESC_RO:", "SEO_TITLE:", "SEO_DESC:", "FOCUS_KW:", "TIP_PRODUS:", "TAGS_RO:")
                for line in out.splitlines():
                    line_stripped = line.strip()
                    if line_stripped.startswith("NAME_RO:"):
                        in_desc_ro = False
                        result["name_ro"] = line_stripped[8:].strip()
                    elif line_stripped.startswith("SHORT_DESC_RO:"):
                        in_desc_ro = False
                        result["short_desc_ro"] = line_stripped[14:].strip()[:160]
                    elif line_stripped.startswith("DESC_RO:"):
                        in_desc_ro = True
                        desc_ro_lines = [line_stripped[8:].strip()]
                    elif in_desc_ro and not any(line_stripped.startswith(p) for p in key_prefixes if p != "DESC_RO:"):
                        desc_ro_lines.append(line_stripped)
                    elif line_stripped.startswith("SEO_TITLE:"):
                        in_desc_ro = False
                        result["seo_title"] = line_stripped[10:].strip()[:60]
                    elif line_stripped.startswith("SEO_DESC:"):
                        result["seo_desc"] = line_stripped[9:].strip()[:160]
                    elif line_stripped.startswith("FOCUS_KW:"):
                        result["focus_kw"] = line_stripped[9:].strip()
                    elif line_stripped.startswith("TIP_PRODUS:"):
                        result["tip_produs"] = line_stripped[11:].strip()
                    elif line_stripped.startswith("TAGS_RO:"):
                        result["tags_ro"] = line_stripped[8:].strip()[:500]
                if desc_ro_lines:
                    result["desc_ro"] = " ".join(desc_ro_lines).replace("|", "\n").strip()[:3000]
                if result.get("name_ro"):
                    return result
                return None
            except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                self.log(f"⚠ Ollama timeout ({timeout_sec}s)" + (" – reîncerc..." if attempt == 0 else f": {e}"), "WARNING")
                if attempt == 1:
                    return None
            except Exception as e:
                self.log(f"⚠ Ollama (câmpuri produs): {e}", "WARNING")
                return None
        return None

    def translate_text(self, text, source='en', target='ro'):
        """Traduce text folosind Google Translate (cu cache + diacritice corecte)."""
        if not text or not text.strip():
            return text

        # Verifică cache-ul (aceleași texte nu se mai traduc de două ori)
        cache_key = f"{source}:{target}:{text.strip()[:200]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            translator = GoogleTranslator(source=source, target=target)
            # Împarte text în bucăți dacă e prea lung (max 5000 caractere)
            max_length = 4500
            if len(text) <= max_length:
                translated = translator.translate(text)
            else:
                # Împarte în paragrafe și traduce separat
                chunks = []
                current_chunk = ""

                for paragraph in text.split('\n'):
                    if len(current_chunk) + len(paragraph) + 1 <= max_length:
                        current_chunk += paragraph + '\n'
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = paragraph + '\n'

                if current_chunk:
                    chunks.append(current_chunk)

                # Traduce fiecare bucată
                translated_chunks = []
                for chunk in chunks:
                    translated_chunks.append(translator.translate(chunk))

                translated = '\n'.join(translated_chunks)

            # Corectează sedilă → virgulă (ş→ș, ţ→ț) pentru română
            if target == 'ro':
                translated = self.fix_romanian_diacritics(translated)

            # Salvează în cache pentru reutilizare
            self._translation_cache[cache_key] = translated
            return translated

        except Exception as e:
            self.log(f"⚠ Eroare traducere: {e}", "WARNING")
            return text  # Returnează textul original dacă traducerea eșuează

    def _tags_look_like_nav(self, tags_str):
        """True dacă tag-urile par a fi din meniu/navigare/footer (Eroare, Europa, Despre, Servicii...)."""
        if not tags_str or not tags_str.strip():
            return False
        nav_phrases = (
            'eroare', 'europa', 'statele unite', 'canada', 'regatul unit', 'despre', 'servicii',
            'mărcile noastre', 'asistență', 'bună ziua', 'contact', 'error', 'europe',
            'united states', 'united kingdom', 'about', 'support', 'hello', 'our brands'
        )
        low = tags_str.lower()
        hits = sum(1 for p in nav_phrases if p in low)
        return hits >= 2

    def _generate_fallback_tags(self, product_name_ro, categories, pa_model, pa_calitate, pa_tehnologie, tip_ro):
        """Generează tag-uri relevante din nume, categorie și atribute (când Ollama lipsește sau tag-urile sunt invalide)."""
        parts = []
        name = (product_name_ro or '').strip()
        if name:
            # Cuvinte relevante din nume (ex: Ecran iPhone 15 Pro Max Aftermarket → ecran, iphone 15 pro max, aftermarket)
            for word in re.split(r'[\s,]+', name):
                w = word.strip()
                if len(w) >= 2 and len(w) <= 40 and w.lower() not in ('si', 'și', 'cu', 'pentru', 'din', 'de', 'la'):
                    parts.append(w)
        if categories:
            # Din "Piese > Piese iPhone > Ecrane" luăm "Piese", "iPhone", "Ecrane"
            for chunk in re.split(r'\s*>\s*', categories):
                for w in re.split(r'[\s,]+', chunk):
                    w = w.strip()
                    if w and len(w) >= 2 and w not in ('Piese', 'Accesorii', 'Unelte') and w not in parts:
                        parts.append(w)
        if pa_model and pa_model not in parts:
            parts.append(pa_model)
        if pa_calitate and pa_calitate not in ('Aftermarket', '') and pa_calitate not in parts:
            parts.append(pa_calitate)
        if pa_tehnologie and pa_tehnologie not in parts:
            parts.append(pa_tehnologie)
        if tip_ro and tip_ro not in parts:
            parts.append(tip_ro)
        # Unic, max 10 tag-uri
        seen = set()
        out = []
        for p in parts:
            key = p.lower().strip()
            if key and key not in seen and len(out) < 10:
                seen.add(key)
                out.append(p)
        return ', '.join(out) if out else (tip_ro or 'piese')

    def export_to_csv(self, products_data, filename="export_produse.csv"):
        """Exportă produsele în CSV format WebGSM cu atribute, ACF meta și SEO Rank Math"""
        import csv

        try:
            csv_path = self._script_dir / "data" / filename
            self.log(f"📄 Creez fișier CSV WebGSM: {csv_path}", "INFO")
            self.log(f"⏳ Procesez {len(products_data)} produse cu upload imagini pe WordPress...", "INFO")

            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = [
                    'ID', 'Type', 'SKU', 'Name', 'Published', 'Is featured?',
                    'Visibility in catalog', 'Short description', 'Description',
                    'Tax status', 'Tax class', 'In stock?', 'Stock', 'Regular price',
                    'Categories', 'Tags', 'Images', 'Parent',
                    # ATRIBUTE WOOCOMMERCE (4 atribute x 4 coloane)
                    'Attribute 1 name', 'Attribute 1 value(s)', 'Attribute 1 visible', 'Attribute 1 global',
                    'Attribute 2 name', 'Attribute 2 value(s)', 'Attribute 2 visible', 'Attribute 2 global',
                    'Attribute 3 name', 'Attribute 3 value(s)', 'Attribute 3 visible', 'Attribute 3 global',
                    'Attribute 4 name', 'Attribute 4 value(s)', 'Attribute 4 visible', 'Attribute 4 global',
                    # ACF META
                    'meta:gtin_ean', 'meta:sku_furnizor', 'meta:furnizor_activ',
                    'meta:pret_achizitie', 'meta:locatie_stoc', 'meta:garantie_luni',
                    'meta:coduri_compatibilitate', 'meta:ic_movable', 'meta:truetone_support',
                    'meta:source_url',
                    # SEO RANK MATH
                    'meta:rank_math_title', 'meta:rank_math_description', 'meta:rank_math_focus_keyword'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)

                writer.writeheader()

                ollama_ok = bool(self.config.get('OLLAMA_URL'))
                if ollama_ok:
                    self.log(f"🤖 Ollama activ: {self.config.get('OLLAMA_URL')} – generează toate câmpurile (nume, descriere, SEO)", "INFO")
                else:
                    self.log("🌍 Ollama neconfigurat (OLLAMA_URL gol în .env) – folosesc Google Translate + logică internă", "INFO")

                for idx, product in enumerate(products_data, 1):
                    self.log(f"🔄 Proceseaza produs {idx}/{len(products_data)}: {product.get('name', 'N/A')}", "INFO")

                    # meta:source_url rămâne MEREU din scrape (link MobileSentrix) – nu se modifică niciodată
                    source_url = product.get('source_url', '')

                    # Atribute din scrape (folosite și de Ollama ca context)
                    clean_name = product.get('name', 'N/A')
                    if clean_name.endswith(' Copy'):
                        clean_name = clean_name[:-5]
                    pa_model = product.get('pa_model', '')
                    pa_calitate = product.get('pa_calitate', 'Aftermarket')
                    pa_brand_piesa = product.get('pa_brand_piesa', '')
                    pa_tehnologie = product.get('pa_tehnologie', '')
                    description_for_longtail = product.get('description', '')

                    ollama_data = None
                    if ollama_ok:
                        ollama_data = self.ollama_generate_product_fields(
                            source_url, clean_name, description_for_longtail,
                            pa_model, pa_calitate, pa_brand_piesa, pa_tehnologie,
                            product.get('tags', '')
                        )
                    if ollama_data:
                        longtail_title = self.curata_text(ollama_data.get('name_ro', '')) or clean_name
                        tip_ro = ollama_data.get('tip_produs', 'Componentă')
                        clean_name_ro = longtail_title
                        self.log(f"   🤖 Ollama: Name={longtail_title[:50]}..., Tip={tip_ro}", "INFO")
                    else:
                        tip_ro = self._detect_tip_produs_ro(clean_name)
                        use_ollama_title = ollama_ok and (self._looks_like_slug(clean_name) or tip_ro == 'Componentă')
                        if use_ollama_title:
                            text_for_ollama = clean_name.replace('-', ' ')
                            clean_name_ro = self.translate_via_ollama(text_for_ollama, 'title')
                            if clean_name_ro is None:
                                clean_name_ro = self.translate_text(clean_name, source='en', target='ro')
                            else:
                                self.log(f"   🤖 Ollama (titlu): {clean_name} → {clean_name_ro}", "INFO")
                        else:
                            clean_name_ro = self.translate_text(clean_name, source='en', target='ro')
                            if clean_name_ro == clean_name and ollama_ok:
                                clean_name_ro = self.translate_via_ollama(clean_name, 'title') or clean_name_ro
                        if not use_ollama_title:
                            self.log(f"   🌍 Titlu tradus: {clean_name} → {clean_name_ro}", "INFO")
                        longtail_attrs = {
                            'pa_model': pa_model, 'pa_calitate': pa_calitate,
                            'pa_brand_piesa': pa_brand_piesa, 'pa_tehnologie': pa_tehnologie,
                            'original_name': clean_name,
                        }
                        longtail_title = self.build_longtail_title(clean_name_ro, description_for_longtail, longtail_attrs)
                    self.log(f"   📝 Titlu (Name CSV): {longtail_title[:60]}...", "INFO")

                    # ⚡ Upload PARALEL imagini pe WordPress (de la ~2min la ~30s)
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    image_urls = []
                    if product.get('images'):
                        # Redenumire imagini cu nume SEO (titlu tradus sau caracteristici produs)
                        seo_title = longtail_title if (longtail_title and len(self.normalize_text(longtail_title)) >= 3) else ' '.join(filter(None, [tip_ro, pa_model, pa_tehnologie, pa_calitate])) or 'produs'
                        images_dir = self._script_dir / "images"
                        for img_idx, img in enumerate(product['images']):
                            if isinstance(img, dict) and 'local_path' in img:
                                old_path = Path(img['local_path'])
                                if old_path.exists():
                                    ext = old_path.suffix.lstrip('.').lower() or 'jpg'
                                    new_name = self.generate_seo_filename(seo_title, ext, img_idx + 1)
                                    new_path = images_dir / new_name
                                    if old_path.resolve() != new_path.resolve() and new_name != old_path.name:
                                        try:
                                            if new_path.exists():
                                                new_path.unlink()
                                            old_path.rename(new_path)
                                            img['local_path'] = str(new_path)
                                            img['name'] = new_name
                                            self.log(f"   📁 Redenumit: {old_path.name} → {new_name}", "INFO")
                                        except Exception as e:
                                            self.log(f"   ⚠️ Redenumire {old_path.name}: {e}", "WARNING")
                        # Pregătește lista de imagini de uploadat
                        upload_tasks = []
                        fallback_urls = {}  # idx -> fallback URL
                        for img_idx, img in enumerate(product['images']):
                            img_path = None
                            if isinstance(img, dict):
                                if 'local_path' in img:
                                    img_path = img['local_path']
                            else:
                                img_path = str(img)

                            if img_path and Path(img_path).exists():
                                upload_tasks.append((img_idx, img_path))
                                if isinstance(img, dict) and 'src' in img:
                                    fallback_urls[img_idx] = img['src']
                            elif isinstance(img, dict) and 'src' in img:
                                # Nu există local, folosește URL direct
                                image_urls.append((img_idx, img['src']))

                        if upload_tasks:
                            self.log(f"   📤 Upload {len(upload_tasks)} imagini pe WordPress (paralel)...", "INFO")

                            def _upload_one(args):
                                img_idx, img_path = args
                                try:
                                    result = self.upload_image_to_wordpress(img_path)
                                    if result:
                                        wp_url = result.get('src') if isinstance(result, dict) else result
                                        return {'success': True, 'idx': img_idx, 'url': wp_url}
                                    else:
                                        fb = fallback_urls.get(img_idx, '')
                                        return {'success': False, 'idx': img_idx, 'url': fb}
                                except Exception as e:
                                    fb = fallback_urls.get(img_idx, '')
                                    return {'success': False, 'idx': img_idx, 'url': fb, 'error': str(e)}

                            # Upload paralel: 3 thread-uri (nu supraîncărcăm WordPress)
                            wp_results = []
                            with ThreadPoolExecutor(max_workers=3) as executor:
                                futures = {executor.submit(_upload_one, task): task for task in upload_tasks}
                                for future in as_completed(futures):
                                    res = future.result()
                                    if res['success']:
                                        wp_results.append((res['idx'], res['url']))
                                        self.log(f"   ✓ [{res['idx']+1}] Uploadat pe WordPress", "SUCCESS")
                                    elif res['url']:
                                        wp_results.append((res['idx'], res['url']))
                                        self.log(f"   ⚠ [{res['idx']+1}] Upload eșuat, URL original", "WARNING")
                                    else:
                                        self.log(f"   ✗ [{res['idx']+1}] Upload eșuat, fără fallback", "ERROR")

                            # Combină cu URL-urile directe și sortează după index
                            image_urls.extend(wp_results)

                        # Sortează după index și extrage doar URL-urile
                        image_urls.sort(key=lambda x: x[0])
                        image_urls = [url for _, url in image_urls]

                    # Limită nr. de link-uri (imagini deja pe site) în CSV – mai puține = import mai rapid
                    if len(image_urls) > MAX_IMAGES_IN_CSV:
                        image_urls = image_urls[:MAX_IMAGES_IN_CSV]
                        self.log(f"   📷 CSV: max {MAX_IMAGES_IN_CSV} imagini/produs (import mai rapid)", "INFO")

                    # Calculează preț vânzare RON: achiziție EUR → RON → adaos 40% → TVA 19%
                    price_eur = product['price']
                    # Preț achiziție în LEI cu TVA: EUR × 5.1 (curs) × 1.21 (TVA achiziție 21%)
                    curs_achizitie = 5.1
                    tva_achizitie = 1.21
                    pret_achizitie_lei_cu_tva = round(price_eur * curs_achizitie * tva_achizitie, 2)
                    if self.convert_price_var.get():
                        exchange_rate = float(self.exchange_rate_var.get())
                        price_ron = self.calculate_selling_price(
                            price_eur, exchange_rate=exchange_rate, markup=0.40, vat=0.19
                        )
                    else:
                        price_ron = price_eur

                    # Short description și Description: din Ollama dacă avem, altfel logică internă
                    if ollama_data:
                        short_description = self.curata_text(ollama_data.get('short_desc_ro', ''))[:160]
                        if not short_description:
                            short_description = f"{tip_ro}. Garanție inclusă. Livrare rapidă în toată România."
                    else:
                        clean_desc = product.get('description', '')[:500]
                        clean_desc = re.sub(r'https?://\S+', '', clean_desc).strip()
                        clean_desc_ro_tr = self.translate_text(clean_desc, source='en', target='ro')
                        self.log(f"   🌍 Descriere tradusă: {len(clean_desc)} → {len(clean_desc_ro_tr)} caractere", "INFO")
                        short_desc_parts = [tip_ro]
                        if pa_model:
                            short_desc_parts.append(pa_model)
                        if pa_tehnologie:
                            short_desc_parts.append(pa_tehnologie)
                        if pa_calitate and pa_calitate != 'Aftermarket':
                            short_desc_parts.append(f"calitate {pa_calitate}")
                        short_desc_intro = ' '.join(short_desc_parts)
                        short_description = f"{short_desc_intro}. Garanție inclusă. Livrare rapidă în toată România."
                        short_description = self.curata_text(short_description)[:160]

                    # Description: doar textul descrierii, fără tabel (Calitate/Model/Brand sunt deja în atribute și detalii tehnice pe site)
                    # Format: bullet list (ul/li) dacă sunt mai multe linii, altfel paragraf
                    if ollama_data and ollama_data.get('desc_ro'):
                        raw_desc = self.curata_text(ollama_data['desc_ro'])
                        # Linii: din | sau \n
                        lines = [s.strip() for s in re.split(r'[\n|]+', raw_desc) if s.strip()]
                        if len(lines) >= 2:
                            # Listă cu bullet-uri
                            clean_desc_ro = '<ul>\n' + '\n'.join('<li>' + html.escape(line) + '</li>' for line in lines) + '\n</ul>'
                        elif lines:
                            clean_desc_ro = '<p>' + html.escape(lines[0]) + '</p>'
                        else:
                            clean_desc_ro = '<p>' + html.escape(raw_desc[:2000]) + '</p>'
                    else:
                        # Fără Ollama: descriere din date – dacă are mai multe linii, listă cu bullet-uri
                        raw_fallback = (product.get('description', '') or '')[:2000]
                        lines_fb = [s.strip() for s in re.split(r'[\n|]+', raw_fallback) if s.strip()]
                        if len(lines_fb) >= 2:
                            clean_desc_ro = '<ul>\n' + '\n'.join('<li>' + html.escape(line) + '</li>' for line in lines_fb) + '\n</ul>'
                        else:
                            clean_desc_ro = '<p>' + html.escape(raw_fallback) + '</p>'

                    # SKU: folosește WebGSM SKU generat (WG-ECR-IP13-JK-01)
                    sku_value = product.get('webgsm_sku', product.get('sku', 'N/A'))

                    # EAN/GTIN: cod numeric 12-14 cifre de la MobileSentrix (meta:gtin_ean)
                    ean_real = str(product.get('ean_real', '')).strip()
                    sku_furn = str(product.get('sku_furnizor', '')).strip()
                    ean_value = ''
                    for raw in (ean_real, sku_furn):
                        if not raw:
                            continue
                        s = raw
                        if not s.isdigit():
                            try:
                                s = str(int(float(s)))
                            except (ValueError, TypeError):
                                s = re.sub(r'\D', '', s)
                        if 12 <= len(s) <= 14:
                            ean_value = s
                            break
                        if 8 <= len(s) <= 14 and not ean_value:
                            ean_value = s
                    if not ean_value and (ean_real or sku_furn):
                        s = re.sub(r'\D', '', ean_real or sku_furn)
                        if s:
                            ean_value = s

                    # SKU furnizor: codul MobileSentrix (ex: 107182127516)
                    sku_furnizor = product.get('sku_furnizor', product.get('sku', ''))

                    # Categorii: Titlu > URL slug > Descriere > Taguri; folosit și pentru garanție
                    manual_code = product.get('manual_category_code')
                    url_slug = (product.get('source_url') or '').rstrip('/').split('/')[-1] or ''
                    categories = self.get_woo_category(
                        clean_name, tip_ro, manual_code=manual_code,
                        description=product.get('description', '')[:500],
                        url_slug=url_slug,
                        tags=product.get('tags', '')
                    )
                    # Detectează garanția (număr luni)
                    warranty_text = self.detect_warranty(clean_name_ro, categories)
                    # Convertește "12 luni" -> 12, "6 luni" -> 6, etc.
                    warranty_months = re.search(r'(\d+)', warranty_text)
                    warranty_months = warranty_months.group(1) if warranty_months else '12'
                    self.log(f"   ⏱️ Garantie: {warranty_months} luni", "INFO")

                    # Disponibilitate și stoc (din scrape: in_stock / preorder / out_of_stock)
                    availability = product.get('availability', 'in_stock')
                    if availability == 'in_stock':
                        in_stock = '1'
                        locatie_stoc = product.get('locatie_stoc', 'depozit_central')
                    elif availability == 'preorder':
                        in_stock = '0'
                        locatie_stoc = 'precomanda'
                    else:
                        in_stock = '0'
                        locatie_stoc = 'indisponibil'
                    # Reparare stoc: dacă Stock > 0, In stock? = 1 (permite vânzarea)
                    try:
                        stock_val = product.get('stock', '100')
                        if int(stock_val) > 0:
                            in_stock = '1'
                    except (ValueError, TypeError):
                        pass

                    # Combină toate imaginile
                    all_images = ', '.join(image_urls) if image_urls else ''

                    # Categorii deja calculate mai sus (cu description, url_slug, tags)

                    # SEO Rank Math: din Ollama dacă avem, altfel funcții interne
                    if ollama_data:
                        seo_title = self.curata_text(ollama_data.get('seo_title', ''))[:60]
                        seo_description = self.curata_text(ollama_data.get('seo_desc', ''))[:160]
                        seo_keyword = self.curata_text(ollama_data.get('focus_kw', ''))
                        if not seo_title:
                            seo_title = longtail_title[:60]
                    else:
                        original_name = product.get('name', '')
                        seo_title = self.generate_seo_title(original_name, pa_model, pa_brand_piesa, pa_tehnologie)
                        seo_description = self.generate_seo_description(original_name, pa_model, pa_brand_piesa, pa_tehnologie, pa_calitate)
                        seo_keyword = self.generate_focus_keyword(original_name, pa_model)
                    self.log(f"   🔍 SEO: {seo_title[:60]}...", "INFO")

                    # IC Movable & TrueTone: mereu OFF (0) la upload – utilizatorul setează manual "Da" dacă e cazul
                    # ACF: 0 = Nu / off, 1 = Da / on
                    ic_movable_val = '0'
                    truetone_val = '0'

                    # Tags: din Ollama (TAGS_RO); dacă lipsesc sau sunt „nav/footer”, generăm din nume/categorie
                    if ollama_data and ollama_data.get('tags_ro'):
                        tags_value = self.curata_text(ollama_data['tags_ro'].strip())[:500]
                    else:
                        tags_value = product.get('tags', '')
                        if tags_value:
                            tags_value = self.translate_text(tags_value, source='en', target='ro')
                        # Detectare tag-uri greșite (navigare/footer: Eroare, Europa, Despre, Servicii...)
                        if self._tags_look_like_nav(tags_value):
                            tags_value = ''
                        if not tags_value or not tags_value.strip():
                            tags_value = self._generate_fallback_tags(
                                longtail_title, categories, pa_model, pa_calitate, pa_tehnologie, tip_ro
                            )

                    row = {
                        'ID': '',
                        'Type': 'simple',
                        'SKU': sku_value,
                        'Name': longtail_title,
                        'Published': '0',  # Draft/Pending – utilizatorul publică manual după review
                        'Is featured?': '0',
                        'Visibility in catalog': 'visible',
                        'Short description': short_description,
                        'Description': clean_desc_ro,
                        'Tax status': 'taxable',
                        'Tax class': '',
                        'In stock?': in_stock,
                        'Stock': product.get('stock', '100'),
                        'Regular price': f"{price_ron:.2f}",
                        'Categories': categories,
                        'Tags': tags_value,
                        'Images': all_images,
                        'Parent': '',
                        # ATRIBUT 1: Model Compatibil
                        'Attribute 1 name': 'Model Compatibil',
                        'Attribute 1 value(s)': pa_model,
                        'Attribute 1 visible': '1',
                        'Attribute 1 global': '1',
                        # ATRIBUT 2: Calitate
                        'Attribute 2 name': 'Calitate',
                        'Attribute 2 value(s)': pa_calitate,
                        'Attribute 2 visible': '1',
                        'Attribute 2 global': '1',
                        # ATRIBUT 3: Brand Piesa
                        'Attribute 3 name': 'Brand Piesa',
                        'Attribute 3 value(s)': pa_brand_piesa,
                        'Attribute 3 visible': '1',
                        'Attribute 3 global': '1',
                        # ATRIBUT 4: Tehnologie
                        'Attribute 4 name': 'Tehnologie',
                        'Attribute 4 value(s)': pa_tehnologie,
                        'Attribute 4 visible': '1',
                        'Attribute 4 global': '1',
                        # ACF META
                        'meta:gtin_ean': ean_value,
                        'meta:sku_furnizor': sku_furnizor,
                        'meta:furnizor_activ': product.get('furnizor_activ', 'mobilesentrix'),
                        'meta:pret_achizitie': f"{pret_achizitie_lei_cu_tva:.2f}",
                        'meta:locatie_stoc': locatie_stoc,
                        'meta:garantie_luni': warranty_months,
                        'meta:coduri_compatibilitate': product.get('coduri_compatibilitate', ''),
                        'meta:ic_movable': ic_movable_val,
                        'meta:truetone_support': truetone_val,
                        'meta:source_url': product.get('source_url', ''),  # MEREU din scrape (link MobileSentrix) – nu se modifică
                        # SEO RANK MATH
                        'meta:rank_math_title': seo_title[:60],
                        'meta:rank_math_description': seo_description[:160],
                        'meta:rank_math_focus_keyword': seo_keyword,
                    }
                    writer.writerow(row)

            self.log(f"✓ CSV WebGSM creat cu succes: {csv_path}", "SUCCESS")
            self.log(f"   📊 Total produse exportate: {len(products_data)}", "INFO")
            self.log(f"   📋 Coloane CSV: {len(fieldnames)} (atribute + ACF + SEO)", "INFO")
            if len(products_data) > 30:
                self.log(f"   💡 Import mai rapid pe site: importă în batch-uri (ex. 30–50 produse/CSV) sau mărește max_execution_time pe server.", "INFO")
            return str(csv_path)

        except Exception as e:
            self.log(f"✗ Eroare creare CSV: {e}", "ERROR")
            import traceback
            self.log(f"   Traceback: {traceback.format_exc()}", "ERROR")
            return None
    
    def scrape_product(self, ean):
        """Extrage date produs de pe MobileSentrix și descarcă imagini local
        Acceptă: EAN, SKU sau LINK DIRECT la produs"""
        try:
            import re  # ⬅️ IMPORTANT: Import la ÎNCEPUTUL funcției!
            
            product_link = None
            product_id = ean  # Va fi folosit pentru nume fișiere
            
            # Headers pentru toate request-urile
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
                'Referer': 'https://www.mobilesentrix.eu/'
            }
            
            # PASUL 1: Detectează dacă input-ul e link direct
            if ean.startswith('http://') or ean.startswith('https://'):
                # E link direct! 🎯
                product_link = ean
                # Extrage un ID simplu din URL pentru nume fișiere (ultimul segment URL)
                product_id = ean.rstrip('/').split('/')[-1][:50]  # Max 50 caractere
                # Curăță caracterele invalide pentru Windows filenames
                product_id = re.sub(r'[<>:"/\\|?*]', '_', product_id)
                self.log(f"   ✓ Link direct detectat!", "INFO")
                self.log(f"      URL: {product_link[:80]}...", "INFO")
                self.log(f"      ID produs: {product_id}", "INFO")
                
                # ⬇️ IMPORTANT: Descarcă pagina produsului!
                self.log(f"   🔄 Se descarcă pagina produsului...", "INFO")
                response = requests.get(product_link, headers=headers, timeout=30)
                response.raise_for_status()
                product_soup = BeautifulSoup(response.content, 'html.parser')
            # PASUL 1b: Detectează dacă e SKU (12-13 cifre consecutive)
            elif re.match(r'^\d{10,14}$', ean.strip()):
                # E SKU/EAN - MobileSentrix acceptă SKU în URL direct!
                # Caută produsul pe baza SKU în pagina de căutare
                search_sku = ean.strip()
                search_url = f"https://www.mobilesentrix.eu/catalogsearch/result/?q={search_sku}"
                self.log(f"   🔍 Căutare produs cu SKU: {search_sku}", "INFO")
                
                response = requests.get(search_url, headers=headers, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # ===== DEBUG: Salvează HTML pentru inspecție =====
                debug_file = self._script_dir / "logs" / f"debug_search_{search_sku}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                self.log(f"   📝 HTML căutare salvat: {debug_file}", "INFO")
                
                # Găsește primul produs valid din rezultate
                product_links = soup.select('a.product-item-link')
                
                if not product_links:
                    self.log(f"   ✗ Nu am găsit produse pentru SKU {search_sku}", "ERROR")
                    return None
                
                # Folosește primul link
                product_link = product_links[0].get('href')
                product_id = search_sku  # Folosim SKU-ul ca ID pentru fișiere
                
                if not product_link:
                    self.log(f"   ✗ Link produs invalid", "ERROR")
                    return None
                
                self.log(f"   ✓ Produs găsit! Link: {product_link[:80]}...", "INFO")
                
                # ⬇️ IMPORTANT: Descarcă pagina produsului!
                self.log(f"   🔄 Se descarcă pagina produsului...", "INFO")
                response = requests.get(product_link, headers=headers, timeout=30)
                response.raise_for_status()
                product_soup = BeautifulSoup(response.content, 'html.parser')
            else:
                # E text generic EAN/SKU - trebuie să căutam
                
                response = requests.get(search_url, headers=headers, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # ===== DEBUG: Salvează HTML pentru inspecție =====
                debug_file = self._script_dir / "logs" / f"debug_search_{ean}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                self.log(f"   📝 HTML salvat în: {debug_file}", "INFO")
                
                # Căuta orice link-uri de produs
                all_product_links = []
                
                # Căută cu selectorii specifici pentru produse
                product_selectors = [
                    'a.product-item-link',
                    'a.product.photo',
                    'a[data-product-id]',
                    'a[href*="/product/"]',
                    'a[href*="/catalogsearch/result/"]'
                ]
                
                for selector in product_selectors:
                    found = soup.select(selector)
                    if found:
                        self.log(f"   Selector '{selector}' a găsit {len(found)} link-uri", "INFO")
                        all_product_links.extend(found)
                
                # Elimină duplicatele și filtrează
                unique_links = []
                seen_hrefs = set()
                for link in all_product_links:
                    href = link.get('href', '')
                    if href and href not in seen_hrefs and 'mobilesentrix.eu' in href:
                        seen_hrefs.add(href)
                        unique_links.append(link)
                
                self.log(f"   🔎 Total link-uri găsite: {len(unique_links)}", "INFO")
                
                if not unique_links:
                    # ❌ NU am găsit nimic
                    self.log(f"   ⚠️ NU AM GĂSIT PRODUSUL cu EAN/SKU {ean} pe MobileSentrix!", "WARNING")
                    self.log(f"   💡 SOLUȚII:", "INFO")
                    self.log(f"      1. Copiază LINK DIRECT din MobileSentrix", "INFO")
                    self.log(f"      2. Pune link-ul în sku_list.txt (în loc de EAN)", "INFO")
                    self.log(f"      3. Programul va extrage datele direct!", "INFO")
                    return None
                
                # Folosește primul link valid
                product_link = unique_links[0]['href']
                self.log(f"   ✓ Link produs găsit: {product_link}", "INFO")
                
                # ⬇️ IMPORTANT: Descarcă pagina produsului!
                self.log(f"   🔄 Se descarcă pagina produsului...", "INFO")
                response = requests.get(product_link, headers=headers, timeout=30)
                response.raise_for_status()
                product_soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrage ID produs intern (230473) - unic pe MobileSentrix
            product_id_internal = None
            # Caută în variabila JavaScript: var magicToolboxProductId = 230473;
            script_content = str(product_soup)
            id_match = re.search(r'var\s+magicToolboxProductId\s*=\s*(\d+)', script_content)
            if id_match:
                product_id_internal = id_match.group(1)
                self.log(f"   ✓ ID produs intern găsit: {product_id_internal}", "INFO")
            
            # Căută și în atribut data-product-id
            if not product_id_internal:
                id_elem = product_soup.select_one('[data-product-id], input[name="product"][value]')
                if id_elem:
                    product_id_internal = id_elem.get('value') or id_elem.get('data-product-id')
                    if product_id_internal:
                        self.log(f"   ✓ ID produs din atribut: {product_id_internal}", "INFO")
            
            # Salvează HTML pentru SKU extraction din JavaScript
            product_page_html = str(product_soup)
            
            # ===== DEBUG: Salvează HTML produsului =====
            debug_product_file = self._script_dir / "logs" / f"debug_product_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(debug_product_file, 'w', encoding='utf-8') as f:
                f.write(product_soup.prettify())
            self.log(f"   📝 HTML produs salvat: {debug_product_file}", "INFO")
            
            # Extrage nume produs - MULTIPLI SELECTORII
            product_name = None
            name_selectors = [
                '.page-title span',
                'h1.page-title',
                'h1[itemprop="name"]',
                '.product-name',
                'h1',
                '.product-info-main h1'
            ]
            
            for selector in name_selectors:
                name_elem = product_soup.select_one(selector)
                if name_elem:
                    product_name = name_elem.text.strip()
                    self.log(f"   ✓ Nume găsit cu: {selector}", "INFO")
                    break
            
            if not product_name:
                product_name = f"Produs {ean}"
                self.log(f"   ⚠️ NU am găsit nume produs - folosesc placeholder", "WARNING")
            
            # Curăță numele de text garbage și caractere nevalide
            import re
            # Elimină "Copy", "EAN:", și alte text nevrut
            product_name = re.sub(r'\s*\bCopy\b\s*', '', product_name)
            product_name = re.sub(r'\s*\bEAN:.*', '', product_name)
            product_name = re.sub(r'\s*\bSKU:.*', '', product_name)
            product_name = re.sub(r'\s+', ' ', product_name)  # Normalizează spații multiple
            product_name = product_name.strip()
            
            # Extrage preț (EUR) - MULTIPLI SELECTORII
            price = 0.0
            price_selectors = [
                '.price-wrapper .price',
                '.product-info-price .price',
                'span[data-price-type="finalPrice"]',
                '.price-box .price',
                '.product-price .price',
                'span.price',
                '[itemprop="price"]'
            ]
            
            for selector in price_selectors:
                price_elem = product_soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.text.strip()
                    # Extrage doar numerele și convertește la float
                    import re
                    price_match = re.search(r'[\d,\.]+', price_text.replace(',', '.'))
                    if price_match:
                        price = float(price_match.group(0))
                        self.log(f"   ✓ Preț găsit cu: {selector}", "INFO")
                        break
            
            if price == 0.0:
                self.log(f"   ⚠️ NU am găsit preț - folosesc 0.00", "WARNING")
            
            self.log(f"   📦 Nume: {product_name}", "INFO")
            self.log(f"   💶 Preț: {price:.2f} EUR", "INFO")
            
            # Extrage descriere
            description = ""
            desc_selectors = [
                '.product.attribute.description .value',
                '.product-description',
                '[itemprop="description"]',
                '.product-info-description'
            ]
            
            for desc_sel in desc_selectors:
                desc_elem = product_soup.select_one(desc_sel)
                if desc_elem:
                    description = desc_elem.get_text(separator='\n', strip=True)
                    if description and len(description) > 30:
                        break

            # Fallback: secțiunea "Product Description" cu listă (bullet points) – ex. iBridge, Qianli
            if not description or len(description) < 80:
                for elem in product_soup.find_all(string=re.compile(r'Product\s+Description', re.I)):
                    parent = elem.find_parent(['div', 'section', 'article'])
                    if not parent:
                        parent = elem.find_parent()
                    if parent:
                        # Caută listă ul/ol cu li în același bloc
                        ul = parent.find(['ul', 'ol'])
                        if ul:
                            items = [li.get_text(strip=True) for li in ul.find_all('li', limit=25) if li.get_text(strip=True)]
                            if items and len(items) >= 2:
                                description = '\n'.join(items)
                                self.log(f"   📄 Descriere din listă (Product Description): {len(items)} puncte", "INFO")
                                break
                        # Sau paragrafe în același container
                        paras = parent.find_all(['p', 'li'], limit=20)
                        if paras:
                            lines = [p.get_text(strip=True) for p in paras if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20]
                            if len(lines) >= 2 and any('designed for' in l.lower() or 'compatible' in l.lower() or 'ideal for' in l.lower() for l in lines):
                                description = '\n'.join(lines)
                                self.log(f"   📄 Descriere din paragrafe (Product Description): {len(lines)} linii", "INFO")
                                break
                    if description and len(description) > 80:
                        break

            # Fallback MobileSentrix: caută blocul "Product Description" (Net Weight, Compatibility, Product size, Speed)
            if not description or len(description) < 50:
                for elem in product_soup.find_all(string=re.compile(r'Product Description|Net Weight|Compatibility|Product size|Speed:', re.I)):
                    parent = elem.parent
                    for _ in range(8):
                        if not parent or not getattr(parent, 'name', None):
                            break
                        text = parent.get_text(separator='\n', strip=True)
                        if ('Net Weight' in text or 'Compatibility' in text or 'Product size' in text) and 40 < len(text) < 3000:
                            description = text
                            self.log(f"   📄 Descriere găsită din bloc (Net Weight/Compatibility)", "INFO")
                            break
                        parent = getattr(parent, 'parent', None)
                    if description and len(description) > 50:
                        break

            # Fallback regex: descrieri tip bullet (Designed for..., Quickly identifies..., Compatible with..., etc.)
            if not description or len(description) < 80:
                page_text = product_soup.get_text(separator='\n')
                bullet_lines = []
                for pattern in [
                    r'Designed for [^\n]+',
                    r'Quickly identifies [^\n]+',
                    r'Compatible with [^\n]+',
                    r'Ideal for [^\n]+',
                    r'High-quality [^\n]+',
                    r'Compact and [^\n]+',
                    r'Functionality assured[^\n]*',
                ]:
                    m = re.search(pattern, page_text, re.I)
                    if m:
                        line = m.group(0).strip()
                        if 15 < len(line) < 400 and line not in bullet_lines:
                            bullet_lines.append(line)
                if len(bullet_lines) >= 2:
                    description = '\n'.join(bullet_lines)
                    self.log(f"   📄 Descriere extrasă din bullet-uri (regex): {len(bullet_lines)} linii", "INFO")

            # Fallback regex pe textul paginii: extrage specificații (Net Weight, Compatibility, Product size, Speed)
            if not description or len(description) < 50:
                page_text = product_soup.get_text(separator='\n')
                spec_parts = []
                # Net Weight: 350g sau Weight: 350g
                m = re.search(r'(?:Net\s+Weight|Weight)[\s:]*([^\n]{2,80})', page_text, re.I)
                if m:
                    spec_parts.append('Net Weight: ' + m.group(1).strip())
                # Compatibility: ...
                m = re.search(r'Compatibility[\s:]*([^\n]{5,400})', page_text, re.I)
                if m:
                    spec_parts.append('Compatibility: ' + m.group(1).strip())
                # Product size: 124*130.5*42mm
                m = re.search(r'Product\s+size[\s:]*([^\n]{3,120})', page_text, re.I)
                if m:
                    spec_parts.append('Product size: ' + m.group(1).strip())
                # Speed: 200 r/min
                m = re.search(r'Speed[\s:]*([^\n]{2,60})', page_text, re.I)
                if m:
                    spec_parts.append('Speed: ' + m.group(1).strip())
                if spec_parts:
                    description = (product_name + '. ' + ' '.join(spec_parts)).strip()
                    self.log(f"   📄 Descriere extrasă prin regex (specs din pagină)", "INFO")
            
            # Curăță descrierea de text garbage
            import re
            # Elimină liniile cu "Copy", "EAN", "SKU", "Share" și alte gunoaie
            lines = description.split('\n')
            clean_lines = []
            for line in lines:
                line = line.strip()
                # Sări linii care conțin cuvinte de ignorat
                if any(skip in line for skip in ['Copy', 'Share', 'Email', 'WhatsApp', 'FAQ', 'Contact', 'EAN:', 'SKU:', 'Add to']):
                    continue
                # Sări linii prea scurte (probably UI text)
                if len(line) < 3:
                    continue
                clean_lines.append(line)
            
            description = ' '.join(clean_lines)[:3000]  # Descriere completă pentru Ollama/SEO

            # Încearcă să extragi și blocul de specificații tehnice (tabel / listă)
            spec_selectors = [
                '.product.attribute.overview .value',
                '.additional-attributes table',
                '.data.table',
                '[itemprop="description"] table',
                '.product-info-description table',
                '.specifications',
                '.product-attachments'
            ]
            for spec_sel in spec_selectors:
                spec_elem = product_soup.select_one(spec_sel)
                if spec_elem:
                    spec_text = spec_elem.get_text(separator=' | ', strip=True)[:1500]
                    if spec_text and len(spec_text) > 20:
                        description = (description + "\n\nSpecificații: " + spec_text).strip()[:3500]
                        break

            # Elimină URL-uri și alte caractere speciale
            description = re.sub(r'https?://\S+', '', description).strip()
            description = re.sub(r'\s+', ' ', description)  # Normalizează whitespace

            if not description:
                description = f"Produs {product_name}"
            
            # Extrage imagini
            images_data = []
            
            if self.download_images_var.get():
                self.log(f"   🖼️ Descarc imagini MARI...", "INFO")
                
                # 🎯 CAUTĂ IMAGINILE ÎN META TAGS + GALERIE COMPLETĂ
                img_urls = set()
                
                # 1. Meta tags Open Graph (imaginea principală)
                og_images = product_soup.find_all('meta', property='og:image')
                for og_img in og_images:
                    if og_img.get('content'):
                        img_urls.add(og_img['content'])
                        self.log(f"      ✓ Găsită imagine în og:image", "INFO")
                
                # 2. JSON-LD structured data (poate conține array de imagini)
                json_ld_scripts = product_soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'image' in data:
                            images = data['image']
                            if isinstance(images, str):
                                img_urls.add(images)
                            elif isinstance(images, list):
                                for img in images:
                                    if isinstance(img, str):
                                        img_urls.add(img)
                                    elif isinstance(img, dict) and 'url' in img:
                                        img_urls.add(img['url'])
                                self.log(f"      ✓ Găsite {len(images) if isinstance(images, list) else 1} imagini în JSON-LD", "INFO")
                    except:
                        pass
                
                # 3. 🔥 GALERIA MAGICZOOM - aici sunt TOATE imaginile!
                magic_zoom_links = product_soup.find_all('a', {'data-zoom-id': True})
                for link in magic_zoom_links:
                    href = link.get('href')
                    if href and '/catalog/product/' in href:
                        img_urls.add(href)
                self.log(f"      ✓ Găsite {len(magic_zoom_links)} imagini în galeria MagicZoom", "INFO")
                
                # 4. Link-uri cu atribut data-image (thumbnail gallery)
                data_image_links = product_soup.find_all('a', {'data-image': True})
                for link in data_image_links:
                    href = link.get('href')
                    if href and '/catalog/product/' in href:
                        img_urls.add(href)
                
                # 5. Fallback: caută imagini în elemente img standard
                img_selectors = [
                    '.product-image-photo',
                    'img[data-role="image"]',
                    '.product-photo img',
                    '.gallery-placeholder img'
                ]
                for selector in img_selectors:
                    for img_elem in product_soup.select(selector):
                        src = img_elem.get('src') or img_elem.get('data-src')
                        if src and 'catalog/product' in src:
                            img_urls.add(src)
                
                if not img_urls:
                    self.log(f"   ⚠️ Nu am găsit imagini pe pagina produsului", "WARNING")
                else:
                    self.log(f"   🔍 Total imagini găsite: {len(img_urls)}", "INFO")

                # Pregătește URL-urile (absolut + fără thumbnail)
                prepared_urls = []
                for img_url in list(img_urls)[:10]:  # Max 10 imagini
                    if img_url.startswith('/'):
                        img_url = 'https://www.mobilesentrix.eu' + img_url
                    elif not img_url.startswith('http'):
                        img_url = 'https://www.mobilesentrix.eu/' + img_url
                    img_url = img_url.replace('/thumbnail/', '/image/').replace('/small_image/', '/image/')
                    prepared_urls.append(img_url)

                # ⚡ DOWNLOAD PARALEL - 4 imagini simultan (de la ~30s la ~8s)
                from concurrent.futures import ThreadPoolExecutor, as_completed

                def _download_one_image(args):
                    """Descarcă și optimizează o imagine (rulează în thread separat)."""
                    idx, url = args
                    try:
                        img_response = requests.get(url, headers=headers, timeout=15)
                        img_response.raise_for_status()

                        img = Image.open(BytesIO(img_response.content))

                        # 🔧 Optimizare: resize la max 1200x1200 (reduce upload time cu 60-70%)
                        max_size = (1200, 1200)
                        if img.width > max_size[0] or img.height > max_size[1]:
                            img.thumbnail(max_size, Image.Resampling.LANCZOS)

                        # 🖼️ Detectează transparență (canal alpha) - NU converti la JPEG!
                        has_transparency = img.mode in ('RGBA', 'LA') or \
                                          (img.mode == 'P' and 'transparency' in img.info)

                        if has_transparency:
                            # Păstrează transparența → salvează ca WebP (suportă alpha, fișier mic)
                            if img.mode in ('P', 'LA'):
                                img = img.convert('RGBA')
                            img_extension = 'webp'
                            img_filename = f"{product_id}_{idx}.{img_extension}"
                            img_path = self._script_dir / "images" / img_filename
                            img.save(img_path, 'WEBP', quality=90)
                        else:
                            # Fără transparență → JPEG (cel mai mic)
                            if img.mode in ('RGBA', 'P', 'LA'):
                                img = img.convert('RGB')
                            img_extension = 'jpg'
                            img_filename = f"{product_id}_{idx}.{img_extension}"
                            img_path = self._script_dir / "images" / img_filename
                            img.save(img_path, 'JPEG', quality=85, optimize=True)
                        file_size = img_path.stat().st_size / (1024 * 1024)

                        return {
                            'success': True,
                            'idx': idx,
                            'src': url,
                            'local_path': str(img_path),
                            'name': img_filename,
                            'size': f"{file_size:.2f} MB"
                        }
                    except Exception as e:
                        return {'success': False, 'idx': idx, 'error': str(e)}

                # Lansează download-urile în paralel (4 thread-uri)
                download_tasks = [(idx, url) for idx, url in enumerate(prepared_urls, 1)]

                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {executor.submit(_download_one_image, task): task for task in download_tasks}

                    for future in as_completed(futures):
                        result = future.result()
                        if result['success']:
                            images_data.append({
                                'src': result['src'],
                                'local_path': result['local_path'],
                                'name': result['name'],
                                'size': result['size']
                            })
                            self.log(f"      📷 [{result['idx']}] ✓ {result['name']} ({result['size']})", "SUCCESS")
                        else:
                            self.log(f"      ⚠️ [{result['idx']}] Eroare: {result['error']}", "WARNING")

                # Sortează imaginile după index (ordinea corectă)
                images_data.sort(key=lambda x: x['name'])

                self.log(f"   ✓ Total imagini descărcate: {len(images_data)} (paralel, optimizate)", "SUCCESS")
            
            # Extrage brand din nume (de obicei primul cuvânt sau "iPhone", "Samsung" etc)
            brand = 'MobileSentrix'  # Default
            if 'iPhone' in product_name or 'Apple' in product_name:
                brand = 'Apple'
            elif 'Samsung' in product_name or 'Galaxy' in product_name:
                brand = 'Samsung'
            elif 'Google' in product_name or 'Pixel' in product_name:
                brand = 'Google'
            
            # 🎯 EXTRAGE SKU-UL REAL DE LA MOBILESENTRIX DIN JAVASCRIPT
            extracted_sku = None
            try:
                import re
                # Caută variabila ecommerce.items.item_id în JavaScript
                # Pattern: var ecommerce = {...,"item_id":"107182127516",...}
                ecommerce_pattern = r'var ecommerce\s*=\s*{[^}]*"item_id"\s*:\s*"(\d+)"'
                ecommerce_match = re.search(ecommerce_pattern, product_page_html)

                if ecommerce_match:
                    extracted_sku = ecommerce_match.group(1)
                    self.log(f"   ✓ SKU MobileSentrix extras din JavaScript: {extracted_sku}", "SUCCESS")
            except Exception as sku_extract_error:
                self.log(f"   ⚠️ Nu am putut extrage SKU din JavaScript: {sku_extract_error}", "WARNING")

            # 🔢 EXTRAGE EAN REAL (COD DE BARE 8-14 CIFRE) DE PE PAGINA MOBILESENTRIX
            extracted_ean = ''
            try:
                import re, json

                # 1. JSON-LD structured data: "gtin13", "gtin", "gtin14", "ean"
                json_ld_scripts = product_soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            for ean_key in ['gtin13', 'gtin', 'gtin14', 'gtin12', 'gtin8', 'ean', 'mpn']:
                                val = data.get(ean_key, '')
                                if val and re.match(r'^\d{8,14}$', str(val)):
                                    extracted_ean = str(val)
                                    self.log(f"   ✓ EAN extras din JSON-LD ({ean_key}): {extracted_ean}", "SUCCESS")
                                    break
                            # Caută și în offers
                            if not extracted_ean and 'offers' in data:
                                offers = data['offers']
                                if isinstance(offers, dict):
                                    offers = [offers]
                                if isinstance(offers, list):
                                    for offer in offers:
                                        for ean_key in ['gtin13', 'gtin', 'sku']:
                                            val = offer.get(ean_key, '')
                                            if val and re.match(r'^\d{8,14}$', str(val)):
                                                extracted_ean = str(val)
                                                self.log(f"   ✓ EAN extras din JSON-LD offers ({ean_key}): {extracted_ean}", "SUCCESS")
                                                break
                                        if extracted_ean:
                                            break
                        if extracted_ean:
                            break
                    except:
                        pass

                # 2. HTML: meta itemprop="gtin13", "gtin", "ean"
                if not extracted_ean:
                    for prop in ['gtin13', 'gtin', 'gtin14', 'gtin8', 'ean', 'mpn']:
                        meta_elem = product_soup.find(attrs={'itemprop': prop})
                        if meta_elem:
                            val = meta_elem.get('content', '') or meta_elem.get_text(strip=True)
                            if val and re.match(r'^\d{8,14}$', str(val)):
                                extracted_ean = str(val)
                                self.log(f"   ✓ EAN extras din HTML itemprop ({prop}): {extracted_ean}", "SUCCESS")
                                break

                # 3. HTML: text vizibil pe pagină "EAN:", "Barcode:", "UPC:"
                if not extracted_ean:
                    page_text = product_soup.get_text()
                    ean_text_match = re.search(
                        r'(?:EAN|Barcode|UPC|GTIN|ISBN)[\s:]*(\d{8,14})',
                        page_text, re.IGNORECASE
                    )
                    if ean_text_match:
                        extracted_ean = ean_text_match.group(1)
                        self.log(f"   ✓ EAN extras din text pagină: {extracted_ean}", "SUCCESS")

                # 4. JavaScript: "ean":"0195949043505" sau barcode/gtin
                if not extracted_ean:
                    js_ean_match = re.search(
                        r'["\'](?:ean|barcode|gtin|gtin13|upc)["\'][\s:]*["\'](\d{8,14})["\']',
                        product_page_html, re.IGNORECASE
                    )
                    if js_ean_match:
                        extracted_ean = js_ean_match.group(1)
                        self.log(f"   ✓ EAN extras din JavaScript: {extracted_ean}", "SUCCESS")

                # 5. Fallback: dacă input-ul original e EAN (8-14 cifre), folosim asta
                if not extracted_ean and re.match(r'^\d{8,14}$', ean.strip()):
                    extracted_ean = ean.strip()
                    self.log(f"   ℹ️ EAN: folosit input-ul original ca EAN: {extracted_ean}", "INFO")

                if not extracted_ean:
                    self.log(f"   ⚠️ Nu am găsit EAN (cod de bare) pe pagina produsului", "WARNING")

            except Exception as ean_error:
                self.log(f"   ⚠️ Eroare extragere EAN: {ean_error}", "WARNING")
            
            # Generează SKU din ID produsului intern sau folosește cel extras
            if extracted_sku:
                # Dacă am extras SKU-ul de la MobileSentrix, îl folosim direct!
                generated_sku = extracted_sku
                self.log(f"   ✓ SKU folosit: {generated_sku} (de la MobileSentrix)", "INFO")
            elif product_id_internal:
                # Fallback: SKU generat din ID intern - DOAR CIFRE
                generated_sku = product_id_internal
                self.log(f"   ✓ SKU generat din ID produs: {generated_sku}", "INFO")
            else:
                # Fallback: din URL slug - DOAR CIFRE
                import re
                import time
                # Extrage doar numerele din URL, dacă nu găsește nimic, folosește timestamp
                sku_base = re.sub(r'[^0-9]', '', product_id[:20])
                if not sku_base:
                    # Dacă nu am găsit cifre în URL, generez din timestamp
                    sku_base = str(int(time.time()))[-8:]
                generated_sku = sku_base
                self.log(f"   ✓ SKU generat din URL: {generated_sku}", "INFO")
            
            # Tag-uri: din pagină, dar excludem text de tip nav/footer (Error, Europe, About, Services, etc.)
            tags = []
            tag_nav_blocklist = (
                'error', 'eroare', 'europe', 'europa', 'united states', 'statele unite', 'canada',
                'united kingdom', 'regatul unit', 'about', 'despre', 'services', 'servicii',
                'our brands', 'mărcile noastre', 'support', 'asistență', 'hello', 'bună ziua',
                'contact', 'contact us', 'choose your country', 'log in', 'copy', 'share'
            )
            tag_selectors = [
                '.product-tags a', '.tags a', '[data-label="Tags"] a',
                '.product-info-tags a', '.product-details-tags a', '.item-tags a',
                '.tag-list a', '.product-info-main a[href*="tag"]',
            ]
            for tag_sel in tag_selectors:
                tag_elems = product_soup.select(tag_sel)
                if tag_elems:
                    for t in tag_elems:
                        txt = t.get_text(strip=True)
                        low = (txt or '').lower()
                        if txt and 2 < len(txt) < 80 and low not in [x.lower() for x in tags]:
                            if not any(bl in low for bl in tag_nav_blocklist):
                                tags.append(txt)
                    if tags:
                        self.log(f"   🏷️ Tag-uri extrase din pagină: {len(tags)}", "INFO")
                        break
            # Fallback: caută secțiunea "Tag" (heading) și linkurile din ea (ex. wholesale screwdrivers)
            if not tags:
                tag_heading = product_soup.find(string=re.compile(r'^\s*Tag\s*$', re.I))
                if tag_heading:
                    container = tag_heading.find_parent(['div', 'section', 'li']) or tag_heading.find_parent('div')
                    if container:
                        for a in container.find_all('a', limit=15):
                            txt = a.get_text(strip=True)
                            if txt and 2 < len(txt) < 80 and txt not in tags:
                                tags.append(txt)
                        if tags:
                            self.log(f"   🏷️ Tag-uri din secțiunea Tag: {len(tags)}", "INFO")

            # MobileSentrix: tag-urile sunt heading-uri (h3/h4), nu link-uri – ex: "wholesale screwdrivers", "cell phone screwdriver supplier"
            if not tags:
                tag_blocklist = (
                    'sku', 'product description', 'add to cart', 'rating', 'ex. vat', 'inc. vat',
                    'related products', 'core return', 'choose your country', 'quantity', 'copy',
                    'share', 'ship', 'price match', 'easy refunds', 'returns', 'do you want',
                    'log in', 'contact us', 'learn more', 'important', 'information', 'cancel',
                    'submit', 'close', 'yes', 'no', 'ok', 'welcome', 'remember my selection',
                    'speed', 'r/min', 'net weight', 'compatibility', 'product size'
                )
                product_main = product_soup.select_one('.product-info-main, .column.main, main, [class*="product-detail"]') or product_soup
                for head in product_main.select('h3, h4, h5'):
                    txt = head.get_text(strip=True)
                    if txt and 3 <= len(txt) <= 80:
                        low = txt.lower()
                        if low not in tag_blocklist and not any(skip in low for skip in ('sku ', 'product ', 'add to', 'rating', 'vat', 'related', 'return', 'country', 'quantity', 'copy', 'share')):
                            if txt not in tags and low not in [t.lower() for t in tags]:
                                tags.append(txt)
                if tags:
                    tags = tags[:12]  # max 12 tag-uri din heading-uri
                    self.log(f"   🏷️ Tag-uri din heading-uri (h3/h4/h5): {len(tags)}", "INFO")

            product_name_lower = product_name.lower()
            if not tags:
                # Fallback: construiește din nume (vor fi traduse la export)
                # Brand
                if 'apple' in product_name_lower:
                    tags.append('Apple')
                if 'samsung' in product_name_lower:
                    tags.append('Samsung')
                if 'motorola' in product_name_lower:
                    tags.append('Motorola')
                if 'google' in product_name_lower or 'pixel' in product_name_lower:
                    tags.append('Google Pixel')
                if 'oneplus' in product_name_lower:
                    tags.append('OnePlus')
                if 'xiaomi' in product_name_lower:
                    tags.append('Xiaomi')
                if 'huawei' in product_name_lower:
                    tags.append('Huawei')
                # Tip dispozitiv
                if 'iphone' in product_name_lower:
                    tags.append('iPhone')
                if 'ipad' in product_name_lower:
                    tags.append('iPad')
                if 'watch' in product_name_lower or 'apple watch' in product_name_lower:
                    tags.append('Apple Watch')
                if 'macbook' in product_name_lower:
                    tags.append('MacBook')
                if 'galaxy' in product_name_lower:
                    tags.append('Samsung Galaxy')
                # Model specific
                if 'pro max' in product_name_lower:
                    tags.append('Pro Max')
                if 'pro' in product_name_lower and 'pro max' not in product_name_lower:
                    tags.append('Pro')
                if 'air' in product_name_lower:
                    tags.append('Air')
                if 'mini' in product_name_lower:
                    tags.append('Mini')
                if 'ultra' in product_name_lower:
                    tags.append('Ultra')
                if 'plus' in product_name_lower:
                    tags.append('Plus')
                # Versiuni iOS
                if 'iphone 17' in product_name_lower:
                    tags.append('iPhone 17')
                if 'iphone 16' in product_name_lower:
                    tags.append('iPhone 16')
                if 'iphone 15' in product_name_lower:
                    tags.append('iPhone 15')
                if 'iphone 14' in product_name_lower:
                    tags.append('iPhone 14')
                if 'iphone 13' in product_name_lower:
                    tags.append('iPhone 13')
                # Specificații
                if 'oled' in product_name_lower:
                    tags.append('OLED')
                if 'lcd' in product_name_lower or 'ips' in product_name_lower:
                    tags.append('LCD')
                if '120hz' in product_name_lower or '120 hz' in product_name_lower:
                    tags.append('120Hz')
                if '90hz' in product_name_lower or '90 hz' in product_name_lower:
                    tags.append('90Hz')
                if '60hz' in product_name_lower or '60 hz' in product_name_lower:
                    tags.append('60Hz')
                # Tip component
                if 'assembly' in product_name_lower or 'display' in product_name_lower:
                    tags.append('Display Assembly')
                if 'screen' in product_name_lower:
                    tags.append('Screen')
                if 'battery' in product_name_lower:
                    tags.append('Battery')
                if 'charging' in product_name_lower or 'charger' in product_name_lower:
                    tags.append('Charging')
                if 'port' in product_name_lower:
                    tags.append('Port')
                if 'camera' in product_name_lower:
                    tags.append('Camera')
                if 'speaker' in product_name_lower:
                    tags.append('Speaker')
                if 'microphone' in product_name_lower:
                    tags.append('Microphone')
                if 'button' in product_name_lower:
                    tags.append('Button')
                if 'cable' in product_name_lower:
                    tags.append('Cable')
                if 'adapter' in product_name_lower:
                    tags.append('Adapter')
                if 'glass' in product_name_lower:
                    tags.append('Glass')
                # Calitate
                if 'genuine' in product_name_lower or 'oem' in product_name_lower:
                    tags.append('Genuine OEM')
                if 'aftermarket' in product_name_lower:
                    tags.append('Aftermarket')
                if 'compatible' in product_name_lower:
                    tags.append('Compatible')
                if 'replacement' in product_name_lower:
                    tags.append('Replacement')
                if 'original' in product_name_lower:
                    tags.append('Original')
                if 'premium' in product_name_lower:
                    tags.append('Premium')
                if 'quality' in product_name_lower:
                    tags.append('Quality')
                # Elimină duplicatele și ordonează alfabetic
                tags = list(dict.fromkeys(tags))
                tags = sorted(set(tags))

            category_path = self.detect_category(product_name, tags)

            # ===== Disponibilitate: in_stock / preorder / out_of_stock =====
            page_text = product_soup.get_text()
            availability = self.detect_availability(product_soup, page_text)
            if availability == 'in_stock':
                locatie_stoc = 'depozit_central'
            elif availability == 'preorder':
                locatie_stoc = 'precomanda'
            else:
                locatie_stoc = 'indisponibil'
            self.log(f"   📦 Disponibilitate: {availability} → locatie_stoc: {locatie_stoc}", "INFO")

            # ===== WEBGSM: Extrage atribute, categorie slug, coduri, features =====
            attributes = self.extract_product_attributes(product_name, description, product_link or '')
            category_slug = self.get_webgsm_category(product_name, description=description)
            compat_codes = self.extract_compatibility_codes(description)
            screen_features = self.detect_screen_features(product_name, description)

            self.log(f"   📋 Atribute WebGSM:", "INFO")
            self.log(f"      Model: {attributes['pa_model']}", "INFO")
            self.log(f"      Calitate: {attributes['pa_calitate']}", "INFO")
            self.log(f"      Brand piesa: {attributes['pa_brand_piesa']}", "INFO")
            self.log(f"      Tehnologie: {attributes['pa_tehnologie']}", "INFO")
            self.log(f"      Categorie slug: {category_slug}", "INFO")
            if compat_codes:
                self.log(f"      Coduri compatibilitate: {compat_codes}", "INFO")
            if screen_features['ic_movable'] == 'true':
                self.log(f"      IC Movable: DA", "INFO")
            if screen_features['truetone_support'] == 'true':
                self.log(f"      TrueTone: DA", "INFO")

            product_data = {
                'ean': ean if not ean.startswith('http') else product_link,
                'ean_real': extracted_ean,  # EAN cod de bare real (8-14 cifre)
                'sku': generated_sku,  # SKU intern MobileSentrix (ex: 230473)
                'sku_furnizor': extracted_sku or generated_sku,  # SKU furnizor (ex: 107182127516)
                'name': product_name,
                'price': price,
                'description': description,
                'stock': '100',
                'brand': brand,
                'tags': ', '.join(tags),
                'category_path': category_path,
                'images': images_data,
                # WebGSM fields
                'pa_model': attributes['pa_model'],
                'pa_calitate': attributes['pa_calitate'],
                'pa_brand_piesa': attributes['pa_brand_piesa'],
                'pa_tehnologie': attributes['pa_tehnologie'],
                'category_slug': category_slug,
                'coduri_compatibilitate': compat_codes,
                'ic_movable': screen_features['ic_movable'],
                'truetone_support': screen_features['truetone_support'],
                'furnizor_activ': 'mobilesentrix',
                'pret_achizitie_eur': price,
                'availability': availability,
                'locatie_stoc': locatie_stoc,
                'source_url': product_link or '',  # URL sursă: direct din input sau pagina finală după căutare
            }

            self.log(f"   ✓ Date extrase cu succes! (format WebGSM)", "SUCCESS")

            return product_data
            
        except requests.exceptions.RequestException as req_error:
            self.log(f"   ✗ Eroare conexiune: {req_error}", "ERROR")
            return None
        except Exception as e:
            self.log(f"   ✗ Eroare scraping: {e}", "ERROR")
            import traceback
            self.log(f"   📝 Traceback: {traceback.format_exc()}", "ERROR")
            return None
    
    def cleanup_phantom_from_mysql(self, product_id):
        """Șterge phantom product direct din MySQL (dacă API nu funcționează)"""
        try:
            # Extrage credentialele MySQL din .env sau config
            db_host = os.getenv('DB_HOST', 'localhost')
            db_user = os.getenv('DB_USER', 'root')
            db_pass = os.getenv('DB_PASSWORD', '')
            db_name = os.getenv('DB_NAME', 'wordpress')
            
            # Încearcă import - MySQL nu e instalat pe client deci NU merge
            # Alternativă: Șterge prin WordPress CLI API
            # Pentru moment: Raportează și cere manual cleanup
            self.log(f"   ⚠️ Phantom ID {product_id} va fi șters manual din phpMyAdmin", "WARNING")
            return False
            
        except Exception as e:
            self.log(f"   ⚠️ Nu am putut șterge phantom ID {product_id}: {e}", "WARNING")
            return False

    def upload_image_to_wordpress(self, local_image_path):
        """Uploadează imagine din folder local pe server WordPress/WooCommerce"""
        try:
            local_path = Path(local_image_path)
            
            if not local_path.exists():
                self.log(f"   ⚠️ Imagine nu există: {local_image_path}", "WARNING")
                return None
            
            # Citește fișierul
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            # Headers pentru upload - WordPress media endpoint
            headers = {
                'Content-Disposition': f'attachment; filename="{local_path.name}"'
            }
            
            # Detectează MIME type
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(local_path.suffix.lower(), 'image/jpeg')
            headers['Content-Type'] = mime_type
            
            # URL media upload endpoint
            media_url = f"{self.config['WOOCOMMERCE_URL']}/wp-json/wp/v2/media"
            
            # WordPress Application Password (diferit de WooCommerce API keys!)
            wp_username = os.getenv('WP_USERNAME', 'admin')
            wp_app_password = os.getenv('WP_APP_PASSWORD', '')
            
            if not wp_app_password:
                self.log(f"         ⚠️ WP_APP_PASSWORD lipsă din .env!", "WARNING")
                return None
            
            # Încearcă upload cu Application Password
            self.log(f"      📤 Upload: {local_path.name} ({len(file_data)/1024:.1f}KB)...", "INFO")
            
            response = requests.post(
                media_url,
                data=file_data,
                headers=headers,
                auth=(wp_username, wp_app_password.replace(' ', '')),  # Remove spaces din password
                timeout=30  # ⚡ Redus de la 60s (imaginile sunt deja optimizate, <1.5MB)
            )
            
            if response.status_code in [200, 201]:
                media_data = response.json()
                media_id = media_data.get('id')
                media_url_result = media_data.get('source_url')
                self.log(f"         ✓ ID={media_id}", "SUCCESS")
                return {
                    'id': media_id,
                    'src': media_url_result,
                    'name': local_path.name
                }
            else:
                error_msg = response.text[:200] if response.text else f"Status {response.status_code}"
                self.log(f"         ✗ Upload eșuat: {error_msg}", "WARNING")
                return None
                
        except Exception as e:
            self.log(f"   ⚠️ Eroare upload imagine: {e}", "WARNING")
            return None


# Main
if __name__ == "__main__":
    root = tk.Tk()
    app = ImportProduse(root)
    root.mainloop()
