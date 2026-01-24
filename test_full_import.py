#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full integration test - reads from sku_list.txt and exports CSV"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'c:\\program preluate prodsue')

from pathlib import Path
from import_gui import ImportProduse

# Mock GUI class
class TestFullImporter(ImportProduse):
    def __init__(self):
        self.logs = []
        class MockVar:
            def __init__(self, value=True):
                self.value = value
            def get(self):
                return self.value
        self.download_images_var = MockVar(True)
        self.images_per_product_var = MockVar()
        self.convert_price_var = MockVar(True)  # Convert EUR to RON
        self.exchange_rate_var = MockVar()
        self.exchange_rate_var.value = 4.97
        self.image_folder = "images"
        self.csv_data = []
        self.csv_filename = None
        self.headers = None
        
        # Create directories
        Path("images").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
    
    def log(self, message, level="INFO"):
        self.logs.append(f"[{level}] {message}")
        print(f"  {message}")

# Create importer
print("=" * 80)
print("FULL INTEGRATION TEST - SKU_LIST.TXT IMPORT")
print("=" * 80)

importer = TestFullImporter()

# Read sku_list.txt
sku_file = Path("sku_list.txt")
if not sku_file.exists():
    print(f"\nERROR: {sku_file} not found!")
    sys.exit(1)

skus = []
with open(sku_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            skus.append(line)

print(f"\nFound {len(skus)} items in {sku_file}:")
for i, sku in enumerate(skus, 1):
    print(f"  [{i}] {sku[:70]}")

# Import each product
print(f"\n{'=' * 80}")
print("IMPORTING PRODUCTS...")
print("=" * 80)

successes = 0
failures = 0
products_data = []  # Lista pentru export_to_csv()

for i, sku in enumerate(skus, 1):
    print(f"\n[{i}/{len(skus)}] Processing: {sku[:70]}...")
    try:
        result = importer.scrape_product(sku)
        if result:
            products_data.append(result)  # Adaugă în listă pentru export
            print(f"   SUCCESS! SKU: {result.get('sku')}, Name: {result.get('name')[:50]}")
            successes += 1
        else:
            print(f"   FAILED: Returned None")
            failures += 1
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {str(e)[:100]}")
        failures += 1

# Export CSV folosind funcția din ImportProduse
print(f"\n{'=' * 80}")
print("EXPORTING CSV...")
print("=" * 80)

csv_filename = f"produse_imported_{Path('sku_list.txt').stat().st_mtime:.0f}.csv"

if products_data:
    importer.export_to_csv(products_data, csv_filename)
    csv_file = Path("data") / csv_filename
    print(f"\nCSV exported: {csv_file}")
    print(f"Rows: {len(products_data)} (+ 1 header)")
else:
    print("No data to export!")
    csv_file = None

# Summary
print(f"\n{'=' * 80}")
print("SUMMARY")
print("=" * 80)
print(f"Total processed: {len(skus)}")
print(f"Successes: {successes}")
print(f"Failures: {failures}")
if csv_file:
    print(f"CSV file: {csv_file}")
print("=" * 80)
