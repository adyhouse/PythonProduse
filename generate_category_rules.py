"""
Generate category_rules.txt from MobileSentrix categories mapped to user's WebGSM structure:

Piese de schimb
  - Apple
  - Samsung
  - Motorola
  - Google
  - Alte piese

Console jocuri
  (no subcategories)

Accesorii
  - Huse
  - Baterii externe
  - Incarcatoare
  - Suport telefon
  - Folii protectie
  - Cabluri si Adaptori
  - Carduri si Memorii USB
  - Casti Audio

Unelte si consumabile
  (generic mapping)
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Load filtered categories
FILTERED_FILE = Path("data/ms_categories_filtered.txt")
OUTPUT_FILE = Path("category_rules_generated.txt")

# Brand-to-category mappings for Piese de schimb
BRAND_MAP = {
    "apple": "Piese de schimb > Apple",
    "samsung": "Piese de schimb > Samsung",
    "motorola": "Piese de schimb > Motorola",
    "google": "Piese de schimb > Google",
    "pixel": "Piese de schimb > Google",
}

# Part types for accessories and consumables
PART_MAP = {
    # Accesorii
    "case": "Accesorii > Huse",
    "cover": "Accesorii > Huse",
    "silicone": "Accesorii > Huse",
    "leather": "Accesorii > Huse",
    "flip": "Accesorii > Huse",
    "book": "Accesorii > Huse",
    "pouch": "Accesorii > Huse",
    
    "battery": "Accesorii > Baterii externe",
    "power bank": "Accesorii > Baterii externe",
    
    "charger": "Accesorii > Incarcatoare",
    "adapter": "Accesorii > Cabluri si Adaptori",
    "wall-adapter": "Accesorii > Incarcatoare",
    "power adapter": "Accesorii > Incarcatoare",
    "macbook charger": "Accesorii > Incarcatoare",
    "watch-charger": "Accesorii > Incarcatoare",
    
    "stand": "Accesorii > Suport telefon",
    "holder": "Accesorii > Suport telefon",
    
    "glass": "Accesorii > Folii protectie",
    "tempered-glass": "Accesorii > Folii protectie",
    "screen protector": "Accesorii > Folii protectie",
    
    "cable": "Accesorii > Cabluri si Adaptori",
    "usb": "Accesorii > Cabluri si Adaptori",
    "lightning": "Accesorii > Cabluri si Adaptori",
    "type-c": "Accesorii > Cabluri si Adaptori",
    "thunderbolt": "Accesorii > Cabluri si Adaptori",
    "micro-usb": "Accesorii > Cabluri si Adaptori",
    
    "memory": "Accesorii > Carduri si Memorii USB",
    "card": "Accesorii > Carduri si Memorii USB",
    "sim": "Accesorii > Carduri si Memorii USB",
    "storage": "Accesorii > Carduri si Memorii USB",
    
    "headphone": "Accesorii > Casti Audio",
    "audio": "Accesorii > Casti Audio",
    "speaker": "Accesorii > Casti Audio",
    "earbud": "Accesorii > Casti Audio",
    
    # Unelte si consumabile
    "cleaning": "Unelte si consumabile",
    "tool": "Unelte si consumabile",
    "workspace": "Unelte si consumabile",
    "adhesive": "Unelte si consumabile",
    "alcohol": "Unelte si consumabile",
    
    # Console jocuri
    "ps5": "Console jocuri > PlayStation 5",
    "ps4": "Console jocuri > PlayStation 4",
    "xbox": "Console jocuri > Xbox",
    "switch": "Console jocuri > Nintendo Switch",
}

def parse_filtered():
    """Parse ms_categories_filtered.txt and extract slug/label/path"""
    entries = []
    if not FILTERED_FILE.exists():
        print(f"File not found: {FILTERED_FILE}")
        return entries
    
    with open(FILTERED_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 3:
                slug = parts[0].strip().lower()
                label = parts[1].strip()
                path = parts[2].strip()
                entries.append({
                    'slug': slug,
                    'label': label,
                    'path': path
                })
    return entries

def categorize_entry(entry):
    """Determine category for a single entry based on slug/label/path"""
    slug = entry['slug'].lower()
    label = entry['label'].lower()
    path = entry['path'].lower()
    
    # Check if it's a replacement part (from /replacement-parts path)
    if '/replacement-parts/' in path:
        # Try brand matching first
        for brand, category in BRAND_MAP.items():
            if brand in slug or brand in label or brand in path:
                return category
        
        # Generic parts category
        return "Piese de schimb > Alte piese"
    
    # Check accessories
    elif '/accessories/' in path or '/repair-tools/' in path:
        for part_type, category in PART_MAP.items():
            if part_type in slug or part_type in label:
                return category
        return "Accesorii > Alte accesorii"  # fallback
    
    # Default
    return "Alte piese"

def main():
    entries = parse_filtered()
    print(f"Loaded {len(entries)} entries from {FILTERED_FILE}")
    
    # Build rules: collect slugs by category, keep only most useful ones
    rules_by_category = defaultdict(set)
    
    for entry in entries:
        category = categorize_entry(entry)
        slug = entry['slug']
        
        # Skip very generic slugs and those with special chars/numbers only
        if len(slug) < 3 or slug.isdigit() or slug.startswith('?'):
            continue
        
        rules_by_category[category].add(slug)
    
    # Build final rules: sort by specificity (longer slugs first)
    all_rules = []
    
    for category in sorted(rules_by_category.keys()):
        slugs = sorted(rules_by_category[category], key=lambda x: -len(x))
        
        # Take max 20 most specific slugs per category (avoid bloat)
        for slug in slugs[:20]:
            all_rules.append((slug, category))
    
    # Sort by specificity (longer slugs = more specific)
    all_rules.sort(key=lambda x: -len(x[0]))
    
    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated category rules from MobileSentrix categories\n")
        f.write("# Format: keyword|Categoria WooCommerce (hierarhie cu '>')\n\n")
        
        for slug, category in all_rules:
            f.write(f"{slug}|{category}\n")
    
    print(f"\nGenerated {len(all_rules)} rules")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"\nTop 30 rules:")
    for slug, category in all_rules[:30]:
        print(f"  {slug:40} | {category}")

if __name__ == "__main__":
    main()
