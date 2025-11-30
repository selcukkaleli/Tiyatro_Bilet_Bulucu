Biletinial Profesyonel – Oyun Tarihi İzleyicisi
Bu repo, Biletinial üzerinden “PROFESYONEL” oyunu için yeni oyun tarihlerini takip eden küçük bir Python otomasyon scriptini içeriyor.
Amaç, belirli bir tarihten sonra (örn. 2025-11-14) yeni bir gösterim açıldığında otomatik e-posta uyarısı almak.
 
Neler Yapıyor?
•	Belirlenen oyun sayfasını ve mekan sayfasını HTTP isteği ile çekiyor (requests).
•	HTML içeriğini BeautifulSoup ile parse ediyor.
•	Türkçe ay isimlerini ve kısaltmalarını tanıyacak şekilde tarihleri metin içinden regex ile ayıklıyor.
•	Eşik tarihten (CUTOFF_DATE) sonra olan tarihleri buluyor.
•	Daha önce bildirilen en büyük tarihi state.json dosyasında saklıyor, böylece:
o	Aynı tarih için tekrar tekrar e-posta göndermiyor.
•	Yeni bir tarih bulunduğunda, SMTP üzerinden e-posta bildirimi gönderiyor.
•	Windows Görev Zamanlayıcısı ile günde birkaç kez çalışacak şekilde ayarlanabiliyor.
Bu projede özellikle şunlara dikkat ettim:
•	Gerçek bir senaryoya yönelik küçük ama uçtan uca çalışan bir otomasyon kurmak
•	Türkçe tarih formatları, ay isimleri ve kısaltmalarıyla çalışma
•	Çevresel değişkenler üzerinden konfigürasyon yönetimi (.env)
•	Idempotent (tekrar çalıştırıldığında gereksiz e-posta atmayan) bir tasarım
________________________________________
Kullanılan Teknolojiler
•	Python 3
•	requests – HTTP istekleri
•	BeautifulSoup – HTML parse
•	re – regex ile tarih yakalama
•	smtplib, email – SMTP e-posta gönderimi
•	python-dotenv – .env yönetimi
•	json, pathlib – basit kalıcı durum (state) takibi
 
Kurulum
git clone https://github.com/<kullanici-adi>/<repo-adi>.git
cd <repo-adi>
pip install -r requirements.txt
.env dosyasını aşağıdaki değişkenlerle doldur:
TARGET_URL="https://biletinial.com/tr-tr/tiyatro/profesyonel-dt"
VENUE_URL="https://biletinial.com/tr-tr/mekan/istanbul-devlet-tiyatrosu"

CUTOFF_DATE="2025-11-14"
ALLOWED_MONTHS="Kasım,Aralık"

SMTP_HOST="smtp.ornek.com"
SMTP_PORT=587
SMTP_USER="kullanici@ornek.com"
SMTP_PASS="sifre"
FROM_EMAIL="kullanici@ornek.com"
TO_EMAIL="hedef@ornek.com"

DEBUG=0
 
Çalıştırma
Komutu elle çalıştırmak için:
python bilet_izleyici.py
Daimi kullanımla ilgili tipik senaryo:
•	Script’i günde 1–2 kez çalışacak şekilde Windows Görev Zamanlayıcı’na eklemek
•	Yeni bir tarih (örn. Biletinial’da ekstra temsil) açıldığında otomatik mail almak
 
Notlar
Bu proje, günlük hayatta yaşadığım gerçek bir ihtiyacı çözerken:
•	Web scraping,
•	Türkçe tarih işleme,
•	Küçük bir script için durum yönetimi (state),
•	Çevresel değişkenlerle gizli bilgiler ve ayarları koddan ayırma,
•	Zamanlanmış görev mantığı
gibi konularda pratik yapmam için kullanıldı.
Küçük ama gerçek bir problemi çözen, uçtan uca çalışan otomasyon örneği olarak GitHub profilimde tutuyorum.

