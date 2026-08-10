import re

def extract_dataset_names(rules_list):
    dataset_names = set()
    pattern = re.compile(r'(?:CONTAINS_ANY|EQUALS_ANY)\(\s*"([^"]+)"\s*\)')
    
    for rule in rules_list:
        if rule and rule != "N/A":
            matches = pattern.findall(rule)
            for match in matches:
                dataset_names.add(match)
                
    return dataset_names

def fetch_datasets_from_ns(session, base_url, headers, dataset_names):
    datasets_cache = {}
    
    for ds_name in dataset_names:
        print(f"    [+] Dataset çekiliyor: {ds_name}...")
        ds_url = f"{base_url}/policydataset_value_binding/{ds_name}"
        
        try:
            res = session.get(ds_url, headers=headers)
            if res.status_code == 200:
                bindings = res.json().get("policydataset_value_binding", [])
                
                extracted_ips = []
                for idx, item in enumerate(bindings, 1):
                    nlb_index = item.get("index", "")

                    val = item.get("value", "")
                    end_val = item.get("endvalue", "")
                    
                    if end_val and end_val != val:
                        ip_text = f"{val} - {end_val}"
                    else:
                        ip_text = val
                        
                    extracted_ips.append({
                        "ID": idx,
                        "Index": nlb_index,
                        "IP": ip_text
                    })
                    
                datasets_cache[ds_name] = extracted_ips
            else:
                print(f"    [-] Dataset bulunamadı veya boş: {ds_name}")
        except Exception as e:
            print(f"    [-] Dataset çekilirken hata ({ds_name}): {e}")
            
    return datasets_cache