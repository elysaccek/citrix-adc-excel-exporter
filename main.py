import os
import re
import sys
from dotenv import load_dotenv
import netscaler_api
import config_manager
import excel_exporter
import dataset_manager
import azure_manager
from language_manager import _  

load_dotenv()

EMPTY_ROW = {
    "Content Switch": "", "CS Aciklama": "", "CS IP": "", "CS Port": "", "CS Protokol": "",
    "CS Policy Name": "", "CS Policy Priority": "", "CS Policy Rule": "",
    "Load Balancer": "", "VS IP": "", "VS Port": "", "VS Protokol": "",
    "Backend Server": "", "IP Adresi": "", "Port": "",
    "Azure Hostname": "", "Azure Tag": "",
    "Persistence": "",
    "Time-out (mins)": "",
    "Cookie Name": "",
    "Backup Persistence": "",
    "Backup Time-out (mins)": "",
    "IPv4 Netmask": "",
    "IPv6 Mask Length": ""
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def select_companies_menu(sirketler):
    company_names = list(sirketler.keys())
    selected = {name: True for name in company_names}
    
    while True:
        clear_screen()
        print("==========================================")
        print(f"      {_('menu.header_title')}         ")
        print("==========================================")
        print(f"{_('menu.select_companies')}\n")
        
        for i, name in enumerate(company_names, 1):
            mark = "X" if selected[name] else " "
            print(f" [{mark}] {i}. {name}")
            
        print("\n------------------------------------------")
        print(f" {_('menu.actions')}")
        print(f" {_('menu.select_all')}")
        print(f" {_('menu.run')}")
        print(f" {_('menu.quit')}")
        print("==========================================")
        
        choice = input(_('menu.choice')).strip().upper()
        
        if choice == 'Q':
            exit(0)
        elif choice == 'C':
            sel = [name for name, is_sel in selected.items() if is_sel]
            if not sel:
                input(_('error.min_one_company'))
                continue
            return sel, 'RUN'
        elif choice == 'Z':
            sel = [name for name, is_sel in selected.items() if is_sel]
            if not sel:
                input(_('error.min_one_company'))
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
            input(_('error.invalid_input'))

def add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info, azure_servers, sirket_config, policy_data, processed_policy_vservers, services_data):    
    lb_info = netscaler_api.get_lb_info(session, base_url, headers, lb_name)

    if not lb_info:
        print(_('error.lb_not_found', lb_name=lb_name))
        row = {
            "Content Switch": cs_info["name"], "CS Aciklama": cs_info["desc"],
            "CS IP": cs_info["ip"], "CS Port": cs_info["port"], "CS Protokol": cs_info["protocol"],
            "CS Policy Name": cs_info["pol_name"], "CS Policy Priority": cs_info["pol_pri"], "CS Policy Rule": cs_info["pol_rule"],
            "Load Balancer": lb_name, "VS IP": _('value.no_definition'), "VS Port": "-", "VS Protokol": "-",
            "Backend Server": "-", "IP Adresi": "-", "Port": "-",
            "Azure Hostname": "-", "Azure Tag": "-",
            "_highlight_lb_missing_red": True
        }
        report_data.append(row)
        return

    persistence_fields = {
        "Persistence": lb_info.get("persistence", "N/A"),
        "Time-out (mins)": lb_info.get("persistence_timeout", "N/A"),
        "Cookie Name": lb_info.get("cookie_name", ""),
        "Backup Persistence": lb_info.get("backup_persistence", "N/A"),
        "Backup Time-out (mins)": lb_info.get(
            "backup_persistence_timeout", "N/A"
        ),
        "IPv4 Netmask": lb_info.get("ipv4_netmask", "N/A"),
        "IPv6 Mask Length": lb_info.get("ipv6_mask_length", "N/A")
    }
    backends = netscaler_api.get_backend_services(session, base_url, headers, lb_name)

    if not backends:
        backends = [{"name": _('value.no_pool'), "ip": "-", "port": "-", "cip": "-"}]

    for backend in backends:
        if backend["name"] != _('value.no_pool') and backend["name"] not in services_data:
            services_data[backend["name"]] = backend

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
                "Backend Server": lb_b["name"], "IP Adresi": lb_b["ip"], "Port": lb_b["port"],
                "Azure Hostname": az_b["ServerName"], "Azure Tag": expected_tag if in_az else "-"
            }

            row.update(persistence_fields)
            
            if not in_az and lb_b["name"] != _('value.no_pool'):
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
                    "Backend Server": lb_b["name"], "IP Adresi": lb_b["ip"], "Port": lb_b["port"],
                    "Azure Hostname": az_b["ServerName"], "Azure Tag": expected_tag
                }
                row.update(persistence_fields)
                row["_highlight_azure_red"] = True
                report_data.append(row)
                
    else:
        for backend in backends:
            row = {
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
                "Azure Hostname": "",
                "Azure Tag": ""
            }

            row.update(persistence_fields)
            report_data.append(row)
    

