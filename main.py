import os
from dotenv import load_dotenv
import netscaler_api
import config_manager
import excel_exporter

load_dotenv()

EMPTY_ROW = {
    "Content Switch": "",
    "CS Aciklama": "",
    "CS IP": "",
    "CS Port": "",
    "CS Protokol": "",
    "Load Balancer": "",
    "VS IP": "",
    "VS Port": "",
    "VS Protokol": "",
    "Backend Server": "",
    "IP Adresi": "",
    "Port": "",
    "CIP": ""
}

def clear_screen():
    """Terminal ekranını temizler."""
    os.system('cls' if os.name == 'nt' else 'clear')

def select_companies_menu(sirketler):
    """Kullanıcıya interaktif şirket seçim paneli sunar."""
    company_names = list(sirketler.keys())
    selected = {name: True for name in company_names}
    
    while True:
        clear_screen()
        print("==========================================")
        print("      CITRIX NLB RAPORLAMA PANELİ         ")
        print("==========================================")
        print("Çalıştırmak istediğiniz şirketleri seçin:")
        print("(Numarayı yazıp Enter'a basarak seçimi değiştirebilirsiniz)\n")
        
        for i, name in enumerate(company_names, 1):
            mark = "X" if selected[name] else " "
            print(f" [{mark}] {i}. {name}")
            
        print("\n------------------------------------------")
        print(" İşlemler:")
        print(" [T] Tümünü Seç")
        print(" [B] Seçimi Bırak (Hiçbiri)")
        print(" [C] ÇALIŞTIR (Sadece 'X' olanlar)")
        print(" [Q] Çıkış")
        print("==========================================")
        
        choice = input("Seçiminiz (Rakam veya Harf): ").strip().upper()
        
        if choice == 'Q':
            print("\nÇıkış yapılıyor...")
            exit(0)
        elif choice == 'C':
            selected_companies = [name for name, is_sel in selected.items() if is_sel]
            if not selected_companies:
                input("\n[!] Lütfen en az bir şirket seçin! (Devam etmek için Enter'a basın)...")
                continue
            return selected_companies
        elif choice == 'T':
            for name in selected: 
                selected[name] = True
        elif choice == 'B':
            for name in selected: 
                selected[name] = False
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(company_names):
                name = company_names[idx]
                selected[name] = not selected[name]
            else:
                input("\n[!] Geçersiz numara! (Devam etmek için Enter'a basın)...")
        else:
            input("\n[!] Hatalı giriş yaptınız! (Devam etmek için Enter'a basın)...")


