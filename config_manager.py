import os
import json
from datetime import datetime

SETTINGS_FILE = "settings.json"
REPORT_DIR = "raporlar"

def ensure_report_dir():
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)
        print(f"[*] '{REPORT_DIR}' klasoru olusturuldu.")

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        raise FileNotFoundError(f"'{SETTINGS_FILE}' dosyasi bulunamadi!")

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
            return settings.get("SIRKETLER", {})
    except json.JSONDecodeError as e:
        raise Exception(f"'{SETTINGS_FILE}' dosyasinin JSON yapisi hatali: {e}")

def get_raw_settings():
    """Web arayüzündeki editör için JSON dosyasını ham metin olarak okur."""
    if not os.path.exists(SETTINGS_FILE):
        return '{\n  "SIRKETLER": {}\n}'
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return f.read()

def save_raw_settings(json_str):
    """Web arayüzünden gelen ham JSON metnini doğrular ve kaydeder."""
    try:
        json.loads(json_str)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write(json_str)
        return True, "Ayarlar başarıyla kaydedildi."
    except json.JSONDecodeError as e:
        return False, f"JSON Format Hatası: {e}"
    except Exception as e:
        return False, f"Bilinmeyen Hata: {e}"

def get_report_filepath(company_name):
    ensure_report_dir()
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    clean_company_name = company_name.lower().replace(" ", "_")
    filename = f"{clean_company_name}_{date_str}_citrix_lb_rapor.xlsx"
    
    return os.path.join(REPORT_DIR, filename)