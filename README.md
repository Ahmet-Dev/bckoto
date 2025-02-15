# bckoto - Backlink Otomation Tool
##  Ön Gereksinimler

Python Kurulumu

Python'un en az 3.8+ sürümünün sisteminizde yüklü olduğundan emin olun.

Gerekli Kütüphaneleri Yükleyin Aşağıdaki komutu çalıştırarak bağımlılıkları yükleyin:

pip install requests beautifulsoup4 googlesearch-python tldextract fake_useragent safetensors torch selenium pytesseract opencv-python

Chrome WebDriver Kurulumu

Selenium'un çalışması için Google Chrome WebDriver'ı sisteminize uygun şekilde yükleyin.

Llama-3.2-1B SafeTensor Modelini İndirin

Hugging Face'den Llama-3.2-1B modelini indirin ve ilgili klasöre yerleştirin:

git clone https://huggingface.co/meta-llama/Llama-3.2-1B

Modelin model.safetensors dosyasının tam konumunu kontrol edin.

# Test Adımları

Python Dosyanızı Çalıştırın

Eğer yukarıdaki adımları eksiksiz tamamladıysanız, Python dosyanızı terminalde şu komutla çalıştırabilirsiniz:

python backlink_automation.py

Eğer dosya farklı bir isimdeyse, komutu uygun dosya adıyla değiştirin.

## English

Python Installation

Make sure that you have at least 3.8+ version of Python installed on your system.

Install Required Libraries Install the dependencies by running the following command:

pip install requests beautifulsoup4 googlesearch-python tldextract fake_useragent safetensors torch selenium pytesseract opencv-python

Chrome WebDriver Installation

Install Google Chrome WebDriver accordingly on your system for Selenium to work.

Download Llama-3.2-1B SafeTensor Model

Download Llama-3.2-1B model from Hugging Face and place it in the relevant folder:

git clone https://huggingface.co/meta-llama/Llama-3.2-1B

Check the exact location of the model.safetensors file of the model.

# Test Steps

Run Your Python File

If you have completed the above steps, you can run your Python file in the terminal with the following command:

python backlink_automation.py

If the file has a different name, replace the command with the appropriate file name.

##  Genel Özellikler

Backlink içeriğini belirlenen konuya göre rastgele değiştirir.

Küçük bir dil modeli (Llama-3.2-1B SafeTensor) ile içerik üretir.

Sunucunun kendi URL’sini otomatik çeker ve backlink ekler.

SEO skoru yüksek siteleri DA ve PA değerlerini otomatik ölçerek belirler.

Spam siteleri engeller.

Google araması kullanarak forum ve blogları otomatik bulur.

CAPTCHA çözücüsü kullanarak doğrulama yapar (API kullanmaz).

Otomatik giriş gerektiren sitelerde kayıt olur ve giriş yapar.

Otomatik e-posta adresi oluşturur ve kullanıcı doğrulaması yapar.

Cronjob veya systemd ile çalıştırılabilir ve belirli aralıklarla backlink ekler.

JSON formatında backlink eklenen web sitelerini saklar ve aynı siteye 3 gün geçmeden tekrar ekleme yapmaz.

Backlink içeren siteleri kayıt eder ve gerektiğinde tekrar analiz eder.

Headless modda çalışarak performansı optimize eder (GUI açmadan çalıştırır).

Raporlama ve log dosyası tutar.

Otomatik captcha çözme (pytesseract + OCR ile).

⭐ Depoya yıldız vermeyi unutmayın! 😊 🚀

##  General Features

Randomly changes the backlink content according to the specified subject.

Generates content with a small language model (Llama-3.2-1B SafeTensor).

Automatically pulls the server's own URL and adds backlinks.

Determines sites with high SEO scores by automatically measuring DA and PA values.

Blocks spam sites.

Automatically finds forums and blogs using Google search.

Verifies using CAPTCHA solver (does not use API).

Registers and logs in sites that require automatic login.

Creates automatic e-mail addresses and verifies users.

Can be run with cronjob or systemd and adds backlinks at certain intervals.

Stores websites with backlinks added in JSON format and does not add them to the same site again within 3 days.

Records sites with backlinks and analyzes them again when necessary.

Optimizes performance by working in headless mode (runs without opening GUI).

Keeps reporting and log files.

Automatic captcha solving (with pytesseract + OCR).

⭐ Don't forget to star the project! 😊 🚀
