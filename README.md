# bckoto
Backlink Otomation Tool

##Genel Özellikler

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

##General Features

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
