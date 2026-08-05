import os
from dotenv import load_dotenv
import netscaler_api
import config_manager
import excel_exporter

load_dotenv()

NS_IP = os.getenv("NS_IP")
USERNAME = os.getenv("NS_USER")
PASSWORD = os.getenv("NS_PASS")

EMPTY_ROW = {
    "Content Switch": "",
    "CS Aciklama": "",
    "CS Durum": "",
    "CS Port": "",
    "CS Protokol": "",
    "Load Balancer": "",
    "VS Port": "",
    "VS Protokol": "",
    "Backend Server": "",
    "IP Adresi": "",
    "Port": ""
}

def get_lb_services(session, base_url, lb_name, cs_name, cs_desc, cs_state, cs_port, cs_protocol, headers, report_data):
    """LB arkasındaki Service ve Service Group'ları rapora ekler. Ayrıca LB'nin kendi port ve protokol bilgisini çeker."""
    
    lb_port = "N/A"
    lb_protocol = "N/A"
    lb_info_res = session.get(f"{base_url}/lbvserver/{lb_name}", headers=headers)
    if lb_info_res.status_code == 200:
        lb_info = lb_info_res.json().get("lbvserver", [{}])[0]
        lb_port = str(lb_info.get("port", "N/A"))
        lb_protocol = str(lb_info.get("servicetype", "N/A"))

    svc_url = f"{base_url}/lbvserver_service_binding/{lb_name}"
    svc_res = session.get(svc_url, headers=headers)
    
    if svc_res.status_code == 200:
        services = svc_res.json().get("lbvserver_service_binding", [])
        for svc in services:
            report_data.append({
                "Content Switch": cs_name,
                "CS Aciklama": cs_desc,
                "CS Durum": cs_state,
                "CS Port": cs_port,
                "CS Protokol": cs_protocol,
                "Load Balancer": lb_name,
                "VS Port": lb_port,
                "VS Protokol": lb_protocol,
                "Backend Server": svc.get("servicename"),
                "IP Adresi": svc.get("ipv46", "N/A"),
                "Port": str(svc.get("port", ""))
            })
            
    svcgrp_url = f"{base_url}/lbvserver_servicegroup_binding/{lb_name}"
    svcgrp_res = session.get(svcgrp_url, headers=headers)
    
    if svcgrp_res.status_code == 200:
        svc_groups = svcgrp_res.json().get("lbvserver_servicegroup_binding", [])
        for sgrp in svc_groups:
            report_data.append({
                "Content Switch": cs_name,
                "CS Aciklama": cs_desc,
                "CS Durum": cs_state,
                "CS Port": cs_port,
                "CS Protokol": cs_protocol,
                "Load Balancer": lb_name,
                "VS Port": lb_port,
                "VS Protokol": lb_protocol,
                "Backend Server": sgrp.get("servicegroupname"),
                "IP Adresi": sgrp.get("ipv46", "N/A"),
                "Port": str(sgrp.get("port", ""))
            })

def main():
    if not all([NS_IP, USERNAME, PASSWORD]):
        print("[-] HATA: .env dosyasinda NS_IP, NS_USER veya NS_PASS eksik!")
        return

    try:
        sirketler = config_manager.load_settings()
    except Exception as e:
        print(f"[-] Config Hatasi: {e}")
        return

    try:
        session, base_url, headers = netscaler_api.connect_and_login(NS_IP, USERNAME, PASSWORD)
    except Exception as e:
        print(f"[-] Baglanti Hatasi: {e}")
        return

    for sirket_adi, sirket_config in sirketler.items():
        print(f"\n==========================================")
        print(f"[*] {sirket_adi} ŞİRKETİ İŞLENİYOR...")
        print(f"==========================================")
        
        report_data = []
        processed_lbs = set()  
        
        cs_listesi = sirket_config.get("HEDEF_CS_LISTESI", [])
        lb_listesi = sirket_config.get("HEDEF_LB_LISTESI", [])

        for cs_item in cs_listesi:
            cs_name = cs_item.get("NAME")
            cs_desc = cs_item.get("DESCRIPTION", "Açıklama Yok")
            
            print(f"[*] CS isleniyor: {cs_name}")
            cs_res = session.get(f"{base_url}/csvserver/{cs_name}", headers=headers)
            
            if cs_res.status_code == 200:
                cs_info = cs_res.json().get("csvserver", [{}])[0]
                cs_state = cs_info.get("curstate", "N/A")
                cs_port = str(cs_info.get("port", "N/A"))
                cs_protocol = str(cs_info.get("servicetype", "N/A"))
                
                target_lbs = set()
                lb_binding_url = f"{base_url}/csvserver_lbvserver_binding/{cs_name}"
                lb_res = session.get(lb_binding_url, headers=headers)
                
                if lb_res.status_code == 200:
                    lb_bindings = lb_res.json().get("csvserver_lbvserver_binding", [])
                    for binding in lb_bindings:
                        if binding.get("lbvserver"):
                            target_lbs.add(binding.get("lbvserver"))

                cspol_binding_url = f"{base_url}/csvserver_cspolicy_binding/{cs_name}"
                cspol_res = session.get(cspol_binding_url, headers=headers)
                
                if cspol_res.status_code == 200:
                    cspol_bindings = cspol_res.json().get("csvserver_cspolicy_binding", [])
                    for binding in cspol_bindings:
                        policy_target_lb = binding.get("targetlbvserver")
                        if policy_target_lb:
                            target_lbs.add(policy_target_lb)
                
                if target_lbs:
                    for lb_name in target_lbs:
                        get_lb_services(session, base_url, lb_name, cs_name, cs_desc, cs_state, cs_port, cs_protocol, headers, report_data)
                        processed_lbs.add(lb_name)
                    report_data.append(EMPTY_ROW)
                else:
                    print(f"    [!] '{cs_name}' icin Default LB veya Policy Target LB bulunamadi.")
            else:
                print(f"[-] HATA: '{cs_name}' Content Switch bulunamadi.")

        for lb_name in lb_listesi:
            if lb_name in processed_lbs:
                continue
                
            print(f"[*] Bagimsiz LB isleniyor: {lb_name}")
            lb_res = session.get(f"{base_url}/lbvserver/{lb_name}", headers=headers)
            
            if lb_res.status_code == 200:
                get_lb_services(session, base_url, lb_name, "N/A", "Bağımsız VS", "N/A", "N/A", "N/A", headers, report_data)
                report_data.append(EMPTY_ROW)
            else:
                print(f"[-] HATA: '{lb_name}' Load Balancer bulunamadi.")

        if report_data:
            if report_data[-1] == EMPTY_ROW:
                report_data.pop()

            excel_path = config_manager.get_report_filepath(sirket_adi)
            
            fields = [
                "Content Switch", "CS Aciklama", "CS Durum", "CS Port", "CS Protokol", 
                "Load Balancer", "VS Port", "VS Protokol", 
                "Backend Server", "IP Adresi", "Port"
            ]
            
            excel_exporter.create_excel_report(report_data, fields, excel_path, EMPTY_ROW, sirket_adi)
            print(f"[+] {sirket_adi} Raporu (Excel) tamamlandi: {excel_path}")
        else:
            print(f"[-] {sirket_adi} için kayit bulunamadi.")

    netscaler_api.logout(session, base_url, headers)

if __name__ == "__main__":
    main()