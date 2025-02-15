import requests
import random
import time
import json
import os
import asyncio
import threading
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from googlesearch import search
import tldextract
from fake_useragent import UserAgent
from safetensors.torch import load_file
import torch
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import pytesseract
from PIL import Image
import cv2
import smtplib
import string
import secrets
from concurrent.futures import ThreadPoolExecutor
import undetected_chromedriver as uc

BACKLINKS_FILE = "backlinks.json"
LOG_FILE = "errors.log"

logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format='%(asctime)s %(message)s')

class BacklinkAutomation:
    def __init__(self, site_url, safetensor_model_path, interval=86400, max_backlinks=100, min_pa=50, min_da=50):
        self.site_url = site_url
        self.user_agent = UserAgent()
        self.keywords = ["seo", "digital marketing", "web development", "link building"]
        self.spam_sites = ["example-spam.com", "blacklisted-site.net"]
        self.model_path = safetensor_model_path
        self.model = self.load_model()
        self.interval = interval
        self.max_backlinks = max_backlinks
        self.min_pa = min_pa
        self.min_da = min_da
        self.backlinks_data = self.load_backlinks_data()
        self.lock = threading.Lock()
        self.driver = self.setup_driver()
        self.executor = ThreadPoolExecutor(max_workers=10)

    def setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return uc.Chrome(options=options)

    def log_error(self, error_message):
        logging.error(error_message)

    def generate_backlink_content(self, keyword):
        input_data = torch.tensor([hash(keyword) % 100])
        output = self.model['output_weights'] @ input_data
        return f"{keyword} hakkında uzman içeriği için {self.site_url} adresine göz atın!"

    def generate_title_content(self, keyword):
        input_data = torch.tensor([hash(keyword) % 100])
        output = self.model['output_weights'] @ input_data
        return f"{keyword} ile İlgili En İyi Kaynaklar!"

    def solve_captcha(self, image_path):
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        return text.strip()

    async def get_seo_score(self, domain):
        try:
            response = await asyncio.to_thread(requests.get, f"https://seo-api.com/get-score?domain={domain}")
            if response.status_code == 200:
                data = response.json()
                return data.get("pa", 0), data.get("da", 0)
        except Exception as e:
            self.log_error(f"SEO skoru alınamadı: {e}")
        return 0, 0

    async def is_valid_site(self, domain):
        pa, da = await self.get_seo_score(domain)
        return pa >= self.min_pa and da >= self.min_da

    async def find_forums_and_blogs(self):
        search_query = "forum OR blog site:com"
        found_sites = []
        for url in search(search_query, num_results=self.max_backlinks):
            domain = tldextract.extract(url).registered_domain
            if domain not in self.spam_sites and await self.is_valid_site(domain):
                found_sites.append(url)
        return found_sites

    def post_comment(self, forum_url):
        try:
            self.driver.get(forum_url)
            time.sleep(3)
            
            comment_section = self.driver.find_elements(By.TAG_NAME, "textarea")
            if not comment_section:
                comment_section = self.driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
            
            if not comment_section:
                print("Yorum alanı bulunamadı!")
                return False
            
            keyword = random.choice(self.keywords)
            backlink_content = self.generate_backlink_content(keyword)
            
            comment_section[0].send_keys(backlink_content)
            submit_buttons = self.driver.find_elements(By.NAME, "submit")
            if submit_buttons:
                submit_buttons[0].click()
            else:
                print("Gönder butonu bulunamadı!")
            
            print(f"Yorum eklendi ve backlink bırakıldı: {forum_url}")
            return True
        except Exception as e:
            self.log_error(f"Yorum ekleme başarısız: {e}")
            return False

    def run(self):
        while True:
            print("Forum ve blog siteleri aranıyor...")
            sites = asyncio.run(self.find_forums_and_blogs())
            print(f"Bulunan siteler: {sites}")
            futures = []
            for site in sites:
                futures.append(self.executor.submit(self.post_comment, site))
            for future in futures:
                future.result()
            print(f"Backlink ekleme işlemi tamamlandı! {self.interval} saniye sonra tekrar çalışacak...")
            time.sleep(self.interval)

if __name__ == "__main__":
    backlink_bot = BacklinkAutomation("https://example.com", "./Llama-3.2-1B/model.safetensors", interval=86400, max_backlinks=100, min_pa=50, min_da=50)
    backlink_bot.run()
