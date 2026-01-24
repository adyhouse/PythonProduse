#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script pentru scrape_product() fix"""

import sys
sys.stdout.reconfigure(encoding='utf-8')  # Fix UTF-8 encoding on Windows
sys.path.insert(0, 'c:\\program preluate prodsue')

from import_gui import ImportProduse

# Creează instanță (ImportProduse necesită root tkinter, deci facem hack)
class TestImporter(ImportProduse):
    def __init__(self):
        # Skip tkinter initialization
        self.logs = []
        # Add mock GUI variables
        class MockVar:
            def get(self):
                return True
        self.download_images_var = MockVar()
        self.images_per_product_var = MockVar()
        self.image_folder = "images"
        self.csv_data = []
    
    def log(self, message, level="INFO"):
        self.logs.append(f"[{level}] {message}")
        print(f"  {message}")

importer = TestImporter()

# Test data din sku_list.txt
test_cases = [
    "107182127516",  # numeric SKU
    "https://www.mobilesentrix.eu/charging-port-flex-cable-for-iphone-17-pro-max-premium-international-version-cosmic-orange",  # direct link
    "107182127516"  # numeric SKU again
]

print("=" * 80)
print("TEST SCRAPE_PRODUCT() FIXES")
print("=" * 80)

for i, test_input in enumerate(test_cases, 1):
    print(f"\n[Test {i}/3] Input: {test_input[:70]}...")
    
    try:
        result = importer.scrape_product(test_input)
        if result:
            print(f"SUCCESS! Result keys: {list(result.keys())}")
            if 'sku' in result:
                print(f"   SKU from product: {result['sku']}")
        else:
            print(f"FAILED: Returned None")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("Test complete!")
print("=" * 80)
