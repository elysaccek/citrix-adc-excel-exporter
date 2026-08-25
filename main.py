import os
import re
import sys
from dotenv import load_dotenv
import netscaler_api
import config_manager
import excel_exporter
import dataset_manager
import azure_manager

load_dotenv()

EMPTY_ROW = {
    "Content Switch": "", "CS Aciklama": "", "CS IP": "", "CS Port": "", "CS Protokol": "",
    "CS Policy Name": "", "CS Policy Priority": "", "CS Policy Rule": "",
    "Load Balancer": "", "VS IP": "", "VS Port": "", "VS Protokol": "",
    "Backend Server": "", "IP Adresi": "", "Port": "", "CIP": "",
    "Azure Hostname": "", "Azure Tag": ""
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def select_companies_menu(sirketler):
    company_names = list(sirketler.keys())
    selected = {name: True for name in company_names}
    
    while True:
        clear_screen()
        print("==========================================")
        print("      CITRIX NLB RAPORLAMA PANELİ         ")
        print("==========================================")
        print("Çalıştırmak istediğiniz şirketleri seçin:\n")
        
        for i, name in enumerate(company_names, 1):
            mark = "X" if selected[name] else " "
            print(f" [{mark}] {i}. {name}")
            
        print("\n------------------------------------------")
        print(" İşlemler:")
        print(" [T] Tümünü Seç | [B] Seçimi Bırak")
        print(" [C] ÇALIŞTIR (Tam Rapor) | [Z] AZURE LİSTE (Sadece Liste)")
        print(" [Q] Çıkış")
        print("==========================================")
        
        choice = input("Seçiminiz: ").strip().upper()
        
        if choice == 'Q':
            exit(0)
        elif choice == 'C':
            sel = [name for name, is_sel in selected.items() if is_sel]
            if not sel:
                input("\n[!] En az bir şirket seçin! (Enter ile devam)...")
                continue
            return sel, 'RUN'
        elif choice == 'Z':
            sel = [name for name, is_sel in selected.items() if is_sel]
            if not sel:
                input("\n[!] En az bir şirket seçin! (Enter ile devam)...")
                continue
            return sel, 'AZURE_LISTE'
        elif choice == 'T':
            for name in selected: selected[name] = True
        elif choice == 'B':
            for name in selected: selected[name] = False
        elif choice.isdigit() and 0 <= (int(choice) - 1) < len(company_names):
            name = company_names[int(choice) - 1]
            selected[name] = not selected[name]
        else:
            input("\n[!] Hatalı giriş! (Enter ile devam)...")

def add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info, azure_servers, sirket_config, policy_data, processed_policy_vservers):    
    lb_info = netscaler_api.get_lb_info(session, base_url, headers, lb_name)

    if not lb_info:
        print(f"    [!] HATA: '{lb_name}' bulunamadı. Raporlara eksik tanım olarak ekleniyor.")
        row = {
            "Content Switch": cs_info["name"], "CS Aciklama": cs_info["desc"],
            "CS IP": cs_info["ip"], "CS Port": cs_info["port"], "CS Protokol": cs_info["protocol"],
            "CS Policy Name": cs_info["pol_name"], "CS Policy Priority": cs_info["pol_pri"], "CS Policy Rule": cs_info["pol_rule"],
            "Load Balancer": lb_name, "VS IP": "Tanım Bulunmamaktadır", "VS Port": "-", "VS Protokol": "-",
            "Backend Server": "-", "IP Adresi": "-", "Port": "-", "CIP": "-",
            "Azure Hostname": "-", "Azure Tag": "-",
            "_highlight_lb_missing_red": True
        }
        report_data.append(row)
        return

    backends = netscaler_api.get_backend_services(session, base_url, headers, lb_name)

    if not backends:
        backends = [{"name": "Havuz Yok", "ip": "-", "port": "-", "cip": "-"}]

    if lb_name not in processed_policy_vservers:
        policy_data.extend(netscaler_api.get_vserver_policies(session, base_url, headers, lb_name, "lbvserver", lb_info))
        processed_policy_vservers.add(lb_name)
    
    lb_to_tag = {item.get("LB"): item.get("TAG") for item in sirket_config.get("AZURE_TAG_LB_ESLESMESI", [])}

    if lb_name in lb_to_tag and azure_servers is not None:
        expected_tag = lb_to_tag[lb_name]
        
        az_matches = {}
        for s in azure_servers:
            tags_list = [t.strip() for t in s["Tags"].split(",")]
            if expected_tag in tags_list:
                az_matches[s["ServerName"].upper()] = s
                
        lb_matches = {b["name"].upper(): b for b in backends}
        matched_az = set()
        
        for lb_raw_name, lb_b in lb_matches.items():
            base_hostname = re.sub(r'_\d+$', '', lb_raw_name)
            
            in_az = base_hostname in az_matches
            az_b = az_matches.get(base_hostname, {"ServerName": "-", "Tags": "-"})
            
            if in_az:
                matched_az.add(base_hostname)
                
            row = {
                "Content Switch": cs_info["name"], "CS Aciklama": cs_info["desc"],
                "CS IP": cs_info["ip"], "CS Port": cs_info["port"], "CS Protokol": cs_info["protocol"],
                "CS Policy Name": cs_info["pol_name"], "CS Policy Priority": cs_info["pol_pri"], "CS Policy Rule": cs_info["pol_rule"],
                "Load Balancer": lb_name, "VS IP": lb_info["ip"], "VS Port": lb_info["port"], "VS Protokol": lb_info["protocol"],
                "Backend Server": lb_b["name"], "IP Adresi": lb_b["ip"], "Port": lb_b["port"], "CIP": lb_b["cip"],
                "Azure Hostname": az_b["ServerName"], "Azure Tag": expected_tag if in_az else "-"
            }
            
            if not in_az and lb_b["name"] != "Havuz Yok":
                row["_highlight_lb_red"] = True
                
            report_data.append(row)
            
        for az_hostname, az_b in az_matches.items():
            if az_hostname not in matched_az:
                lb_b = {"name": "-", "ip": "-", "port": "-", "cip": "-"}
                row = {
                    "Content Switch": cs_info["name"], "CS Aciklama": cs_info["desc"],
                    "CS IP": cs_info["ip"], "CS Port": cs_info["port"], "CS Protokol": cs_info["protocol"],
                    "CS Policy Name": cs_info["pol_name"], "CS Policy Priority": cs_info["pol_pri"], "CS Policy Rule": cs_info["pol_rule"],
                    "Load Balancer": lb_name, "VS IP": lb_info["ip"], "VS Port": lb_info["port"], "VS Protokol": lb_info["protocol"],
                    "Backend Server": lb_b["name"], "IP Adresi": lb_b["ip"], "Port": lb_b["port"], "CIP": lb_b["cip"],
                    "Azure Hostname": az_b["ServerName"], "Azure Tag": expected_tag
                }
                row["_highlight_azure_red"] = True
                report_data.append(row)
                
    else:
        for backend in backends:
            report_data.append({
                "Content Switch": cs_info["name"], "CS Aciklama": cs_info["desc"],
                "CS IP": cs_info["ip"], "CS Port": cs_info["port"], "CS Protokol": cs_info["protocol"],
                "CS Policy Name": cs_info["pol_name"], "CS Policy Priority": cs_info["pol_pri"], "CS Policy Rule": cs_info["pol_rule"],
                "Load Balancer": lb_name, "VS IP": lb_info["ip"], "VS Port": lb_info["port"], "VS Protokol": lb_info["protocol"],
                "Backend Server": backend["name"], "IP Adresi": backend["ip"], "Port": backend["port"], "CIP": backend["cip"],
                "Azure Hostname": "", "Azure Tag": ""
            })