def run_custom_report(ns_ip, ns_user, ns_pass):
    from datetime import datetime

    session = None
    report_saved = False

    ns_ip = str(ns_ip).strip()
    ns_ip = re.sub(r"^https?://", "", ns_ip, flags=re.IGNORECASE)
    ns_ip = ns_ip.rstrip("/")

    safe_ip = re.sub(r"[^A-Za-z0-9.-]+", "-", ns_ip).strip("-")

    if not safe_ip:
        print("[!] Geçerli bir NLB IP adresi girilmelidir.")
        return

    try:
        print(f"[*] Custom rapor başlatılıyor: {ns_ip}")

        session, base_url, headers = netscaler_api.connect_and_login(
            ns_ip, ns_user, ns_pass
        )

        all_cs = netscaler_api.get_all_vservers(
            session, base_url, headers, "csvserver"
        )
        all_lbs = netscaler_api.get_all_vservers(
            session, base_url, headers, "lbvserver"
        )

        cs_names = sorted({
            item["name"] for item in all_cs if item.get("name")
        })
        lb_names = sorted({
            item["name"] for item in all_lbs if item.get("name")
        })

        print(
            f"[*] Keşfedilen CS sayısı: {len(cs_names)}, "
            f"LB sayısı: {len(lb_names)}"
        )

        if not cs_names and not lb_names:
            raise RuntimeError(
                "Cihazda raporlanabilecek CS veya LB Virtual Server bulunamadı."
            )

        report_data = []
        policy_data = []
        services_data = {}

        processed_lbs = set()
        processed_policy_vservers = set()

        sirket_config = {}
        azure_servers = None

        for cs_name in cs_names:
            print(f"[*] CS işleniyor: {cs_name}")

            cs_api_info = netscaler_api.get_cs_info(
                session, base_url, headers, cs_name
            )

            if not cs_api_info:
                print(f"[!] CS bilgisi alınamadı: {cs_name}")

                report_data.append({
                    "Content Switch": cs_name,
                    "CS Aciklama": "Custom Rapor",
                    "CS IP": "N/A",
                    "CS Port": "-",
                    "CS Protokol": "-",
                    "CS Policy Name": "-",
                    "CS Policy Priority": "-",
                    "CS Policy Rule": "-",
                    "Load Balancer": "-",
                    "VS IP": "-",
                    "VS Port": "-",
                    "VS Protokol": "-",
                    "Backend Server": "-",
                    "IP Adresi": "-",
                    "Port": "-",
                    "Azure Hostname": "-",
                    "Azure Tag": "-",
                    "_highlight_cs_red": True
                })
                report_data.append(EMPTY_ROW)
                continue

            if cs_name not in processed_policy_vservers:
                policy_data.extend(
                    netscaler_api.get_vserver_policies(
                        session,
                        base_url,
                        headers,
                        cs_name,
                        "csvserver",
                        cs_api_info
                    )
                )
                processed_policy_vservers.add(cs_name)

            target_lbs = netscaler_api.get_cs_target_lbs(
                session, base_url, headers, cs_name
            )

            if target_lbs:
                for lb_name, policy_info in target_lbs.items():
                    cs_info = {
                        "name": cs_name,
                        "desc": "Custom Rapor",
                        "ip": cs_api_info["ip"],
                        "port": cs_api_info["port"],
                        "protocol": cs_api_info["protocol"],
                        "pol_name": "\n".join(policy_info["names"]),
                        "pol_pri": "\n".join(policy_info["priorities"]),
                        "pol_rule": "\n".join(policy_info["rules"])
                    }

                    add_lb_to_report(
                        session,
                        base_url,
                        headers,
                        report_data,
                        lb_name,
                        cs_info,
                        azure_servers,
                        sirket_config,
                        policy_data,
                        processed_policy_vservers,
                        services_data
                    )

                    processed_lbs.add(lb_name)

            else:
                report_data.append({
                    "Content Switch": cs_name,
                    "CS Aciklama": "Custom Rapor",
                    "CS IP": cs_api_info["ip"],
                    "CS Port": cs_api_info["port"],
                    "CS Protokol": cs_api_info["protocol"],
                    "CS Policy Name": "-",
                    "CS Policy Priority": "-",
                    "CS Policy Rule": "-",
                    "Load Balancer": "Hedef Yok",
                    "VS IP": "-",
                    "VS Port": "-",
                    "VS Protokol": "-",
                    "Backend Server": "-",
                    "IP Adresi": "-",
                    "Port": "-",
                    "Azure Hostname": "-",
                    "Azure Tag": "-"
                })

            report_data.append(EMPTY_ROW)

        for lb_name in lb_names:
            if lb_name in processed_lbs:
                continue

            print(f"[*] Bağımsız LB işleniyor: {lb_name}")

            cs_info = {
                "name": "N/A",
                "desc": "Bağımsız VS - Custom Rapor",
                "ip": "N/A",
                "port": "N/A",
                "protocol": "N/A",
                "pol_name": "N/A",
                "pol_pri": "N/A",
                "pol_rule": "N/A"
            }

            add_lb_to_report(
                session,
                base_url,
                headers,
                report_data,
                lb_name,
                cs_info,
                azure_servers,
                sirket_config,
                policy_data,
                processed_policy_vservers,
                services_data
            )

            report_data.append(EMPTY_ROW)

        if report_data and report_data[-1] == EMPTY_ROW:
            report_data.pop()

        if not report_data:
            raise RuntimeError("Rapor oluşturmak için kayıt bulunamadı.")

        datasets_data = {}

        all_rules = [
            row.get("CS Policy Rule", "")
            for row in report_data
        ]

        found_datasets = dataset_manager.extract_dataset_names(all_rules)

        if found_datasets:
            print(
                f"[*] {len(found_datasets)} Dataset bulundu. Çekiliyor..."
            )
            try:
                datasets_data = dataset_manager.fetch_datasets_from_ns(
                    session, base_url, headers, found_datasets
                )
            except Exception as e:
                print(f"[!] Dataset bilgileri alınamadı: {e}")

        output_dir = "raporlar"
        os.makedirs(output_dir, exist_ok=True)

        date_string = datetime.now().strftime("%Y-%m-%d")
        filename = (
            f"{safe_ip}_{date_string}_citrix_lb_rapor.xlsx"
        )
        excel_path = os.path.join(output_dir, filename)

        fields = list(EMPTY_ROW.keys())

        excel_exporter.create_excel_report(
            report_data,
            fields,
            excel_path,
            EMPTY_ROW,
            f"Custom_{safe_ip}",
            datasets_data,
            policy_data,
            services_data
        )

        print(f"[+] Custom rapor kaydedildi: {excel_path}")
        report_saved = True

    except Exception as e:
        print(f"\n[!] Custom rapor hatası: {e}")

    finally:
        if session is not None:
            netscaler_api.logout(session, base_url, headers)

    if report_saved:
        print(_('info.all_done'))


