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
            "protocol": str(info.get("servicetype", "N/A")),
            "persistence": info.get("persistencetype", "N/A"),
            "persistence_timeout": info.get("timeout", "N/A"),
            "cookie_name": info.get("cookiename") or "",
            "backup_persistence": info.get("persistencebackup", "N/A"),
            "backup_persistence_timeout": info.get(
                "backuppersistencetimeout", "N/A"
            ),
            "ipv4_netmask": (
                info.get("netmask")
                or info.get("persistmask")
                or "N/A"
            ),
            "ipv6_mask_length": (
                info.get("v6netmasklen")
                or info.get("v6persistmasklen")
                or "N/A"
            )
        }

    return None

def get_monitor_info(session, base_url, headers, entity_name, entity_type="service"):
    try:
        res = session.get(f"{base_url}/{entity_type}_lbmonitor_binding/{entity_name}", headers=headers)
        if res.status_code == 200:
            bindings = res.json().get(f"{entity_type}_lbmonitor_binding", [])
            monitors = [b.get("monitor_name") for b in bindings if b.get("monitor_name")]
            if monitors:
                return "\n".join(monitors)
    except:
        pass
    return "N/A"

def get_service_details(session, base_url, headers, entity_name, entity_type="service"):
    defaults = {
        "sp": "N/A", "useproxyport": "N/A", "downstateflush": "N/A", "accessdown": "N/A",
        "usip": "N/A", "cka": "N/A", "tcpb": "N/A", "cmp": "N/A",
        "cip": "N/A", "cipheader": "N/A", "maxbandwidth": "N/A", "monthreshold": "N/A",
        "maxreq": "N/A", "maxclient": "N/A", "clttimeout": "N/A", "svrtimeout": "N/A"
    }
    
    try:
        res = session.get(f"{base_url}/{entity_type}/{entity_name}", headers=headers)
        if res.status_code == 200:
            info = res.json().get(entity_type, [{}])[0]
            
            cip_status = info.get("cip", "DISABLED")
            cip_display = info.get("cipheader") or "Header Yok" if cip_status == "ENABLED" else "-"
            
            return {
                "sp": info.get("sp", "N/A"),
                "useproxyport": info.get("useproxyport", "N/A"),
                "downstateflush": info.get("downstateflush", "N/A"),
                "accessdown": info.get("accessdown", "N/A"),
                "usip": info.get("usip", "N/A"),
                "cka": info.get("cka", "N/A"),
                "tcpb": info.get("tcpb", "N/A"),
                "cmp": info.get("cmp", "N/A"),
                "cip": cip_status,
                "cipheader": cip_display,
                "maxbandwidth": str(info.get("maxbandwidth", "N/A")),
                "monthreshold": str(info.get("monthreshold", "N/A")),
                "maxreq": str(info.get("maxreq", "N/A")),
                "maxclient": str(info.get("maxclient", "N/A")),
                "clttimeout": str(info.get("clttimeout", "N/A")),
                "svrtimeout": str(info.get("svrtimeout", "N/A"))
            }
    except:
        pass
    return defaults

def get_backend_services(session, base_url, headers, lb_name):
    backends = []
    
    svc_res = session.get(f"{base_url}/lbvserver_service_binding/{lb_name}", headers=headers)
    if svc_res.status_code == 200:
        for svc in svc_res.json().get("lbvserver_service_binding", []):
            svc_name = svc.get("servicename")
            details = get_service_details(session, base_url, headers, svc_name, "service")
            backend_data = {
                "name": svc_name,
                "ip": svc.get("ipv46", "N/A"),
                "port": str(svc.get("port", "")),
                "cip": details["cip"] if details["cip"] == "DISABLED" else details["cipheader"],
                "monitor": get_monitor_info(session, base_url, headers, svc_name, "service")
            }
            backend_data.update(details) # Servis detaylarını sözlüğe ekle
            backends.append(backend_data)

    grp_res = session.get(f"{base_url}/lbvserver_servicegroup_binding/{lb_name}", headers=headers)
    if grp_res.status_code == 200:
        for grp in grp_res.json().get("lbvserver_servicegroup_binding", []):
            grp_name = grp.get("servicegroupname")
            details = get_service_details(session, base_url, headers, grp_name, "servicegroup")
            backend_data = {
                "name": grp_name,
                "ip": grp.get("ipv46", "N/A"),
                "port": str(grp.get("port", "")),
                "cip": details["cip"] if details["cip"] == "DISABLED" else details["cipheader"],
                "monitor": get_monitor_info(session, base_url, headers, grp_name, "servicegroup")
            }
            backend_data.update(details) # Servis detaylarını sözlüğe ekle
            backends.append(backend_data)

    sorted_backends = sorted(backends, key=lambda k: k["name"].lower())
            
    return sorted_backends

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
            target_lb = b.get("targetlbvserver") or b.get("targetvserver")
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

