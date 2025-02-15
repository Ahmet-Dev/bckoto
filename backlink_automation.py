import os
import time
import json
import random
import logging
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from googlesearch import search
import tldextract
from fake_useragent import UserAgent

# --- AI Model (Meta Llama 3.2-1B) ---
from transformers import LlamaForCausalLM, LlamaTokenizer
# Model dosyanız "/Llama-3.2-1B/model.safetensors" şeklinde olmalı.
# Model klasöründe config ve tokenizer dosyalarının bulunması gerekmektedir.

# --- Selenium & CAPTCHA ---
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

import cv2
import pytesseract
from PIL import Image

# Loglama ayarları
BACKLINKS_FILE = "backlinks.json"
LOG_FILE = "errors.log"
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format='%(asctime)s %(message)s')


class BacklinkAutomation:
    def __init__(self, site_url, safetensor_model_path, interval=86400, max_backlinks=100, min_pa=50, min_da=50):
        self.site_url = site_url  # Örneğin, referans URL veya ana domain
        self.user_agent = UserAgent()
        # Kullanılacak anahtar kelimeler (aynı zamanda arama sorgularını oluşturmak için de kullanılacak)
        self.keywords = ["seo", "digital marketing", "web development", "link building"]
        # Kara liste (spam) siteler
        self.spam_sites = ["example-spam.com", "blacklisted-site.net"]
        self.model_path = safetensor_model_path
        # Meta Llama 3.2-1B modelini ve tokenizer'ı yükle
        self.model, self.tokenizer = self.load_model()
        self.interval = interval
        self.max_backlinks = max_backlinks
        self.min_pa = min_pa
        self.min_da = min_da
        self.backlinks_data = self.load_backlinks_data()
        self.lock = threading.Lock()
        self.driver = self.setup_driver()
        self.executor = ThreadPoolExecutor(max_workers=10)
        # Backlink URL'si: Yorum içeriğine eklenecek
        self.backlink_url = "https://example.com"

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
        """
        Llama modelini ve tokenizer'ı, model dosyasının bulunduğu klasörden yükler.
        Örneğin, model dosyanız "/Llama-3.2-1B/model.safetensors" ise klasör "/Llama-3.2-1B" kullanılır.
        """
        model_dir = os.path.dirname(self.model_path)
        try:
            tokenizer = LlamaTokenizer.from_pretrained(model_dir, trust_remote_code=True)
            model = LlamaForCausalLM.from_pretrained(model_dir, trust_remote_code=True)
            return model, tokenizer
        except Exception as e:
            self.log_error(f"Model yüklenemedi: {e}")
            raise

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
        """Aynı siteye 3 gün içerisinde tekrar backlink eklenmesini engeller."""
        last_post_time = self.backlinks_data.get(url)
        if last_post_time:
            return (time.time() - last_post_time) > (3 * 86400)
        return True

    async def find_forums_and_blogs(self):
        """
        Googlesearch modülü kullanılarak, self.keywords listesindeki her anahtar kelime için
        "inurl:forum <keyword>" ve "inurl:blog <keyword>" sorguları oluşturulur.
        Sadece forum ve blog siteleri toplanır.
        """
        search_queries = []
        for keyword in self.keywords:
            search_queries.append(f"inurl:forum {keyword}")
            search_queries.append(f"inurl:blog {keyword}")

        found_sites = set()
        for query in search_queries:
            try:
                for url in search(query, num_results=25):
                    domain = tldextract.extract(url).registered_domain
                    if domain not in self.spam_sites and self.is_valid_site(domain):
                        found_sites.add(url)
            except Exception as e:
                self.log_error(f"Google arama hatası ({query}): {e}")
        return list(found_sites)

    def get_seo_score(self, domain):
        """
        Dış API kullanmadan, verilen domain’in ana sayfasını çekip,
        sayfadaki kelime sayısı ve link sayısına dayalı orta seviyede bir hesaplama yapar.
        Örnek hesaplama:
          - DA: (word_count / 150) * 50 (maksimum 100)
          - PA: (link_count * 5) (maksimum 100)
        """
        url_options = [f"https://{domain}", f"http://{domain}"]
        for url in url_options:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    text = soup.get_text(separator=" ")
                    word_count = len(text.split())
                    links = soup.find_all("a")
                    link_count = len(links)
                    da = min(100, int((word_count / 150) * 50))
                    pa = min(100, int(link_count * 5))
                    return pa, da
            except Exception as e:
                self.log_error(f"SEO skor hesaplanamadı ({url}): {e}")
        return 0, 0

    def is_valid_site(self, domain):
        pa, da = self.get_seo_score(domain)
        return pa >= self.min_pa and da >= self.min_da

    def solve_captcha(self, image_path):
        """
        OpenCV ve pytesseract kullanarak CAPTCHA metnini çözer.
        """
        try:
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray)
            return text.strip()
        except Exception as e:
            self.log_error(f"CAPTCHA çözülemedi: {e}")
            return ""

    def generate_random_email(self):
        return f"user{random.randint(1000, 9999)}@tempmail.com"

    def generate_random_password(self):
        return "P@ssw0rd!" + str(random.randint(1000, 9999))

    def generate_title_content(self, keyword=None):
        """
        Llama modeli kullanarak AI destekli başlık (title_content) üretir.
        """
        if not keyword:
            keyword = random.choice(self.keywords)
        prompt = f"Write a catchy title about {keyword}:"
        try:
            input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids
            outputs = self.model.generate(
                input_ids,
                max_new_tokens=10,
                do_sample=True,
                temperature=0.7
            )
            title = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return title
        except Exception as e:
            self.log_error(f"Başlık üretilemedi: {e}")
            return f"Default Title about {keyword}"

    def generate_backlink_content(self, keyword=None):
        """
        Llama modeli kullanılarak, belirlenen konuya göre detaylı ve bilgilendirici backlink içeriği üretir.
        Oluşturulan içeriğin sonuna backlink URL'si eklenir.
        """
        if not keyword:
            keyword = random.choice(self.keywords)
        prompt = f"Write a detailed and informative comment about {keyword}:"
        try:
            input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids
            outputs = self.model.generate(
                input_ids,
                max_new_tokens=60,
                do_sample=True,
                temperature=0.7
            )
            content = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Backlink URL'sini metne ekleyelim:
            full_content = f"{content}\n\nVisit our site: {self.backlink_url}"
            return full_content
        except Exception as e:
            self.log_error(f"İçerik üretilemedi: {e}")
            return f"This is a default comment about {keyword}. Visit {self.backlink_url} for more info."

    def create_account_and_login(self, site_url):
        """
        Selenium kullanarak otomatik hesap oluşturma ve giriş yapma işlemini gerçekleştirir.
        Form alanı isimleri, CAPTCHA XPath’i ve e-posta doğrulama adımları örnek olarak verilmiştir.
        """
        try:
            self.driver.get(site_url)
            time.sleep(3)
            
            email = self.generate_random_email()
            username = f"user{random.randint(1000, 9999)}"
            password = self.generate_random_password()
            
            # Form alanları örnek: "email", "username", "password", "password_confirm"
            self.driver.find_element(By.NAME, "email").send_keys(email)
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "password_confirm").send_keys(password)
            
            # CAPTCHA çözümü (XPath siteye göre uyarlanmalı)
            captcha_img = self.driver.find_element(By.XPATH, "//img[contains(@class, 'captcha')]")
            captcha_img.screenshot("captcha.png")
            captcha_text = self.solve_captcha("captcha.png")
            self.driver.find_element(By.NAME, "captcha").send_keys(captcha_text)
            
            self.driver.find_element(By.NAME, "submit").click()
            time.sleep(3)
            print(f"{site_url}: Kayıt başarılı, giriş yapılıyor...")
            
            # Giriş adımları (form alanları örnek; siteye göre düzenleyin)
            self.driver.find_element(By.NAME, "username").clear()
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "password").clear()
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "login").click()
            time.sleep(3)
            return True
        except Exception as e:
            self.log_error(f"Otomatik kayıt ve giriş başarısız ({site_url}): {e}")
        return False

    def find_comment_field(self):
        """
        Sayfadaki yorum formu alanını otomatik olarak tespit eder.
        Önce name="comment" aranır, bulunamazsa textarea ve input elementleri placeholder, name veya class içeriğine bakılır.
        """
        try:
            return self.driver.find_element(By.NAME, "comment")
        except:
            pass
        # Tüm textarea'ları kontrol et
        textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
        for textarea in textareas:
            try:
                if any(x in (textarea.get_attribute("placeholder") or "").lower() for x in ["comment"]) or \
                   any(x in (textarea.get_attribute("name") or "").lower() for x in ["comment"]) or \
                   any(x in (textarea.get_attribute("class") or "").lower() for x in ["comment"]):
                    return textarea
            except Exception as e:
                self.log_error(f"Yorum alanı tespit hatası: {e}")
        # Son çare: input alanlarını kontrol et
        inputs = self.driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            try:
                if any(x in (inp.get_attribute("placeholder") or "").lower() for x in ["comment"]) or \
                   any(x in (inp.get_attribute("name") or "").lower() for x in ["comment"]) or \
                   any(x in (inp.get_attribute("class") or "").lower() for x in ["comment"]):
                    return inp
            except Exception as e:
                self.log_error(f"Yorum alanı tespit hatası: {e}")
        return None

    def find_submit_comment_button(self):
        """
        Sayfadaki yorum gönderme butonunu otomatik olarak tespit eder.
        İlk olarak name="submit_comment", ardından buton metni veya type submit kontrolü yapılır.
        """
        try:
            return self.driver.find_element(By.NAME, "submit_comment")
        except:
            pass
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            try:
                if btn.text and "submit" in btn.text.lower():
                    return btn
            except Exception as e:
                self.log_error(f"Yorum butonu tespit hatası: {e}")
        submits = self.driver.find_elements(By.XPATH, "//input[@type='submit']")
        if submits:
            return submits[0]
        return None

    def post_comment(self, site_url):
        """
        Otomatik hesap oluşturma ve giriş sonrası, AI destekli üretilen başlık ve içerikle yorum (backlink) gönderir.
        Yorum form alanı ve gönder butonu otomatik olarak tespit edilir.
        """
        try:
            self.driver.get(site_url)
            time.sleep(3)
            
            keyword = random.choice(self.keywords)
            title = self.generate_title_content(keyword)
            content = self.generate_backlink_content(keyword)
            full_comment = f"{title}\n\n{content}"
            
            comment_field = self.find_comment_field()
            if not comment_field:
                self.log_error(f"{site_url}: Yorum alanı bulunamadı.")
                return False
            comment_field.clear()
            comment_field.send_keys(full_comment)
            
            submit_button = self.find_submit_comment_button()
            if not submit_button:
                self.log_error(f"{site_url}: Yorum gönder butonu bulunamadı.")
                return False
            submit_button.click()
            time.sleep(3)
            print(f"{site_url}: Yorum başarıyla gönderildi.")
            return True
        except Exception as e:
            self.log_error(f"Yorum gönderilemedi ({site_url}): {e}")
            return False

    def run(self):
        """
        Belirli aralıklarla:
         - Googlesearch ile yalnızca blog ve forum sitelerini bulur.
         - SEO kontrolü yaparak uygun sitelerde otomatik kayıt/giriş ve yorum (backlink) gönderimi gerçekleştirir.
         - Gönderilen backlinkler JSON dosyasına zaman damgasıyla kaydedilir.
         - Paralel işlem ve hata loglaması sağlanır.
        """
        while True:
            print("Blog ve forum siteleri aranıyor...")
            try:
                sites = asyncio.run(self.find_forums_and_blogs())
            except Exception as e:
                self.log_error(f"Forum/blog arama hatası: {e}")
                sites = []
            print(f"Bulunan siteler: {sites}")
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for site in sites:
                    if not self.should_post_backlink(site):
                        continue
                    futures[site] = executor.submit(self.create_account_and_login, site)
                for site, future in futures.items():
                    if future.result():
                        if executor.submit(self.post_comment, site).result():
                            with self.lock:
                                self.backlinks_data[site] = time.time()
            
            self.save_backlinks_data()
            print(f"İşlemler tamamlandı. {self.interval} saniye sonra tekrar deneniyor...")
            time.sleep(self.interval)


if __name__ == "__main__":
    # site_url: Hedef domain veya referans URL (örneğin, "https://example.com")
    # safetensor_model_path: Model dosyanızın tam yolu (örneğin, "/Llama-3.2-1B/model.safetensors")
    backlink_bot = BacklinkAutomation(
        "https://example.com",
        "/Llama-3.2-1B/model.safetensors",  # Kullanılan model dosyası
        interval=86400,         # 24 saatte bir çalışır
        max_backlinks=100,
        min_pa=50,
        min_da=50
    )
    backlink_bot.run()