def run_reports(selected_company_names):
    try:
        sirketler = config_manager.load_settings()
    except Exception as e:
        print(f"[-] Config Hatasi: {e}")
        return

    sirketler_to_process = {k: v for k, v in sirketler.items() if k in selected_company_names}
    
    print("[*] Seçilen şirketler için işlemler başlatılıyor...\n")

    for sirket_adi, sirket_config in sirketler_to_process.items():
        print(f"==========================================")
        print(f"[*] {sirket_adi} ŞİRKETİ İŞLENİYOR...")
        print(f"==========================================")

        azure_server_list = None
        if sirket_config.get("AZURE") == True:
            az_url = os.getenv(f"{sirket_adi}_AZURE_SERVER_URL")
            az_col = os.getenv(f"{sirket_adi}_AZURE_COLLECTION")
            az_proj = os.getenv(f"{sirket_adi}_AZURE_PROJECT")
            az_dg_id = os.getenv(f"{sirket_adi}_AZURE_DEPLOYMENT_GROUP_ID")
            az_pat = os.getenv(f"{sirket_adi}_AZURE_PAT")
            
            if all([az_url, az_col, az_proj, az_dg_id, az_pat]):
                azure_server_list = azure_manager.fetch_azure_deployment_targets(az_url, az_col, az_proj, az_dg_id, az_pat)
            else:
                print(f"[-] {sirket_adi} için AZURE açık ancak .env değerleri eksik! Atlanıyor...\n")

        ns_ip = os.getenv(f"{sirket_adi}_NS_IP") or os.getenv("NS_IP")
        ns_user = os.getenv(f"{sirket_adi}_NS_USER") or os.getenv("NS_USER")
        ns_pass = os.getenv(f"{sirket_adi}_NS_PASS") or os.getenv("NS_PASS")

        if not all([ns_ip, ns_user, ns_pass]):
            print(f"[-] HATA: Eksik kimlik bilgisi! Atlanıyor...\n")
            continue

        try:
            session, base_url, headers = netscaler_api.connect_and_login(ns_ip, ns_user, ns_pass)
        except Exception as e:
            print(f"[-] Baglanti Hatasi: {e}\n")
            continue
        
        report_data = []
        policy_data = []
        processed_lbs = set()
        processed_policy_vservers = set()
        
        cs_listesi = sirket_config.get("HEDEF_CS_LISTESI", [])
        lb_listesi = sirket_config.get("HEDEF_LB_LISTESI", [])

        for cs_item in cs_listesi:
            cs_name = cs_item.get("NAME")
            print(f"[*] CS isleniyor: {cs_name}")
            
            cs_api_info = netscaler_api.get_cs_info(session, base_url, headers, cs_name)

            if not cs_api_info:
                print(f"[-] HATA: '{cs_name}' bulunamadı. Raporlara eksik tanım olarak ekleniyor.")
                report_data.append({
                    "Content Switch": cs_name, "CS Aciklama": cs_item.get("DESCRIPTION", "Açıklama Yok"),
                    "CS IP": "Tanım Bulunmamaktadır", "CS Port": "-", "CS Protokol": "-",
                    "CS Policy Name": "-", "CS Policy Priority": "-", "CS Policy Rule": "-",
                    "Load Balancer": "-", "VS IP": "-", "VS Port": "-", "VS Protokol": "-",
                    "Backend Server": "-", "IP Adresi": "-", "Port": "-", "CIP": "-",
                    "Azure Hostname": "-", "Azure Tag": "-",
                    "_highlight_cs_red": True
                })
                report_data.append(EMPTY_ROW)
                continue
            
            if cs_name not in processed_policy_vservers:
                policy_data.extend(netscaler_api.get_vserver_policies(session, base_url, headers, cs_name, "csvserver", cs_api_info))
                processed_policy_vservers.add(cs_name)

            target_lbs = netscaler_api.get_cs_target_lbs(session, base_url, headers, cs_name)
            
            if target_lbs:
                for lb_name, p_data in target_lbs.items():
                    cs_info = {
                        "name": cs_name,
                        "desc": cs_item.get("DESCRIPTION", "Açıklama Yok"),
                        "ip": cs_api_info["ip"],
                        "port": cs_api_info["port"],
                        "protocol": cs_api_info["protocol"],
                        "pol_name": "\n".join(p_data["names"]),
                        "pol_pri": "\n".join(p_data["priorities"]),
                        "pol_rule": "\n".join(p_data["rules"])
                    }
                    add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info, azure_server_list, sirket_config, policy_data, processed_policy_vservers)
                    processed_lbs.add(lb_name)
                report_data.append(EMPTY_ROW)
            else:
                print(f"    [!] Hedef LB veya Policy bulunamadı.")
                report_data.append({
                    "Content Switch": cs_name, "CS Aciklama": cs_item.get("DESCRIPTION", "Açıklama Yok"),
                    "CS IP": cs_api_info["ip"], "CS Port": cs_api_info["port"], "CS Protokol": cs_api_info["protocol"],
                    "CS Policy Name": "-", "CS Policy Priority": "-", "CS Policy Rule": "-",
                    "Load Balancer": "Hedef Yok", "VS IP": "-", "VS Port": "-", "VS Protokol": "-",
                    "Backend Server": "-", "IP Adresi": "-", "Port": "-", "CIP": "-",
                    "Azure Hostname": "-", "Azure Tag": "-"
                })
                report_data.append(EMPTY_ROW)

        for lb_name in lb_listesi:
            if lb_name in processed_lbs:
                continue
                
            print(f"[*] Bagimsiz LB isleniyor: {lb_name}")
            cs_info = {
                "name": "N/A", "desc": "Bağımsız VS", "ip": "N/A", "port": "N/A", 
                "protocol": "N/A", "pol_name": "N/A", "pol_pri": "N/A", "pol_rule": "N/A"
            }
            add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info, azure_server_list, sirket_config, policy_data, processed_policy_vservers)
            report_data.append(EMPTY_ROW)

        if report_data:
            if report_data[-1] == EMPTY_ROW:
                report_data.pop()

            excel_path = config_manager.get_report_filepath(sirket_adi)
            fields = list(EMPTY_ROW.keys())
            
            all_rules = [row.get("CS Policy Rule", "") for row in report_data]
            found_datasets = dataset_manager.extract_dataset_names(all_rules)

            datasets_data = {}
            if found_datasets:
                print(f"[*] {len(found_datasets)} Dataset bulundu. Çekiliyor...")
                datasets_data = dataset_manager.fetch_datasets_from_ns(session, base_url, headers, found_datasets)

            excel_exporter.create_excel_report(report_data, fields, excel_path, EMPTY_ROW, sirket_adi, datasets_data, policy_data)
            print(f"[+] {sirket_adi} Raporu tamamlandi: {excel_path}\n")
        else:
            print(f"[-] Kayit bulunamadi.\n")

        netscaler_api.logout(session, base_url, headers)
        
    print("[✓] Tüm işlemler başarıyla tamamlandı.\n")

