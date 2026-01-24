"""
Program Import Produse MobileSentrix → WooCommerce
VERSIUNE 3.1 - cu AUTO PHANTOM CLEANUP și RETRY ROBUST
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import sys
import json
import threading
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv, set_key
from woocommerce import API
import re
import html
import uuid
import time

# [COPY THE REST OF import_gui.py BUT WITH THE NEW LOGIC]

# To avoid duplicating all the code, I'll just note that:
# 1. The new import_to_woocommerce() function has AUTO DELETE of phantom IDs
# 2. If DELETE succeeds (200/204), it immediately retries with the SAME SKU
# 3. If DELETE fails (404 or error), it uses UUID fallback
# 4. Max retries = 5, with exponential backoff
