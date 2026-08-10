# Citrix NetScaler (ADC) LB & CS Raporlama Aracı
Citrix NetScaler (ADC) üzerinden NITRO API kullanarak Content Switch (CS) ve Load Balancer (LB/VS) yapılandırmalarını çeken; kural, policy, dataset, port, protokol ve backend sunucu bilgilerini analiz ederek şirket/proje bazlı, formatlanmış profesyonel Excel raporları oluşturan modüler Python aracıdır.

## Öne Çıkan Özellikler
* **İnteraktif Yönetim Paneli:** Araç çalıştırıldığında açılan CLI paneli sayesinde sadece seçtiğiniz şirketlerin NetScaler cihazlarına bağlanarak gereksiz ağ ve API trafiğinin önüne geçer.
* **CS Policy & Kural Analizi:** Content Switch yönlendirme kurallarını (Policy Name, Priority, Expression) detaylıca çeker. Bir Load Balancer'a birden fazla kural geliyorsa bunları alt alta düzenli bir şekilde listeler.
* **Otomatik Dataset (Veri Seti) Keşfi:** Policy kuralları içine gömülmüş (örn: `CONTAINS_ANY("ATLAS_VIP_IP")`) Dataset isimlerini otomatik tespit eder. NetScaler'a minimum API isteği atarak IP aralıklarını çeker ve **ana raporun yanına her Dataset için ayrı bir Excel sekmesi (Tab)** oluşturur.
* **Çoklu Cihaz (Multi-NLB) Desteği:** Her şirket veya proje için farklı NetScaler IP, Kullanıcı Adı ve Parola tanımlanabilir. Özel tanım yapılmayanlar varsayılan cihaza yönlenir.
* **Client IP (CIP) Analizi:** Backend servislerde CIP'in aktif olup olmadığını ve aktifse hangi header (örn: `X-Forwarded-For`, `client-ip`) ile gönderildiğini otomatik tespit eder.
* **Akıllı Excel Çıktısı:** Aynı CS ve VS'ye ait verileri akıllı algoritmasıyla dikey olarak birleştirir (merge), okumayı kolaylaştıran kurumsal pastel renkler ve zebra desenleri uygular, sütunları otomatik boyutlandırır.

## NetScaler Kullanıcı Yetkileri
Bu aracın cihazdan veri çekebilmesi için kullanılacak kullanıcının (user) NetScaler üzerinde aşağıdaki yetkilere sahip olması gerekmektedir:
* **Allowed Management Interface:** `API` (NITRO API üzerinden haberleştiği için zorunludur).
* **Yetki Seviyesi:** Sadece okuma (`read-only`) yetkisi raporlama için yeterlidir (Sistemde değişiklik yapmaz).

## Kurulum
Gerekli Python kütüphanelerini kurmak için terminalde şu komutu çalıştırın:
```
pip3 install requests urllib3 openpyxl python-dotenv
```

## Yapılandırma
Proje dizininde gizli bir .env dosyası oluşturun (veya repodaki .env.example dosyasının adını değiştirin) ve NetScaler giriş bilgilerinizi ekleyin:
```
NS_IP=NLBIP
NS_USER=kullanici
NS_PASS=sifreniz

ORNEK_SIRKET_B_IP=NLBIP
ORNEK_SIRKET_B_USER=kullanici
ORNEK_SIRKET_B_PASS=sifreniz
```
Projedeki settings_example.json dosyasının adını settings.json olarak değiştirin ve kendi yapınızdaki Content Switch (CS) ile bağımsız Load Balancer (LB) isimlerini bu dosyaya tanımlayın.

## Manuel Çalıştırma
Komut çalıştırıldığında cihazlara bağlanılacak, veriler çekilecek ve raporlar/ klasörü altına güncel tarih etiketiyle kurumsal renklendirilmiş bir Excel dosyası (.xlsx) oluşturulacaktır.
```
python3 main.py
```