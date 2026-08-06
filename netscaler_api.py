import requests
import urllib3
import ssl
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class InsecureTLSAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=1")
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super(InsecureTLSAdapter, self).init_poolmanager(*args, **kwargs)

def connect_and_login(ns_ip, username, password):
    base_url = f"https://{ns_ip}/nitro/v1/config"
    session = requests.Session()
    session.mount('https://', InsecureTLSAdapter())
    session.verify = False

    login_payload = {
        "login": {
            "username": username,
            "password": password
        }
    }
    
    print(f"[*] NetScaler'a ({ns_ip}) baglaniliyor...")
    login_res = session.post(f"{base_url}/login", json=login_payload, timeout=10)
    
    try:
        json_data = login_res.json()
    except:
        raise Exception(f"Sunucudan JSON disinda cevap geldi. HTTP: {login_res.status_code}")

    if "sessionid" in json_data:
        session_id = json_data["sessionid"]
    elif "login" in json_data and len(json_data["login"]) > 0:
        session_id = json_data["login"][0]["sessionid"]
    else:
        raise Exception(f"Session ID alinamadi! Cevap: {json_data}")
        
    headers = {"Cookie": f"NITRO_AUTH_TOKEN={session_id}"}
    print("[+] Login basarili, Session Token alindi.\n")
    return session, base_url, headers

def logout(session, base_url, headers):
    try:
        session.post(f"{base_url}/logout", json={"logout": {}}, headers=headers)
        print("\n[*] NetScaler oturumu guvenli sekilde kapatildi.")
    except Exception as e:
        print(f"\n[-] Logout uyarisi: {e}")