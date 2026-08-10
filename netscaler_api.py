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

def get_cs_info(session, base_url, headers, cs_name):
    res = session.get(f"{base_url}/csvserver/{cs_name}", headers=headers)
    if res.status_code == 200:
        info = res.json().get("csvserver", [{}])[0]
        return {
            "ip": str(info.get("ipv46", "N/A")),
            "port": str(info.get("port", "N/A")),
            "protocol": str(info.get("servicetype", "N/A"))
        }
    return None

def get_lb_info(session, base_url, headers, lb_name):
    res = session.get(f"{base_url}/lbvserver/{lb_name}", headers=headers)
    if res.status_code == 200:
        info = res.json().get("lbvserver", [{}])[0]
        return {
            "ip": str(info.get("ipv46", "N/A")),
            "port": str(info.get("port", "N/A")),
            "protocol": str(info.get("servicetype", "N/A"))
        }
    return {"ip": "N/A", "port": "N/A", "protocol": "N/A"}

def get_cip_info(session, base_url, headers, entity_name, entity_type="service"):
    try:
        res = session.get(f"{base_url}/{entity_type}/{entity_name}", headers=headers)
        if res.status_code == 200:
            info = res.json().get(entity_type, [{}])[0]
            if info.get("cip", "DISABLED") == "ENABLED":
                return info.get("cipheader") or "ENABLED (Header Yok)"
            return "DISABLE"
    except:
        pass
    return "N/A"

def get_backend_services(session, base_url, headers, lb_name):
    """Bir Load Balancer arkasındaki tüm Servis ve Servis Gruplarını liste olarak döner."""
    backends = []
    
    # 1. Standart Servisler
    svc_res = session.get(f"{base_url}/lbvserver_service_binding/{lb_name}", headers=headers)
    if svc_res.status_code == 200:
        for svc in svc_res.json().get("lbvserver_service_binding", []):
            svc_name = svc.get("servicename")
            backends.append({
                "name": svc_name,
                "ip": svc.get("ipv46", "N/A"),
                "port": str(svc.get("port", "")),
                "cip": get_cip_info(session, base_url, headers, svc_name, "service")
            })

    # 2. Servis Grupları
    grp_res = session.get(f"{base_url}/lbvserver_servicegroup_binding/{lb_name}", headers=headers)
    if grp_res.status_code == 200:
        for grp in grp_res.json().get("lbvserver_servicegroup_binding", []):
            grp_name = grp.get("servicegroupname")
            backends.append({
                "name": grp_name,
                "ip": grp.get("ipv46", "N/A"),
                "port": str(grp.get("port", "")),
                "cip": get_cip_info(session, base_url, headers, grp_name, "servicegroup")
            })
            
    return backends

def get_cs_target_lbs(session, base_url, headers, cs_name):
    target_lbs_data = {}
    
    def add_lb(lb_name, p_name, p_pri, p_rule):
        if lb_name not in target_lbs_data:
            target_lbs_data[lb_name] = {"names": [], "priorities": [], "rules": []}
        target_lbs_data[lb_name]["names"].append(str(p_name))
        target_lbs_data[lb_name]["priorities"].append(str(p_pri))
        target_lbs_data[lb_name]["rules"].append(str(p_rule))

    lb_res = session.get(f"{base_url}/csvserver_lbvserver_binding/{cs_name}", headers=headers)
    if lb_res.status_code == 200:
        for b in lb_res.json().get("csvserver_lbvserver_binding", []):
            if b.get("lbvserver"):
                add_lb(b.get("lbvserver"), "Default LB", "-", "-")

    pol_res = session.get(f"{base_url}/csvserver_cspolicy_binding/{cs_name}", headers=headers)
    if pol_res.status_code == 200:
        for b in pol_res.json().get("csvserver_cspolicy_binding", []):
            target_lb = b.get("targetlbvserver")
            if target_lb:
                p_name = b.get("policyname", "N/A")
                p_pri = b.get("priority", "N/A")
                p_rule = "N/A"
                
                if p_name != "N/A":
                    try:
                        rule_res = session.get(f"{base_url}/cspolicy/{p_name}", headers=headers)
                        if rule_res.status_code == 200:
                            p_rule = rule_res.json().get("cspolicy", [{}])[0].get("rule", "N/A")
                    except:
                        pass
                add_lb(target_lb, p_name, p_pri, p_rule)

    return target_lbs_data