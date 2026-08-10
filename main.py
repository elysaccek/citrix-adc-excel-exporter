import os
from dotenv import load_dotenv
import netscaler_api
import config_manager
import excel_exporter
import dataset_manager

load_dotenv()

EMPTY_ROW = {
    "Content Switch": "", "CS Aciklama": "", "CS IP": "", "CS Port": "", "CS Protokol": "",
    "CS Policy Name": "", "CS Policy Priority": "", "CS Policy Rule": "",
    "Load Balancer": "", "VS IP": "", "VS Port": "", "VS Protokol": "",
    "Backend Server": "", "IP Adresi": "", "Port": "", "CIP": ""
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
        print(" [C] ÇALIŞTIR   | [Q] Çıkış")
        print("==========================================")
        
        choice = input("Seçiminiz: ").strip().upper()
        
        if choice == 'Q':
            exit(0)
        elif choice == 'C':
            sel = [name for name, is_sel in selected.items() if is_sel]
            if not sel:
                input("\n[!] En az bir şirket seçin! (Enter ile devam)...")
                continue
            return sel
        elif choice == 'T':
            for name in selected: selected[name] = True
        elif choice == 'B':
            for name in selected: selected[name] = False
        elif choice.isdigit() and 0 <= (int(choice) - 1) < len(company_names):
            name = company_names[int(choice) - 1]
            selected[name] = not selected[name]
        else:
            input("\n[!] Hatalı giriş! (Enter ile devam)...")

def add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info):    
    lb_info = netscaler_api.get_lb_info(session, base_url, headers, lb_name)
    backends = netscaler_api.get_backend_services(session, base_url, headers, lb_name)
    
    for backend in backends:
        report_data.append({
            "Content Switch": cs_info["name"],
            "CS Aciklama": cs_info["desc"],
            "CS IP": cs_info["ip"],
            "CS Port": cs_info["port"],
            "CS Protokol": cs_info["protocol"],
            "CS Policy Name": cs_info["pol_name"],
            "CS Policy Priority": cs_info["pol_pri"],
            "CS Policy Rule": cs_info["pol_rule"],
            "Load Balancer": lb_name,
            "VS IP": lb_info["ip"],
            "VS Port": lb_info["port"],
            "VS Protokol": lb_info["protocol"],
            "Backend Server": backend["name"],
            "IP Adresi": backend["ip"],
            "Port": backend["port"],
            "CIP": backend["cip"]
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
            print(f"[-] HATA: Eksik kimlik bilgisi! Atlanıyor...\n")
            continue

        try:
            session, base_url, headers = netscaler_api.connect_and_login(ns_ip, ns_user, ns_pass)
        except Exception as e:
            print(f"[-] Baglanti Hatasi: {e}\n")
            continue
        
        report_data = []
        processed_lbs = set()  
        
        cs_listesi = sirket_config.get("HEDEF_CS_LISTESI", [])
        lb_listesi = sirket_config.get("HEDEF_LB_LISTESI", [])

        for cs_item in cs_listesi:
            cs_name = cs_item.get("NAME")
            print(f"[*] CS isleniyor: {cs_name}")
            
            cs_api_info = netscaler_api.get_cs_info(session, base_url, headers, cs_name)
            if not cs_api_info:
                print(f"[-] HATA: '{cs_name}' bulunamadı.")
                continue

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
                    add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info)
                    processed_lbs.add(lb_name)
                report_data.append(EMPTY_ROW)
            else:
                print(f"    [!] Hedef LB veya Policy bulunamadı.")

        for lb_name in lb_listesi:
            if lb_name in processed_lbs:
                continue
                
            print(f"[*] Bagimsiz LB isleniyor: {lb_name}")
            cs_info = {
                "name": "N/A", "desc": "Bağımsız VS", "ip": "N/A", "port": "N/A", 
                "protocol": "N/A", "pol_name": "N/A", "pol_pri": "N/A", "pol_rule": "N/A"
            }
            add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info)
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

            excel_exporter.create_excel_report(report_data, fields, excel_path, EMPTY_ROW, sirket_adi, datasets_data)
            print(f"[+] {sirket_adi} Raporu tamamlandi: {excel_path}\n")
        else:
            print(f"[-] Kayit bulunamadi.\n")

        netscaler_api.logout(session, base_url, headers)
        
    print("[✓] Tüm işlemler başarıyla tamamlandı.")

if __name__ == "__main__":
    main()