def get_vserver_policies(session, base_url, headers, vs_name, vs_type, vs_info):
    policies_list = []
    policy_found = False  
    
    for pol_type in ['responder', 'rewrite']:
        endpoint = f"{base_url}/{vs_type}_{pol_type}policy_binding/{vs_name}"
        try:
            res = session.get(endpoint, headers=headers)
            if res.status_code == 200:
                bindings = res.json().get(f"{vs_type}_{pol_type}policy_binding", [])
                
                if bindings:
                    policy_found = True
                    
                for b in bindings:
                    pol_name = b.get('policyname')
                    priority = b.get('priority', '')
                    bindpoint = b.get('bindpoint', 'N/A')
                    goto_expr = b.get('gotopriorityexpression', 'N/A')
                    
                    invoke_flag = b.get('invoke', False)
                    invoke_label = "N/A"
                    if str(invoke_flag).lower() == 'true':
                        invoke_label = f"{b.get('labeltype', '')} ({b.get('labelname', '')})"
                    
                    rule = "N/A"
                    action_name = "N/A"
                    action_type = "N/A"
                    action_details = "N/A"
                    
                    try:
                        p_res = session.get(f"{base_url}/{pol_type}policy/{pol_name}", headers=headers)
                        if p_res.status_code == 200:
                            p_data = p_res.json().get(f"{pol_type}policy", [{}])[0]
                            rule = p_data.get('rule', 'N/A')
                            action_name = p_data.get('action', 'N/A')
                    except: pass
                    
                    if action_name not in ["N/A", "NOREWRITE", "DROP", "RESET"]:
                        try:
                            a_res = session.get(f"{base_url}/{pol_type}action/{action_name}", headers=headers)
                            if a_res.status_code == 200:
                                a_data = a_res.json().get(f"{pol_type}action", [{}])[0]
                                action_type = str(a_data.get('type', 'N/A'))
                                
                                details = []
                                if a_data.get('target'): details.append(f"Target: {a_data.get('target')}")
                                if a_data.get('stringbuilderexpr'): details.append(f"Expr: {a_data.get('stringbuilderexpr')}")
                                action_details = " | ".join(details) if details else "N/A"
                        except: pass
                    elif action_name in ["DROP", "RESET", "NOREWRITE"]:
                        action_type = "Built-in"
                        action_details = action_name
                        
                    policies_list.append({
                        "Content Switch / Load Balancer": vs_name,
                        "CS IP / VS IP": vs_info.get("ip", "N/A"),
                        "CS Port / VS Port": vs_info.get("port", "N/A"),
                        "CS Protokol / VS Protokol": vs_info.get("protocol", "N/A"),
                        "Policy": pol_type.capitalize(),
                        "Policy Type": str(bindpoint),
                        "Policy Priority": str(priority),
                        "Policy Name": str(pol_name),
                        "Expression": str(rule),
                        "Action Name": str(action_name),
                        "Action Type": str(action_type),
                        "Action diğer detayları": str(action_details),
                        "Goto Expression": str(goto_expr),
                        "Invoke Label Type": str(invoke_label)
                    })
        except:
            pass
            
    if not policy_found:
        policies_list.append({
            "Content Switch / Load Balancer": vs_name,
            "CS IP / VS IP": vs_info.get("ip", "N/A"),
            "CS Port / VS Port": vs_info.get("port", "N/A"),
            "CS Protokol / VS Protokol": vs_info.get("protocol", "N/A"),
            "Policy": "-",
            "Policy Type": "-",
            "Policy Priority": "-",
            "Policy Name": "-",
            "Expression": "-",
            "Action Name": "-",
            "Action Type": "-",
            "Action diğer detayları": "-",
            "Goto Expression": "-",
            "Invoke Label Type": "-"
        })
            
    return policies_list


def get_all_vservers(session, base_url, headers, entity_type, page_size=100):
    if entity_type not in ("csvserver", "lbvserver"):
        raise ValueError(
            "Desteklenmeyen Virtual Server tipi: " + str(entity_type)
        )

    endpoint = f"{base_url}/{entity_type}"
    all_vservers = []
    page_number = 1

    while True:
        response = session.get(
            endpoint,
            headers=headers,
            params={
                "pagesize": page_size,
                "pageno": page_number
            },
            timeout=30
        )

        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError(
                f"{entity_type} yanıtı JSON değil. "
                f"HTTP: {response.status_code}"
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"{entity_type} listesi alınamadı. "
                f"HTTP: {response.status_code}, "
                f"Detay: {payload.get('message', payload)}"
            )

        error_code = payload.get("errorcode", 0)
        if error_code not in (0, "0", None):
            raise RuntimeError(
                f"{entity_type} NITRO hatası: "
                f"{payload.get('message', payload)}"
            )

        page_items = payload.get(entity_type, [])

        if not isinstance(page_items, list):
            raise RuntimeError(
                f"{entity_type} yanıt formatı beklenenden farklı."
            )

        all_vservers.extend(page_items)

        if len(page_items) < page_size:
            break

        page_number += 1

        if page_number > 10000:
            raise RuntimeError(
                f"{entity_type} listelemesinde sayfa sınırı aşıldı."
            )

    return sorted(
        all_vservers,
        key=lambda item: str(item.get("name", "")).lower()
    )
