from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

url = "https://ty.gl/y9894fue6zd7w"

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

if "trendyol.com" in driver.current_url:
    print("Trendyol logic executing...")
    normal = None
    indirimli = None
    try:
        org_el = driver.find_element(By.CLASS_NAME, "prc-org")
        print("prc-org text:", org_el.text)
        org_match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2}))", org_el.text)
        if org_match: normal = org_match.group(1)
    except Exception as e: 
        print("prc-org Exception:", e)
    
    try:
        dsc_el = driver.find_element(By.CLASS_NAME, "prc-dsc")
        print("prc-dsc text:", dsc_el.text)
        dsc_match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2}))", dsc_el.text)
        if dsc_match: indirimli = dsc_match.group(1)
    except Exception as e: 
        print("prc-dsc Exception:", e)
        
    print("Trendyol özel logic sonucu: normal:", normal, "indirimli:", indirimli)
    if normal and indirimli:
        print("RETURN: ", {"normal_fiyat": normal, "indirimli_fiyat": indirimli})
    elif indirimli and not normal:
        print("RETURN: ", {"normal_fiyat": indirimli, "indirimli_fiyat": None})

body_text = driver.find_element(By.TAG_NAME, "body").text
with open("body_debug.txt", "w", encoding="utf-8") as f:
    f.write(body_text)
print("Body saved to body_debug.txt")

lines = body_text.split('\n')
for i, line in enumerate(lines):
    if any(k in line.lower() for k in ["taksit", "isim", "baskı", "kargo", "numara", "bedel", "fark", "üzeri", "alışveriş", "kupon", "puan", "hediye", "kazan", "fırsat"]):
        continue
        
    temiz_line = re.sub(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|TRY|tl|Tl|try)(?:'ye|ye|ya|'ya)?\s*(?:sepette\s*)?(?:ek\s*)?(?:indirim|kupon|puan|hediye)", "", line, flags=re.IGNORECASE)
    
    tum_fiyatlar = re.findall(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|TRY|tl|Tl|try)", temiz_line)
    if not tum_fiyatlar:
        tum_fiyatlar = re.findall(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2}))", temiz_line)
        
    gecerli_fiyatlar = [f for f in tum_fiyatlar if 3 <= len(f.replace(".", "").split(",")[0]) <= 7]
    if gecerli_fiyatlar:
        print(f"Line {i}: {line}")
        print(f"  Geçerli fiyatlar: {gecerli_fiyatlar}")

driver.quit()
