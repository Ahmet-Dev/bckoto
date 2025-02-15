import requests
import random
import time
import json
import os
import asyncio
import threading
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

BACKLINKS_FILE = "backlinks.json"

class BacklinkAutomation:
    def __init__(self, site_url, safetensor_model_path, interval=86400, max_backlinks=100):
        self.site_url = site_url
        self.user_agent = UserAgent()
        self.keywords = ["seo", "digital marketing", "web development", "link building"]
        self.spam_sites = ["example-spam.com", "blacklisted-site.net"]
        self.model_path = safetensor_model_path
        self.model = self.load_model()
        self.interval = interval
        self.max_backlinks = max_backlinks
        self.backlinks_data = self.load_backlinks_data()
        self.lock = threading.Lock()
        self.driver = self.setup_driver()

    def setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=options)

    def load_model(self):
        if os.path.exists(self.model_path):
            return load_file(self.model_path)
        else:
            raise FileNotFoundError("SafeTensor modeli bulunamadı!")

    def load_backlinks_data(self):
        if os.path.exists(BACKLINKS_FILE):
            with open(BACKLINKS_FILE, "r") as file:
                return json.load(file)
        return {}

    def save_backlinks_data(self):
        with self.lock:
            with open(BACKLINKS_FILE, "w") as file:
                json.dump(self.backlinks_data, file, indent=4)

    def should_post_backlink(self, url):
        last_post_time = self.backlinks_data.get(url)
        if last_post_time:
            return (time.time() - last_post_time) > (3 * 86400)
        return True

    def generate_backlink_content(self, keyword):
        input_data = torch.tensor([hash(keyword) % 100])
        output = self.model['output_weights'] @ input_data
        return f"{keyword} hakkında uzman içeriği için {self.site_url} adresine göz atın!"
    
    def generate_title_content(self, keyword):
        input_data = torch.tensor([hash(keyword) % 100])
        output = self.model['output_weights'] @ input_data
        return f"{keyword} ile İlgili En İyi Kaynaklar!"

    async def get_seo_score(self, domain):
        try:
            response = await asyncio.to_thread(requests.get, f"https://seo-api.com/get-score?domain={domain}")
            if response.status_code == 200:
                data = response.json()
                return data.get("pa", 0), data.get("da", 0)
        except Exception as e:
            print(f"SEO skoru alınamadı: {e}")
        return 0, 0

    async def is_valid_site(self, domain):
        if domain in self.spam_sites:
            return False
        pa, da = await self.get_seo_score(domain)
        return pa > 50 and da > 50

    async def find_forums_and_blogs(self):
        search_query = "SEO forum OR blog site:com"
        found_sites = []
        tasks = []
        for url in search(search_query, num_results=self.max_backlinks):
            domain = tldextract.extract(url).registered_domain
            tasks.append(self.is_valid_site(domain))
        results = await asyncio.gather(*tasks)
        for idx, valid in enumerate(results):
            if valid and self.should_post_backlink(search_query):
                found_sites.append(search_query)
        return found_sites[:self.max_backlinks]

    def post_backlink_thread(self, url):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.post_backlink(url))

    async def post_backlink(self, url):
        try:
            self.driver.get(url)
            await asyncio.sleep(3)
            keyword = random.choice(self.keywords)
            backlink_content = self.generate_backlink_content(keyword)
            title_content = self.generate_title_content(keyword)
            self.driver.find_element(By.NAME, "post_title").send_keys(title_content)
            self.driver.find_element(By.NAME, "post_content").send_keys(backlink_content + f"\n\nDaha fazla bilgi için: {self.site_url}")
            self.driver.find_element(By.NAME, "submit").click()
            print(f"Backlink başarıyla eklendi: {url}")
            with self.lock:
                self.backlinks_data[url] = time.time()
                self.save_backlinks_data()
            return True
        except Exception as e:
            print(f"Hata: {e}")
        return False

    def run(self):
        while True:
            print("Forum ve blog siteleri aranıyor...")
            sites = asyncio.run(self.find_forums_and_blogs())
            print(f"Bulunan siteler: {sites}")
            threads = []
            for site in sites:
                thread = threading.Thread(target=self.post_backlink_thread, args=(site,))
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join()
            print(f"Backlink ekleme işlemi tamamlandı! {self.interval} saniye sonra tekrar çalışacak...")
            time.sleep(self.interval)

# Kullanım
if __name__ == "__main__":
    backlink_bot = BacklinkAutomation("https://example.com", "./Llama-3.2-1B/model.safetensors", interval=86400, max_backlinks=100)
    backlink_bot.run()
