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

    async def find_forums_and_blogs(self):
        search_queries = [
            "inurl:forum SEO",
            "inurl:forum digital marketing",
            "inurl:forum web development",
            "inurl:blog link building"
        ]
        found_sites = set()
        for query in search_queries:
            for url in search(query, num_results=25):
                domain = tldextract.extract(url).registered_domain
                if domain not in self.spam_sites and self.is_valid_site(domain):
                    found_sites.add(url)
        return list(found_sites)

    def get_seo_score(self, domain):
        try:
            response = requests.get(f"https://seo-api.com/get-score?domain={domain}")
            if response.status_code == 200:
                data = response.json()
                return data.get("pa", 0), data.get("da", 0)
        except Exception as e:
            self.log_error(f"SEO skoru alınamadı: {e}")
        return 0, 0

    def is_valid_site(self, domain):
        pa, da = self.get_seo_score(domain)
        return pa >= self.min_pa and da >= self.min_da

    def solve_captcha(self, image_path):
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        return text.strip()

    def generate_random_email(self):
        return f"user{random.randint(1000, 9999)}@tempmail.com"

    def generate_random_password(self):
        return "P@ssw0rd!" + str(random.randint(1000, 9999))

    def create_account_and_login(self, site_url):
        try:
            self.driver.get(site_url)
            time.sleep(3)
            
            email = self.generate_random_email()
            username = f"user{random.randint(1000, 9999)}"
            password = self.generate_random_password()
            
            self.driver.find_element(By.NAME, "email").send_keys(email)
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "password_confirm").send_keys(password)
            
            captcha_img = self.driver.find_element(By.XPATH, "//img[@class='captcha']")
            captcha_img.screenshot("captcha.png")
            captcha_text = self.solve_captcha("captcha.png")
            
            self.driver.find_element(By.NAME, "captcha").send_keys(captcha_text)
            self.driver.find_element(By.NAME, "submit").click()
            
            time.sleep(3)
            print("Kayıt başarılı, giriş yapılıyor...")
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "login").click()
            time.sleep(3)
            return True
        except Exception as e:
            self.log_error(f"Otomatik kayıt ve giriş başarısız: {e}")
        return False

    def run(self):
        while True:
            print("Forum ve blog siteleri aranıyor...")
            sites = asyncio.run(self.find_forums_and_blogs())
            print(f"Bulunan siteler: {sites}")
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.create_account_and_login, site) for site in sites]
                for future in futures:
                    if future.result():
                        executor.submit(self.post_comment, site)
            
            time.sleep(self.interval)

if __name__ == "__main__":
    backlink_bot = BacklinkAutomation("https://example.com", "./Llama-3.2-1B/model.safetensors", interval=86400, max_backlinks=100, min_pa=50, min_da=50)
    backlink_bot.run()
