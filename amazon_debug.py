from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

url = "https://www.amazon.com.tr/Apple-iPhone-13-128-GB/dp/B09G9CHGHZ" # A typical expensive product (iPhone)

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--headless") 
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

print("Navigating to URL...")
driver.get(url)
time.sleep(10) # Sayfanın yüklenmesi için bekleme

print("Current URL:", driver.current_url)

body_text = driver.find_element(By.TAG_NAME, "body").text
with open("amazon_debug.txt", "w", encoding="utf-8") as f:
    f.write(body_text)
print("Body saved to amazon_debug.txt")

def satir_temizle(satir):
    yasakli_kelimeler = [
        "taksit", "isim", "baskı", "kargo", "numara", "bedel", "fark", 
        "üzeri", "alışveriş", "kupon", "puan", "hediye", "kazan", "fırsat", 
        "vade", "ayda", "peşin fiyatına", "aylık"
    ]
    if any(k in satir.lower() for k in yasakli_kelimeler):
        return None
        
    satir = re.sub(r"\b\d+\s*[xX]\s*\d+(?:\.\d{3})*(?:,\d{2})?\s*(?:TL|₺|TRY|tl|Tl|try)?", "", satir, flags=re.IGNORECASE)
    satir = re.sub(r"(\d+(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|TRY|tl|Tl|try)(?:'ye|ye|ya|'ya)?\s*(?:sepette\s*)?(?:ek\s*)?(?:indirim|kupon|puan|hediye)", "", satir, flags=re.IGNORECASE)
    return satir

lines = body_text.split('\n')
for i, line in enumerate(lines):
    temiz_line = satir_temizle(line)
    if temiz_line is None:
        continue
        
    tum_fiyatlar = re.findall(r"(\d+(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|TRY|tl|Tl|try)", temiz_line)
    if not tum_fiyatlar:
        tum_fiyatlar = re.findall(r"(\d+(?:\.\d{3})*(?:,\d{2}))", temiz_line)
        
    gecerli_fiyatlar = [f for f in tum_fiyatlar if 3 <= len(f.replace(".", "").split(",")[0]) <= 7]
    if gecerli_fiyatlar:
        print(f"Line {i}: {line}")
        print(f"  Geçerli fiyatlar: {gecerli_fiyatlar}")

driver.quit()
