#!/usr/bin/env python3
"""
MASTER EXTRACTOR - Simple Version (non-interactive)
Versiune simplificată pentru batch execution
"""

import sys
import os

# Fix encoding for Windows
try:
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
except:
    pass

from pathlib import Path
import subprocess

def main():
    print("=" * 70)
    print(" " * 15 + "MASTER EXTRACTOR - MOBILESENTRIX")
    print(" " * 10 + "Extrage link-uri pe categorii din MobileSentrix.eu")
    print("=" * 70)
    print()
    print("Opțiuni disponibile:")
    print()
    print("  1. python category_url_generator.py")
    print("     Generează și testează URL-urile categoriilor")
    print()
    print("  2. python extractor_category_links.py")
    print("     Extrage link-urile din categorii")
    print()
    print("  3. python extractor_from_csv.py <fișier>")
    print("     Organizează link-uri din CSV existent")
    print()
    print("  4. python extractor_selenium.py")
    print("     Extrage cu browser (pentru site-uri cu JS)")
    print()
    print("  5. python import_gui.py")
    print("     GUI pentru import produse")
    print()
    print("Alternativ, rulează direct fișierele cu extensia .bat:")
    print()
    print("  master_extractor.bat (meniu interactiv)")
    print("  import_gui.bat (import GUI)")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
