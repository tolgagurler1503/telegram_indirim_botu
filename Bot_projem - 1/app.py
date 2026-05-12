import telebot
import sqlite3
import time
import re
import threading
import schedule
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- TELEGRAM BİLGİLERİN ---
TOKEN = "8727518790:AAHJDw8z0NSh9iJCh0CvIObyCFXlpV-M5RM"
bot = telebot.TeleBot(TOKEN)

# Veritabanı başlatma (Eğer yoksa bot_db.sqlite oluşturur)
def init_db():
    conn = sqlite3.connect('bot_db.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS urunler
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  link TEXT, 
                  guncel_fiyat TEXT, 
                  chat_id TEXT)''')
    
    # Yeni sütunları eklemeyi dene (eski tabloyu bozmamak için)
    try:
        c.execute("ALTER TABLE urunler ADD COLUMN ilk_fiyat TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE urunler ADD COLUMN eklenme_tarihi TEXT")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

def fiyat_cek(url):
    options = Options()
    options.add_argument("--start-maximized")
    # Arka planda açılması için Headless modu ekledik:
    options.add_argument("--headless") 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(url)
        time.sleep(10) # Sayfanın yüklenmesi için bekleme
        
        # Trendyol için özel deneme (Sadece fiyatları daha kolay bulmak için, bulamazsa genel algoritmaya geçer)
        if "trendyol.com" in driver.current_url:
            normal = None
            indirimli = None
            try:
                org_el = driver.find_element(By.CLASS_NAME, "prc-org")
                org_match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2}))", org_el.text)
                if org_match: normal = org_match.group(1)
            except Exception: pass
            
            try:
                dsc_el = driver.find_element(By.CLASS_NAME, "prc-dsc")
                dsc_match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2}))", dsc_el.text)
                if dsc_match: indirimli = dsc_match.group(1)
            except Exception: pass
            
            if normal and indirimli:
                driver.quit()
                return {"normal_fiyat": normal, "indirimli_fiyat": indirimli}
            elif indirimli and not normal:
                driver.quit()
                return {"normal_fiyat": indirimli, "indirimli_fiyat": None}
        
        # Amazon için özel deneme (Amazon fiyatları genelde a-offscreen içinde tam olarak bulunur)
        if "amazon.com.tr" in driver.current_url or "amazon.com" in driver.current_url:
            try:
                # Amazon'un gizli ama tam fiyat içeren elementlerini bulmaya çalış
                offscreen_prices = driver.find_elements(By.CSS_SELECTOR, ".a-price .a-offscreen")
                amazon_fiyatlar = []
                for p in offscreen_prices:
                    p_text = p.get_attribute("textContent")
                    if p_text:
                        match = re.search(r"(\d+(?:\.\d{3})*(?:,\d{2})?)", p_text)
                        if match:
                            amazon_fiyatlar.append(match.group(1))
                
                if amazon_fiyatlar:
                    # Amazon'da genellikle ilk fiyat asıl fiyattır, ikinci varsa o indirimli olabilir (veya tam tersi)
                    # Ancak biz burada en mantıklı olanı seçelim.
                    if len(amazon_fiyatlar) >= 2:
                        f1 = parse_fiyat(amazon_fiyatlar[0])
                        f2 = parse_fiyat(amazon_fiyatlar[1])
                        if f1 > f2:
                            driver.quit()
                            return {"normal_fiyat": amazon_fiyatlar[0], "indirimli_fiyat": amazon_fiyatlar[1]}
                        else:
                            driver.quit()
                            return {"normal_fiyat": amazon_fiyatlar[0], "indirimli_fiyat": None}
                    else:
                        driver.quit()
                        return {"normal_fiyat": amazon_fiyatlar[0], "indirimli_fiyat": None}
            except Exception:
                pass

        # Genel Akıllı Fiyat Algoritması (Tüm markalar ve siteler için geçerli)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = body_text.split('\n')
        
        def satir_temizle(satir):
            # 1. Taksit, forma yazdırma, kampanya, teknik özellik gibi kelimeler içeren satırları tamamen reddet
            yasakli_kelimeler = [
                "taksit", "isim", "baskı", "kargo", "numara", "bedel", "fark", 
                "üzeri", "alışveriş", "kupon", "puan", "hediye", "kazan", "fırsat", 
                "vade", "ayda", "peşin fiyatına", "peşin", "pesin", "aylık", "dpi", "sensör", "sensor",
                "hz", "mah", "mhz", "watt", "fps", "çözünürlük", "piksel", "pixel", "rpm",
                "gb", "tb", "mb", "kg", "gr", "litre", "ml", "cm", "mm", "volt", "amper",
                "inç", "inch", "kwh", "btu", "devir", "model", "kod", "sn", "saniye"
            ]
            if any(k in satir.lower() for k in yasakli_kelimeler):
                return None
                
            # 2. "3x 799 TL" veya "6 x 400 TL" veya "x 1.557 TL" gibi taksit ifadelerini (x veya X içeren fiyatları) tamamen sil
            satir = re.sub(r"(?:\b\d+\s*)?[xX]\s*\d+(?:\.\d{3})*(?:,\d{2})?\s*(?:TL|₺|TRY|tl|Tl|try)?", "", satir, flags=re.IGNORECASE)
            
            # 3. "250 TL indirim" veya "150 TL kupon" gibi doğrudan indirim TUTARLARINI sil (fiyat sanılmasını önler)
            satir = re.sub(r"(\d+(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|TRY|tl|Tl|try)(?:'ye|ye|ya|'ya)?\s*(?:sepette\s*)?(?:ek\s*)?(?:indirim|kupon|puan|hediye)", "", satir, flags=re.IGNORECASE)
            
            return satir
            
        for i, line in enumerate(lines):
            temiz_line = satir_temizle(line)
            if temiz_line is None:
                continue
                
            # 1. İçinde TL, ₺ olan (ondalıklı veya ondalıksız) kesin fiyatlar (Örn: 3.500 TL, 1.250,50 ₺)
            tum_fiyatlar = re.findall(r"(\d+(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|TRY|tl|Tl|try)", temiz_line)
            
            # 2. Eğer satırda TL yoksa, sadece KURUŞLU olan (,\d{2}) formatı kabul et. Bu, 25.000 gibi model/teknik sayıların fiyat sanılmasını büyük ölçüde engeller.
            if not tum_fiyatlar:
                # İçinde nokta olabilen ama KESİNLİKLE virgül ve 2 hane ile biten sayıları ara (Örn: 1.500,00 veya 49,90)
                tum_fiyatlar = re.findall(r"(\d+(?:\.\d{3})*,\d{2})", temiz_line)
                
            gecerli_fiyatlar = [f for f in tum_fiyatlar if 3 <= len(f.replace(".", "").split(",")[0]) <= 7]
            
            if gecerli_fiyatlar:
                fiyat1_str = gecerli_fiyatlar[0]
                fiyat1 = parse_fiyat(fiyat1_str)
                
                # 1. İhtimal: Eski fiyat ve Yeni fiyat AYNI SATIRDA yan yana yazılmış olabilir
                if len(gecerli_fiyatlar) >= 2:
                    fiyat2_str = gecerli_fiyatlar[1]
                    fiyat2 = parse_fiyat(fiyat2_str)
                    
                    if fiyat1 > fiyat2 and (fiyat2 / fiyat1) > 0.2:
                        driver.quit()
                        return {"normal_fiyat": fiyat1_str, "indirimli_fiyat": fiyat2_str}
                    elif fiyat2 > fiyat1 and (fiyat1 / fiyat2) > 0.2:
                        driver.quit()
                        return {"normal_fiyat": fiyat2_str, "indirimli_fiyat": fiyat1_str}
                
                # 2. İhtimal: Eski fiyat üstte, Yeni fiyat ALT SATIRLARDA yazılmış olabilir
                for j in range(1, 4):  # Sonraki 3 satıra kadar bak
                    if i + j < len(lines):
                        temiz_alt = satir_temizle(lines[i+j])
                        if temiz_alt is None:
                            continue
                            
                        sonraki_fiyatlar = re.findall(r"(\d+(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|TRY|tl|Tl|try)", temiz_alt)
                        if not sonraki_fiyatlar:
                            sonraki_fiyatlar = re.findall(r"(\d+(?:\.\d{3})+(?:,\d{2})?|\d+,\d{2})", temiz_alt)
                            
                        sonraki_gecerli = [f for f in sonraki_fiyatlar if 3 <= len(f.replace(".", "").split(",")[0]) <= 7]
                        
                        if sonraki_gecerli:
                            fiyat2_str = sonraki_gecerli[0]
                            fiyat2 = parse_fiyat(fiyat2_str)
                            
                            if fiyat1 > fiyat2 and (fiyat2 / fiyat1) > 0.2:
                                driver.quit()
                                return {"normal_fiyat": fiyat1_str, "indirimli_fiyat": fiyat2_str}
                            elif fiyat2 > fiyat1 and (fiyat1 / fiyat2) > 0.2:
                                driver.quit()
                                return {"normal_fiyat": fiyat2_str, "indirimli_fiyat": fiyat1_str}
                            break
                
                # İndirimli bir fiyat bulamadıysa, ilk gördüğü fiyat ana (tek) fiyattır.
                driver.quit()
                return {"normal_fiyat": fiyat1_str, "indirimli_fiyat": None}
                
        driver.quit()
        return None
    except Exception as e:
        print(f"Hata oluştu: {e}")
        driver.quit()
        return None

# String olan fiyatı küçüklük büyüklük karşılaştırması için sayıya (float) çevirme fonksiyonu
def parse_fiyat(fiyat_str):
    try:
        # "1.245,50" -> "1245.50" -> 1245.50
        return float(fiyat_str.replace('.', '').replace(',', '.'))
    except:
        return 0.0

def isleyip_cevapla(message, link, chat_id):
    fiyat_bilgisi = fiyat_cek(link)
    if fiyat_bilgisi:
        # Satış fiyatı (guncel fiyat), kullanıcının ödeyeceği en son fiyattır
        fiyat = fiyat_bilgisi["indirimli_fiyat"] if fiyat_bilgisi["indirimli_fiyat"] else fiyat_bilgisi["normal_fiyat"]
        
        conn = sqlite3.connect('bot_db.sqlite')
        c = conn.cursor()
        
        # Bu kullanıcı aynı linki daha önce eklemiş mi kontrolü
        try:
            c.execute("SELECT guncel_fiyat, ilk_fiyat, eklenme_tarihi FROM urunler WHERE link=? AND chat_id=?", (link, str(chat_id)))
            mevcut = c.fetchone()
        except sqlite3.OperationalError:
            # Sütunlar henüz yoksa hata verebilir, eski sistemden kalmaysa diye:
            c.execute("SELECT guncel_fiyat FROM urunler WHERE link=? AND chat_id=?", (link, str(chat_id)))
            mevcut = c.fetchone()
            if mevcut:
                mevcut = (mevcut[0], mevcut[0], "Bilinmiyor")
        
        if mevcut:
            db_guncel_fiyat = mevcut[0]
            ilk_fiyat = mevcut[1] if mevcut[1] else db_guncel_fiyat
            tarih = mevcut[2] if mevcut[2] else "Bilinmiyor"
            
            # Güncel fiyat değişmişse arka planda veritabanını da güncelleyelim
            if fiyat != db_guncel_fiyat:
                c.execute("UPDATE urunler SET guncel_fiyat=? WHERE link=? AND chat_id=?", (fiyat, link, str(chat_id)))
                conn.commit()
                
            cevap = f"📦 Bu ürünü zaten takip ediyorsunuz.\n\n"
            cevap += f"🗓 Eklenme Tarihi: {tarih}\n\n"
            
            if fiyat_bilgisi["indirimli_fiyat"]:
                cevap += f"❌ Üstü Çizili Fiyat: {fiyat_bilgisi['normal_fiyat']} TL\n"
                cevap += f"⚡ İndirimli Sepet Fiyatı: {fiyat_bilgisi['indirimli_fiyat']} TL"
            else:
                cevap += f"⚡ Güncel Fiyat: {fiyat_bilgisi['normal_fiyat']} TL"
                
            bot.reply_to(message, cevap)
        else:
            su_an = datetime.now().strftime("%d.%m.%Y %H:%M")
            c.execute("INSERT INTO urunler (link, guncel_fiyat, chat_id, ilk_fiyat, eklenme_tarihi) VALUES (?, ?, ?, ?, ?)", (link, fiyat, str(chat_id), fiyat, su_an))
            conn.commit()
            
            cevap = f"🚀 ÜRÜN TAKİPTE!\n\n🗓 Tarih: {su_an}\n\n"
            if fiyat_bilgisi["indirimli_fiyat"]:
                cevap += f"❌ Üstü Çizili Fiyat: {fiyat_bilgisi['normal_fiyat']} TL\n"
                cevap += f"⚡ İndirimli Sepet Fiyatı: {fiyat_bilgisi['indirimli_fiyat']} TL\n\n"
            else:
                cevap += f"⚡ Güncel Fiyat: {fiyat_bilgisi['normal_fiyat']} TL\n\n"
            cevap += "Artık bu ürün indirime girdiğinde size bildirim göndereceğim."
            
            bot.reply_to(message, cevap)
        conn.close()
    else:
        bot.reply_to(message, "❌ Üzgünüm, linkteki fiyatı bulamadım. Sayfa yapısı veya ürün fiyat formatı beklenenden farklı olabilir.")

@bot.message_handler(func=lambda message: True)
def mesaj_al(message):
    chat_id = message.chat.id
    metin = message.text
    
    # Gelen mesajın içinde link olup olmadığını kontrol ediyoruz
    if "http://" in metin or "https://" in metin:
        bot.reply_to(message, "🔍 Linkinizi aldım, fiyat taraması başlatıldı. Lütfen biraz bekleyin...")
        
        # Eğer mesajın yanında yazı da varsa içinden sadece linki ayıkla
        link = [kelime for kelime in metin.split() if kelime.startswith("http")][0]
        
        # Fiyat çekme işlemi uzun sürdüğü için botun kilitlenmesini engellemek adına işlemi yeni bir thread'de (arka planda) başlatıyoruz.
        t = threading.Thread(target=isleyip_cevapla, args=(message, link, chat_id))
        t.start()
    else:
        bot.reply_to(message, "👋 Merhaba! Bana takip etmek istediğiniz ürünün linkini gönderin. İndirime girdiğinde size haber vereyim.")

def arka_plan_fiyat_kontrol(ilk_calisma=False):
    print("Arka planda fiyatlar kontrol ediliyor...")
    conn = sqlite3.connect('bot_db.sqlite')
    c = conn.cursor()
    c.execute("SELECT id, link, guncel_fiyat, chat_id FROM urunler")
    urunler = c.fetchall()
    
    kullanici_indirimleri = {}
    
    for urun in urunler:
        uid, link, eski_fiyat_str, chat_id = urun
        
        if chat_id not in kullanici_indirimleri:
            kullanici_indirimleri[chat_id] = False
            
        yeni_fiyat_bilgisi = fiyat_cek(link)
        
        if yeni_fiyat_bilgisi:
            yeni_fiyat_satis_str = yeni_fiyat_bilgisi["indirimli_fiyat"] if yeni_fiyat_bilgisi["indirimli_fiyat"] else yeni_fiyat_bilgisi["normal_fiyat"]
            
            eski_fiyat = parse_fiyat(eski_fiyat_str)
            yeni_fiyat = parse_fiyat(yeni_fiyat_satis_str)
            
            # Eğer yeni çekilen fiyat, veritabanındakinden düşükse indirim var demektir
            if yeni_fiyat < eski_fiyat:
                kullanici_indirimleri[chat_id] = True
                mesaj = f"🔥 İNDİRİM YAKALANDI! 🔥\n\nTakip ettiğiniz ürünün fiyatı düştü!\n"
                mesaj += f"Eski Fiyat: {eski_fiyat_str} TL\n\n"
                
                if yeni_fiyat_bilgisi["indirimli_fiyat"]:
                    mesaj += f"❌ Üstü Çizili Fiyat: {yeni_fiyat_bilgisi['normal_fiyat']} TL\n"
                    mesaj += f"⚡ Yeni İndirimli Fiyat: {yeni_fiyat_bilgisi['indirimli_fiyat']} TL\n\n"
                else:
                    mesaj += f"⚡ Yeni Fiyat: {yeni_fiyat_bilgisi['normal_fiyat']} TL\n\n"
                    
                mesaj += f"Link: {link}"
                bot.send_message(chat_id, mesaj)
                
                # Tekrar bildirim atmaması için yeni fiyatı veritabanına kaydet
                c.execute("UPDATE urunler SET guncel_fiyat=? WHERE id=?", (yeni_fiyat_satis_str, uid))
                conn.commit()
                
            # İsteğe bağlı: Fiyat yükselirse de arka planda gizlice güncelleyelim
            elif yeni_fiyat > eski_fiyat:
                c.execute("UPDATE urunler SET guncel_fiyat=? WHERE id=?", (yeni_fiyat_satis_str, uid))
                conn.commit()

    conn.close()
    
    # Sadece bot ilk çalıştığında ve kullanıcının hiçbir ürününde indirim yoksa haber ver
    if ilk_calisma:
        for chat_id, indirim_var in kullanici_indirimleri.items():
            if not indirim_var:
                bot.send_message(chat_id, "ℹ️ Bot başlatıldı. Şu an takip ettiğiniz ürünler arasında indirime giren bir ürün yok.")
                
    print("Fiyat kontrolü tamamlandı.")

def zamanlayici():
    # Bot ilk açıldığında beklemeden hemen bir kez fiyat kontrolü yap (Kapanıp açılma durumları için)
    arka_plan_fiyat_kontrol(ilk_calisma=True)

    # Arka plandaki kontrol işleminin ne sıklıkla yapılacağını ayarla
    # Güvenlik ve engellenmemek için 2 dakikaya ayarlandı.
    schedule.every(2).minutes.do(arka_plan_fiyat_kontrol)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    # Önce veritabanını oluştur veya bağlan
    init_db()
    
    # Arka plan fiyat takibi döngüsünü ayrı bir iş parçacığı (thread) olarak başlat
    t = threading.Thread(target=zamanlayici)
    t.daemon = True  # Ana program kapanırsa bu thread de kapansın
    t.start()
    
    print("Bot başarıyla başlatıldı ve dinleniyor. Telegram üzerinden link gönderebilirsiniz...")
    
    # Botun gelen mesajları dinleme (polling) işlemi
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot çalışırken hata oluştu: {e}")