def get_lb_services(session, base_url, lb_name, cs_name, cs_desc, cs_ip, cs_port, cs_protocol, headers, report_data):
    """LB arkasındaki Service ve Service Group'ları rapora ekler. Ayrıca CIP ve IP bilgilerini çeker."""
    
    lb_ip = "N/A"
    lb_port = "N/A"
    lb_protocol = "N/A"
    
    lb_info_res = session.get(f"{base_url}/lbvserver/{lb_name}", headers=headers)
    if lb_info_res.status_code == 200:
        lb_info = lb_info_res.json().get("lbvserver", [{}])[0]
        lb_ip = str(lb_info.get("ipv46", "N/A"))
        lb_port = str(lb_info.get("port", "N/A"))
        lb_protocol = str(lb_info.get("servicetype", "N/A"))

    svc_url = f"{base_url}/lbvserver_service_binding/{lb_name}"
    svc_res = session.get(svc_url, headers=headers)
    
    if svc_res.status_code == 200:
        services = svc_res.json().get("lbvserver_service_binding", [])
        for svc in services:
            svc_name = svc.get("servicename")
            
            cip_val = "N/A"
            try:
                s_info_res = session.get(f"{base_url}/service/{svc_name}", headers=headers)
                if s_info_res.status_code == 200:
                    s_info = s_info_res.json().get("service", [{}])[0]
                    cip_status = s_info.get("cip", "DISABLED")
                    if cip_status == "ENABLED":
                        cip_val = s_info.get("cipheader") or "ENABLED (Header Yok)"
                    else:
                        cip_val = "DISABLE"
            except:
                pass
            
            report_data.append({
                "Content Switch": cs_name,
                "CS Aciklama": cs_desc,
                "CS IP": cs_ip,
                "CS Port": cs_port,
                "CS Protokol": cs_protocol,
                "Load Balancer": lb_name,
                "VS IP": lb_ip,
                "VS Port": lb_port,
                "VS Protokol": lb_protocol,
                "Backend Server": svc_name,
                "IP Adresi": svc.get("ipv46", "N/A"),
                "Port": str(svc.get("port", "")),
                "CIP": cip_val
            })
            
    svcgrp_url = f"{base_url}/lbvserver_servicegroup_binding/{lb_name}"
    svcgrp_res = session.get(svcgrp_url, headers=headers)
    
    if svcgrp_res.status_code == 200:
        svc_groups = svcgrp_res.json().get("lbvserver_servicegroup_binding", [])
        for sgrp in svc_groups:
            sgrp_name = sgrp.get("servicegroupname")
            
            cip_val = "N/A"
            try:
                sg_info_res = session.get(f"{base_url}/servicegroup/{sgrp_name}", headers=headers)
                if sg_info_res.status_code == 200:
                    sg_info = sg_info_res.json().get("servicegroup", [{}])[0]
                    cip_status = sg_info.get("cip", "DISABLED")
                    if cip_status == "ENABLED":
                        cip_val = sg_info.get("cipheader") or "ENABLED (Header Yok)"
                    else:
                        cip_val = "DISABLE"
            except:
                pass

            report_data.append({
                "Content Switch": cs_name,
                "CS Aciklama": cs_desc,
                "CS IP": cs_ip,
                "CS Port": cs_port,
                "CS Protokol": cs_protocol,
                "Load Balancer": lb_name,
                "VS IP": lb_ip,
                "VS Port": lb_port,
                "VS Protokol": lb_protocol,
                "Backend Server": sgrp_name,
                "IP Adresi": sgrp.get("ipv46", "N/A"),
                "Port": str(sgrp.get("port", "")),
                "CIP": cip_val
            })

def main():
    try:
        sirketler = config_manager.load_settings()
    except Exception as e:
        print(f"[-] Config Hatasi: {e}")
        return

    if not sirketler:
        print("[-] settings.json içinde şirket bulunamadı!")
        return

    selected_company_names = select_companies_menu(sirketler)
    sirketler_to_process = {k: v for k, v in sirketler.items() if k in selected_company_names}
    
    clear_screen()
    print("[*] Seçilen şirketler için işlemler başlatılıyor...\n")

    for sirket_adi, sirket_config in sirketler_to_process.items():
        print(f"==========================================")
        print(f"[*] {sirket_adi} ŞİRKETİ İŞLENİYOR...")
        print(f"==========================================")

        ns_ip = os.getenv(f"{sirket_adi}_NS_IP") or os.getenv("NS_IP")
        ns_user = os.getenv(f"{sirket_adi}_NS_USER") or os.getenv("NS_USER")
        ns_pass = os.getenv(f"{sirket_adi}_NS_PASS") or os.getenv("NS_PASS")

        if not all([ns_ip, ns_user, ns_pass]):
            print(f"[-] HATA: {sirket_adi} için IP/User/Pass eksik! Bu sirketi atliyoruz.\n")
            continue

        try:
            session, base_url, headers = netscaler_api.connect_and_login(ns_ip, ns_user, ns_pass)
        except Exception as e:
            print(f"[-] Baglanti Hatasi ({sirket_adi}): {e}\n")
            continue
        
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
                cs_ip = str(cs_info.get("ipv46", "N/A"))
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
                        get_lb_services(session, base_url, lb_name, cs_name, cs_desc, cs_ip, cs_port, cs_protocol, headers, report_data)
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
                "Content Switch", "CS Aciklama", "CS IP", "CS Port", "CS Protokol", 
                "Load Balancer", "VS IP", "VS Port", "VS Protokol", 
                "Backend Server", "IP Adresi", "Port", "CIP"
            ]
            
            excel_exporter.create_excel_report(report_data, fields, excel_path, EMPTY_ROW, sirket_adi)
            print(f"[+] {sirket_adi} Raporu (Excel) tamamlandi: {excel_path}\n")
        else:
            print(f"[-] {sirket_adi} için kayit bulunamadi.\n")

        netscaler_api.logout(session, base_url, headers)
        
    print("[✓] Tüm işlemler başarıyla tamamlandı.")

if __name__ == "__main__":
    main()