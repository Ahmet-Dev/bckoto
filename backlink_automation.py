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
# Your model file should be in a folder with the required config and tokenizer files.

# --- Selenium & CAPTCHA ---
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

import cv2
import pytesseract
from PIL import Image

# Logging configuration
BACKLINKS_FILE = "backlinks.json"
LOG_FILE = "errors.log"
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format='%(asctime)s %(message)s')

class BacklinkAutomation:
    def __init__(self, site_url, safetensor_model_path, interval=86400, max_backlinks=100, min_pa=50, min_da=50):
        self.site_url = site_url  # e.g. reference URL or main domain
        self.user_agent = UserAgent()
        # Keywords to be used for both search queries and content generation.
        self.keywords = ["seo", "digital marketing", "web development", "link building"]
        # Blacklisted (spam) sites
        self.spam_sites = ["example-spam.com", "blacklisted-site.net"]
        self.model_path = safetensor_model_path
        # Load Meta Llama 3.2-1B model and tokenizer
        self.model, self.tokenizer = self.load_model()
        self.interval = interval
        self.max_backlinks = max_backlinks
        self.min_pa = min_pa
        self.min_da = min_da
        self.backlinks_data = self.load_backlinks_data()
        self.lock = threading.Lock()
        self.driver = self.setup_driver()
        self.executor = ThreadPoolExecutor(max_workers=10)
        # Backlink URL to be appended to generated content
        self.backlink_url = "https://example.com"

    def network_delay(self):
        """Introduce a random delay between 1 and 2 seconds."""
        time.sleep(random.uniform(1, 2))

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
        Load the Llama model and tokenizer from the directory containing your checkpoint.
        Ensure that the directory (e.g., "Llama-3.2-1B") contains required files like config.json and a SentencePiece model file.
        """
        model_dir = os.path.dirname(self.model_path)
        # If you have a SentencePiece model (e.g., "tokenizer.model" or "spiece.model"), set its path:
        vocab_path = os.path.join(model_dir, "tokenizer.model")  # Adjust the filename if needed.
        if not os.path.exists(vocab_path):
            raise FileNotFoundError(f"Vocabulary file not found at: {vocab_path}")
        try:
            tokenizer = LlamaTokenizer.from_pretrained(
                model_dir,
                trust_remote_code=True,
                legacy=True,  # Use legacy behavior (or set legacy=False if your setup supports it)
                vocab_file=vocab_path
            )
            model = LlamaForCausalLM.from_pretrained(model_dir, trust_remote_code=True)
            return model, tokenizer
        except Exception as e:
            self.log_error(f"Model could not be loaded: {e}")
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
        """Prevent posting a backlink to the same site within 3 days."""
        last_post_time = self.backlinks_data.get(url)
        if last_post_time:
            return (time.time() - last_post_time) > (3 * 86400)
        return True

    async def find_forums_and_blogs(self):
        """
        Use the googlesearch module to create queries from self.keywords.
        For each keyword, generate "inurl:forum <keyword>" and "inurl:blog <keyword>" queries.
        Only forum and blog sites are collected.
        """
        search_queries = []
        for keyword in self.keywords:
            search_queries.append(f"inurl:forum {keyword}")
            search_queries.append(f"inurl:blog {keyword}")

        found_sites = set()
        for query in search_queries:
            try:
                self.network_delay()  # Delay between queries
                for url in search(query, num_results=25):
                    domain = tldextract.extract(url).registered_domain
                    if domain not in self.spam_sites and self.is_valid_site(domain):
                        found_sites.add(url)
            except Exception as e:
                self.log_error(f"Google search error ({query}): {e}")
        return list(found_sites)

    def get_external_link_count_from_search(self, domain, retries=3, delay=2):
        """
        Use googlesearch to search for the given domain and return the number of results
        as an estimate for external link count. Implements retry logic.
        """
        query = f"\"{domain}\""
        for attempt in range(retries):
            try:
                self.network_delay()
                results = list(search(query, num_results=50))
                return len(results)
            except Exception as e:
                self.log_error(f"Attempt {attempt+1}/{retries} - Error fetching search results for {domain}: {e}")
                time.sleep(delay)
        return 0

    def get_seo_score(self, domain):
        """
        Without using an external API, fetch the homepage of the given domain,
        then calculate SEO scores based on the word count and link count.
        
        Additionally, add the estimated external link count (from search) to the calculation.
        
        Calculation:
          - Effective Word Count = word_count + (external_count * 10)
          - Effective Link Count = (homepage_link_count + external_count) / 2
          - DA = (Effective Word Count / 150) * 50, capped at 100
          - PA = Effective Link Count * 5, capped at 100
        
        Returns:
            pa (int): Page Authority (0-100)
            da (int): Domain Authority (0-100)
        """
        url_options = [f"https://{domain}", f"http://{domain}"]
        for url in url_options:
            try:
                self.network_delay()
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    text = soup.get_text(separator=" ")
                    word_count = len(text.split())
                    links = soup.find_all("a")
                    homepage_link_count = len(links)
                    external_count = self.get_external_link_count_from_search(domain)
                    effective_word_count = word_count + (external_count * 10)
                    effective_link_count = (homepage_link_count + external_count) / 2.0
                    da = min(100, int((effective_word_count / 150) * 50))
                    pa = min(100, int(effective_link_count * 5))
                    return pa, da
            except Exception as e:
                self.log_error(f"SEO score calculation failed ({url}): {e}")
        return 0, 0

    def is_valid_site(self, domain):
        pa, da = self.get_seo_score(domain)
        return pa >= self.min_pa and da >= self.min_da

    def solve_captcha(self, image_path):
        """
        Solve CAPTCHA using OpenCV and pytesseract.
        """
        try:
            self.network_delay()
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray)
            return text.strip()
        except Exception as e:
            self.log_error(f"CAPTCHA could not be solved: {e}")
            return ""

    def generate_random_email(self):
        return f"user{random.randint(1000, 9999)}@tempmail.com"

    def generate_random_password(self):
        return "P@ssw0rd!" + str(random.randint(1000, 9999))

    def generate_title_content(self, keyword=None):
        """
        Generate an AI-supported title using the Llama model.
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
            self.log_error(f"Title generation failed: {e}")
            return f"Default Title about {keyword}"

    def generate_backlink_content(self, keyword=None):
        """
        Generate detailed, informative backlink content using the Llama model.
        Append the backlink URL to the generated content.
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
            full_content = f"{content}\n\nVisit our site: {self.backlink_url}"
            return full_content
        except Exception as e:
            self.log_error(f"Content generation failed: {e}")
            return f"This is a default comment about {keyword}. Visit {self.backlink_url} for more info."

    def create_account_and_login(self, site_url):
        """
        Use Selenium to create an account and log in on the target site.
        Fills out form fields, solves CAPTCHA, and logs in.
        """
        try:
            self.driver.get(site_url)
            time.sleep(3)
            
            email = self.generate_random_email()
            username = f"user{random.randint(1000, 9999)}"
            password = self.generate_random_password()
            
            # Example form fields: "email", "username", "password", "password_confirm"
            self.driver.find_element(By.NAME, "email").send_keys(email)
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "password_confirm").send_keys(password)
            
            # Solve CAPTCHA (XPath may need to be adjusted)
            captcha_img = self.driver.find_element(By.XPATH, "//img[contains(@class, 'captcha')]")
            captcha_img.screenshot("captcha.png")
            captcha_text = self.solve_captcha("captcha.png")
            self.driver.find_element(By.NAME, "captcha").send_keys(captcha_text)
            
            self.driver.find_element(By.NAME, "submit").click()
            time.sleep(3)
            print(f"{site_url}: Registration successful, logging in...")
            
            # Log in using the created credentials
            self.driver.find_element(By.NAME, "username").clear()
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "password").clear()
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "login").click()
            time.sleep(3)
            return True
        except Exception as e:
            self.log_error(f"Account creation and login failed ({site_url}): {e}")
        return False

    def find_comment_field(self):
        """
        Automatically locate the comment input field on the page.
        First, try to find an element with name="comment".
        If not found, scan through all textareas and input elements for attributes containing "comment".
        """
        try:
            return self.driver.find_element(By.NAME, "comment")
        except:
            pass
        # Check all textareas
        textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
        for textarea in textareas:
            try:
                if any(x in (textarea.get_attribute("placeholder") or "").lower() for x in ["comment"]) or \
                   any(x in (textarea.get_attribute("name") or "").lower() for x in ["comment"]) or \
                   any(x in (textarea.get_attribute("class") or "").lower() for x in ["comment"]):
                    return textarea
            except Exception as e:
                self.log_error(f"Comment field detection error: {e}")
        # As a last resort, check input elements
        inputs = self.driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            try:
                if any(x in (inp.get_attribute("placeholder") or "").lower() for x in ["comment"]) or \
                   any(x in (inp.get_attribute("name") or "").lower() for x in ["comment"]) or \
                   any(x in (inp.get_attribute("class") or "").lower() for x in ["comment"]):
                    return inp
            except Exception as e:
                self.log_error(f"Comment field detection error: {e}")
        return None

    def find_submit_comment_button(self):
        """
        Automatically locate the comment submission button.
        First, try to find an element with name="submit_comment".
        If not found, search for a button with text containing "submit" or an input with type="submit".
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
                self.log_error(f"Submit button detection error: {e}")
        submits = self.driver.find_elements(By.XPATH, "//input[@type='submit']")
        if submits:
            return submits[0]
        return None

    def post_comment(self, site_url):
        """
        After account creation and login, use AI to generate a title and comment content,
        then automatically locate the comment field and submit the comment.
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
                self.log_error(f"{site_url}: Comment field not found.")
                return False
            comment_field.clear()
            comment_field.send_keys(full_comment)
            
            submit_button = self.find_submit_comment_button()
            if not submit_button:
                self.log_error(f"{site_url}: Submit comment button not found.")
                return False
            submit_button.click()
            time.sleep(3)
            print(f"{site_url}: Comment successfully posted.")
            return True
        except Exception as e:
            self.log_error(f"Comment posting failed ({site_url}): {e}")
            return False

    def run(self):
        """
        Periodically:
         - Find only blog and forum sites via googlesearch.
         - For valid sites (based on SEO score), create an account, log in, and post a comment.
         - Record the posting timestamp in a JSON file to avoid reposting within 3 days.
         - All operations include network delays and are executed in parallel.
        """
        while True:
            print("Searching for blog and forum sites...")
            try:
                sites = asyncio.run(self.find_forums_and_blogs())
            except Exception as e:
                self.log_error(f"Forum/blog search error: {e}")
                sites = []
            print(f"Found sites: {sites}")
            
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
            print(f"Operations complete. Retrying in {self.interval} seconds...")
            time.sleep(self.interval)


if __name__ == "__main__":
    # Example usage:
    # site_url: Target domain or reference URL (e.g., "https://example.com")
    # safetensor_model_path: Full path to your model file (e.g., "D:/Otomation/bckoto/Llama-3.2-1B/model.safetensors")
    backlink_bot = BacklinkAutomation(
        "https://example.com",
        "Llama-3.2-1B/model.safetensors",  # Use a valid local path without a leading slash if relative
        interval=86400,         # Run every 24 hours
        max_backlinks=100,
        min_pa=50,
        min_da=50
    )
    backlink_bot.run()