def run_azure_liste(selected_company_names):
    try:
        sirketler = config_manager.load_settings()
    except Exception as e:
        print(f"[-] Config Hatasi: {e}")
        return

    sirketler_to_process = {k: v for k, v in sirketler.items() if k in selected_company_names}
    
    print("[*] Seçilen şirketler için YALNIZCA AZURE LİSTE başlatılıyor...\n")

    for sirket_adi, sirket_config in sirketler_to_process.items():
        print(f"==========================================")
        print(f"[*] {sirket_adi} - AZURE DEVOPS SUNUCULARI")
        print(f"==========================================")

        if sirket_config.get("AZURE") == True:
            az_url = os.getenv(f"{sirket_adi}_AZURE_SERVER_URL")
            az_col = os.getenv(f"{sirket_adi}_AZURE_COLLECTION")
            az_proj = os.getenv(f"{sirket_adi}_AZURE_PROJECT")
            az_dg_id = os.getenv(f"{sirket_adi}_AZURE_DEPLOYMENT_GROUP_ID")
            az_pat = os.getenv(f"{sirket_adi}_AZURE_PAT")
            
            if all([az_url, az_col, az_proj, az_dg_id, az_pat]):
                azure_manager.fetch_azure_deployment_targets(az_url, az_col, az_proj, az_dg_id, az_pat)
            else:
                print(f"[-] {sirket_adi} için AZURE açık ancak .env değerleri eksik!\n")
        else:
            print(f"[-] {sirket_adi} için settings.json'da AZURE özelliği kapalı (false).\n")

    input("\n[✓] Liste tamamlandı. Ana menüye dönmek için Enter'a basın...")

def main():
    is_web = os.getenv("WEB_VIEW", "False").strip().lower() == "true"
    port_number = os.getenv("PORT")
    
    if is_web:
        import web_app
        web_app.start_server(port_number)
    else:
        while True:
            try:
                sirketler = config_manager.load_settings()
            except Exception as e:
                print(f"[-] Config Hatasi: {e}")
                return

            if not sirketler:
                print("[-] settings.json içinde şirket bulunamadı!")
                return

            selected_company_names, action = select_companies_menu(sirketler)
            clear_screen()
            
            if action == 'RUN':
                run_reports(selected_company_names)
                input("\nİşlemler bitti. Devam etmek için Enter'a basın...")
            elif action == 'AZURE_LISTE':
                run_azure_liste(selected_company_names)

if __name__ == "__main__":
    main()