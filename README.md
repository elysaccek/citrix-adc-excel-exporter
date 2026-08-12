# Citrix NetScaler (ADC) LB & CS Raporlama Aracı
Citrix NetScaler (ADC) üzerinden NITRO API kullanarak Content Switch (CS) ve Load Balancer (LB/VS) yapılandırmalarını çeken; kural, policy, dataset, port, protokol ve backend sunucu bilgilerini analiz ederek şirket/proje bazlı, formatlanmış profesyonel Excel raporları oluşturan modüler Python aracıdır.

## Öne Çıkan Özellikler
* **Azure DevOps Denetimi (Audit):** NetScaler'daki (NLB) backend sunucular ile Azure DevOps Deployment Group'taki sunucuları belirttiğiniz Tag'lere göre çapraz kontrole sokar. NLB'de ismin sonuna eklenen `_PORT` eklerini akıllıca ayıklar. Azure'da olup NLB'de olmayan veya tam tersi durumdaki eksik/fazla sunucuları Excel'de **kırmızıyla uyararak** mimari açıklarını anında tespit etmenizi sağlar.
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

ORNEK_SIRKET_B_NS_IP=NLBIP
ORNEK_SIRKET_B_NS_USER=kullanici
ORNEK_SIRKET_B_NS_PASS=sifreniz

ORNEK_SIRKET_B_AZURE_SERVER_URL=Azure Urli
ORNEK_SIRKET_B_AZURE_COLLECTION=Collection Adı
ORNEK_SIRKET_B_AZURE_PROJECT=Proje Adı
ORNEK_SIRKET_B_AZURE_DEPLOYMENT_GROUP_ID=1
ORNEK_SIRKET_B_AZURE_PAT=Personal Access Token Değeri
```

Projedeki settings_example.json dosyasının adını settings.json olarak değiştirin ve kendi yapınızdaki Content Switch (CS), Load Balancer (LB) ve Azure Tag eşleştirmelerini bu dosyaya tanımlayın.
```
{
  "SIRKETLER": {
    "ORNEK_SIRKET_A": {
      "AZURE": false,
      "HEDEF_CS_LISTESI": [
        {
          "NAME": "sistem.orneksirket.com.tr_CS_SSL",
          "DESCRIPTION": "Ornek Sistem Portali"
        },
        {
          "NAME": "servis.orneksirket.com.tr_SSL",
          "DESCRIPTION": "Ornek B2B Servisi"
        }
      ],
      "HEDEF_LB_LISTESI": [
        "yonetim.orneksirket.com.tr_https",
        "rapor.orneksirket.com.tr_SSL"
      ]
    },
    "ORNEK_SIRKET_B": {
      "AZURE": true,
      "AZURE_TAG_LB_ESLESMESI": [
        {
          "TAG":"ROBOT",
          "LB":"robot_havuz"
        }
      ],
      "HEDEF_CS_LISTESI": [
        {
          "NAME": "api.ikincisirket.com_CS",
          "DESCRIPTION": "API Gateway"
        }
      ],
      "HEDEF_LB_LISTESI": []
    }
  }
}
```

## Manuel Çalıştırma
Komut çalıştırıldığında cihazlara bağlanılır, veriler, Dataset'ler ve Azure DevOps entegrasyonu çekilir; ardından raporlar/ klasörü altına güncel tarih etiketiyle kurumsal renklendirilmiş bir Excel dosyası (.xlsx) oluşturulacaktır.
```
python3 main.py
```