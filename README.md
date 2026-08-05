# Citrix NetScaler (ADC) LB & CS Raporlama Aracı
Citrix NetScaler (ADC) üzerinden NITRO API kullanarak Content Switch (CS) ve Load Balancer (LB/VS) yapılandırmalarını çeken; kural, port, protokol ve backend sunucu bilgilerini analiz ederek şirket/proje bazlı, formatlanmış (hücreleri dikey birleştirilmiş) profesyonel Excel raporları oluşturan modüler Python aracıdır.

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
```
Projedeki settings_example.json dosyasının adını settings.json olarak değiştirin ve kendi yapınızdaki Content Switch (CS) ile bağımsız Load Balancer (LB) isimlerini bu dosyaya tanımlayın.

## Manuel Çalıştırma
Komut çalıştırıldığında cihazlara bağlanılacak, veriler çekilecek ve raporlar/ klasörü altına güncel tarih etiketiyle kurumsal renklendirilmiş bir Excel dosyası (.xlsx) oluşturulacaktır.
```
python3 main.py
```