def run_reports(selected_company_names):
    try:
        sirketler = config_manager.load_settings()
    except Exception as e:
        print(_('error.config', e=str(e)))
        return

    sirketler_to_process = {k: v for k, v in sirketler.items() if k in selected_company_names}
    
    print(_('info.starting'))

    for sirket_adi, sirket_config in sirketler_to_process.items():
        print(f"==========================================")
        print(_('info.processing_company', sirket_adi=sirket_adi))
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
                print(_('error.azure_env_missing', sirket_adi=sirket_adi))

        ns_ip = os.getenv(f"{sirket_adi}_NS_IP") or os.getenv("NS_IP")
        ns_user = os.getenv(f"{sirket_adi}_NS_USER") or os.getenv("NS_USER")
        ns_pass = os.getenv(f"{sirket_adi}_NS_PASS") or os.getenv("NS_PASS")

        if not all([ns_ip, ns_user, ns_pass]):
            print(_('error.missing_credentials'))
            continue

        try:
            session, base_url, headers = netscaler_api.connect_and_login(ns_ip, ns_user, ns_pass)
        except Exception as e:
            print(_('error.connection', e=str(e)))
            continue
        
        report_data = []
        policy_data = []
        services_data = {} 
        processed_lbs = set()
        processed_policy_vservers = set()
        
        cs_listesi = sirket_config.get("HEDEF_CS_LISTESI", [])
        lb_listesi = sirket_config.get("HEDEF_LB_LISTESI", [])

        for cs_item in cs_listesi:
            cs_name = cs_item.get("NAME")
            print(_('info.processing_cs', cs_name=cs_name))
            
            cs_api_info = netscaler_api.get_cs_info(session, base_url, headers, cs_name)

            if not cs_api_info:
                print(_('error.cs_not_found', cs_name=cs_name))
                report_data.append({
                    "Content Switch": cs_name, "CS Aciklama": cs_item.get("DESCRIPTION", _('value.no_description')),
                    "CS IP": _('value.no_definition'), "CS Port": "-", "CS Protokol": "-",
                    "CS Policy Name": "-", "CS Policy Priority": "-", "CS Policy Rule": "-",
                    "Load Balancer": "-", "VS IP": "-", "VS Port": "-", "VS Protokol": "-",
                    "Backend Server": "-", "IP Adresi": "-", "Port": "-",
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
                        "desc": cs_item.get("DESCRIPTION", _('value.no_description')),
                        "ip": cs_api_info["ip"],
                        "port": cs_api_info["port"],
                        "protocol": cs_api_info["protocol"],
                        "pol_name": "\n".join(p_data["names"]),
                        "pol_pri": "\n".join(p_data["priorities"]),
                        "pol_rule": "\n".join(p_data["rules"])
                    }
                    add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info, azure_server_list, sirket_config, policy_data, processed_policy_vservers, services_data)
                    processed_lbs.add(lb_name)
                report_data.append(EMPTY_ROW)
            else:
                print(_('value.no_target_lb'))
                report_data.append({
                    "Content Switch": cs_name, "CS Aciklama": cs_item.get("DESCRIPTION", _('value.no_description')),
                    "CS IP": cs_api_info["ip"], "CS Port": cs_api_info["port"], "CS Protokol": cs_api_info["protocol"],
                    "CS Policy Name": "-", "CS Policy Priority": "-", "CS Policy Rule": "-",
                    "Load Balancer": _('value.no_target'), "VS IP": "-", "VS Port": "-", "VS Protokol": "-",
                    "Backend Server": "-", "IP Adresi": "-", "Port": "-",
                    "Azure Hostname": "-", "Azure Tag": "-"
                })
                report_data.append(EMPTY_ROW)

        for lb_name in lb_listesi:
            if lb_name in processed_lbs:
                continue
                
            print(_('info.processing_independent_lb', lb_name=lb_name))
            cs_info = {
                "name": "N/A", "desc": _('value.independent_vs'), "ip": "N/A", "port": "N/A", 
                "protocol": "N/A", "pol_name": "N/A", "pol_pri": "N/A", "pol_rule": "N/A"
            }
            add_lb_to_report(session, base_url, headers, report_data, lb_name, cs_info, azure_server_list, sirket_config, policy_data, processed_policy_vservers, services_data)
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
                print(_('info.datasets_found', count=len(found_datasets)))
                datasets_data = dataset_manager.fetch_datasets_from_ns(session, base_url, headers, found_datasets)

            excel_exporter.create_excel_report(report_data, fields, excel_path, EMPTY_ROW, sirket_adi, datasets_data, policy_data, services_data)
            print(_('info.report_completed', sirket_adi=sirket_adi, excel_path=excel_path))
        else:
            print(_('error.no_records'))

        netscaler_api.logout(session, base_url, headers)
        
    print(_('info.all_done'))

def run_azure_liste(selected_company_names):
    try:
        sirketler = config_manager.load_settings()
    except Exception as e:
        print(_('error.config', e=str(e)))
        return

    sirketler_to_process = {k: v for k, v in sirketler.items() if k in selected_company_names}
    
    print(_('info.starting_azure_only'))

    for sirket_adi, sirket_config in sirketler_to_process.items():
        print(f"==========================================")
        print(_('info.azure_servers_title', sirket_adi=sirket_adi))
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
                print(_('error.azure_env_missing_list', sirket_adi=sirket_adi))
        else:
            print(_('error.azure_disabled', sirket_adi=sirket_adi))

    input(_('info.list_done'))

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
                print(_('error.config', e=str(e)))
                return

            if not sirketler:
                print(_('error.no_company_in_settings'))
                return

            selected_company_names, action = select_companies_menu(sirketler)
            clear_screen()
            
            if action == 'RUN':
                run_reports(selected_company_names)
                input(_('info.press_enter_to_continue'))
            elif action == 'AZURE_LISTE':
                run_azure_liste(selected_company_names)

if __name__ == "__main__":
    main()