🛒 BTF İndirim Takip Botu (@btf_indirim_botu)
BTF İndirim Takip Botu, verdiğiniz ürün linklerini sürekli izleyerek fiyat düşüşlerini anlık olarak Telegram üzerinden bildiren bir Python asistanıdır. Özellikle manuel fiyat takibi yapmak istemeyen kullanıcılar için geliştirilmiştir.

✨ Özellikler
Anlık Fiyat Sorgulama: Gönderdiğiniz ürün linkini anında tarayarak güncel fiyat bilgisini çeker.

Otomatik Veritabanı Kaydı: Takibe alınan ürünler veritabanına kaydedilir, böylece bot kapansa bile verileriniz kaybolmaz.

Akıllı Başlangıç Kontrolü (Startup Scan): Botu çalıştırdığınız anda, veritabanındaki tüm linkler taranır. Siz botu kapalı tuttuğunuz sürece gerçekleşen indirimler, bot açıldığı ilk 2-3 dakika içinde size raporlanır.

Dinamik Takip Döngüsü: Bot aktif olduğu sürece her 2 dakikada bir tüm ürünleri kontrol eder ve fiyat değişikliği durumunda "Eski Fiyat ➡️ Yeni Fiyat" şeklinde bildirim gönderir.

Esnek Mimari: Yerel bilgisayarınızda (Localhost) çalışacak şekilde optimize edilmiştir.

🛠 Çalışma Mantığı
Proje, sürekli aktif bir sunucu (VPS) gerektirmeden, çalıştırıldığı süre boyunca maksimum verimle görev yapacak şekilde tasarlanmıştır:

Açılış Fazı: python app.py komutu verildiğinde bot önce veritabanını okur ve geçmişteki fiyatlar ile güncel web fiyatlarını karşılaştırır.

Döngü Fazı: İlk tarama bittikten sonra bot sürekli bir döngüye girer ve her 120 saniyede bir fiyat güncellemesi yapar.

Bildirim: Sadece fiyat düştüğünde kullanıcıya Telegram üzerinden mesaj gönderilir.

🚀 Kurulum ve Kullanım
Projeyi yerel makinenizde çalıştırmak için aşağıdaki adımları izleyebilirsiniz:

1. Dosyaları Klonlayın
git clone https://github.com/tolgagurler1503/telegram_indirim_botu

2. Gereksinimleri Yükleyin
pip install requirements.txt

3. Botu Çalıştırın
Botu terminal üzerinden başlatmanız yeterlidir:

python app.py
Not: Bot, terminaliniz ve bilgisayarınız açık kaldığı sürece takibe devam edecektir.

📈 Gelecek Planları (Roadmap)
[1] 7/24 kesintisiz çalışma için Cloud/VPS entegrasyonu.

[2] Daha fazla e-ticaret platformu için scraping desteği.

[3] Grafiksel fiyat değişim raporları.

[4] Çoklu kullanıcı desteğinin optimize edilmesi.

🤝 Katkıda Bulunma
Bu proje geliştirilmeye devam etmektedir. Her türlü fikir, hata bildirimi veya iyileştirme talebi için bir "Issue" açabilir ya da "Pull Request" gönderebilirsiniz.
