import redis
import json

# Connexion au serveur Redis (ajustez host, port, password si besoin)
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Chemin vers ton fichier JSON
filepath = 'dataset_json/dataset_complet.json'

with open(filepath, encoding='utf-8') as f:
    data = json.load(f)
    for item in data:
        commande_id = item['commande']['id_commande']
        key = f"commande:{commande_id}"
        # Stockage JSON complet en string dans Redis
        r.set(key, json.dumps(item, ensure_ascii=False))
        print(f"Stocké commande {commande_id}." )

print("Import terminé.")