import requests
import base64

def fetch_azure_deployment_targets(server_url, collection, project, deployment_group_id, pat):
    print(f"\n[*] Azure DevOps üzerinden sunucu listesi ve tag bilgileri çekiliyor... (Grup ID: {deployment_group_id})")
    
    auth_str = f":{pat}"
    b64_auth = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/json"
    }
    
    api_url = f"{server_url}/{collection}/{project}/_apis/distributedtask/deploymentgroups/{deployment_group_id}/targets?api-version=7.0"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        targets = data.get("value", [])
        
        if not targets:
            print("[-] Belirtilen Deployment Group içerisinde herhangi bir sunucu bulunamadı.")
            return []
            
        #print("-" * 80)
        #print(f"{'Server Name'.ljust(30)} | {'Health Status'.ljust(15)} | {'Tags'}")
        #print("-" * 80)
        
        server_list = []
        for target in targets:
            agent = target.get("agent", {})
            server_name = agent.get("name", "Bilinmiyor")
            health_status = agent.get("status", "Bilinmiyor")
            
            tags = target.get("tags", [])
            tags_str = ", ".join(tags) if tags else ""
            
            server_list.append({
                "ServerName": server_name,
                "HealthStatus": health_status,
                "Tags": tags_str
            })
            
            #print(f"{server_name.ljust(30)} | {health_status.ljust(15)} | {tags_str}")
            
        #print("-" * 80)
        print(f"[+] Toplam {len(server_list)} sunucu Azuredan başarıyla çekildi.\n")
        
        return server_list
        
    except requests.exceptions.RequestException as e:
        print("[-] API çağrısı sırasında bir hata oluştu. Lütfen URL, PAT ve ağ erişiminizi kontrol edin.")
        print(f"[-] Hata Detayı: {e}\n")
        return []