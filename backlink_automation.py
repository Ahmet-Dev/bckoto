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

    async def find_forums_and_blogs(self):
        search_query = "SEO forum OR blog site:com"
        found_sites = []
        tasks = []
        for url in search(search_query, num_results=self.max_backlinks):
            domain = tldextract.extract(url).registered_domain
            if domain not in self.spam_sites:
                found_sites.append(url)
        return found_sites

    def post_comment(self, forum_url):
        """ Yorum ekleyerek backlink gömmek için kullanılan fonksiyon """
        try:
            self.driver.get(forum_url)
            time.sleep(3)
            
            comment_section = self.driver.find_elements(By.NAME, "comment")
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
            print(f"Yorum ekleme başarısız: {e}")
            return False

    def site_requires_login(self, site_url):
        """ Site giriş gerektiriyor mu kontrol eder """
        self.driver.get(site_url)
        time.sleep(3)
        login_fields = self.driver.find_elements(By.NAME, "username")
        return len(login_fields) > 0

    def create_account_and_login(self, site_url):
        """ Otomatik kayıt ve giriş yapar """
        try:
            self.driver.get(site_url)
            time.sleep(3)
            username = f"user{random.randint(1000, 9999)}"
            password = "SecurePass123!"
            
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "login").click()
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Giriş başarısız: {e}")
        return False

    def run(self):
        while True:
            print("Forum ve blog siteleri aranıyor...")
            sites = asyncio.run(self.find_forums_and_blogs())
            print(f"Bulunan siteler: {sites}")
            for site in sites:
                if self.site_requires_login(site):
                    if self.create_account_and_login(site):
                        self.post_comment(site)
                else:
                    self.post_comment(site)
            print(f"Backlink ekleme işlemi tamamlandı! {self.interval} saniye sonra tekrar çalışacak...")
            time.sleep(self.interval)

# Kullanım
if __name__ == "__main__":
    backlink_bot = BacklinkAutomation("https://example.com", "./Llama-3.2-1B/model.safetensors", interval=86400, max_backlinks=100)
    backlink_bot.run()
