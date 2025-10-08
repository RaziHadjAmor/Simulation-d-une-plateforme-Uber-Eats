import json

# Charger les fichiers JSON
with open('dataset_json/Client.json', encoding='utf-8') as f:
    clients = {c['id_client']: c for c in json.load(f)}

with open('dataset_json/Restaurant.json', encoding='utf-8') as f:
    restaurants = {r['id_restaurant']: r for r in json.load(f)}

with open('dataset_json/Plat.json', encoding='utf-8') as f:
    plats = {p['id_plat']: p for p in json.load(f)}

with open('dataset_json/Livreur.json', encoding='utf-8') as f:
    livreurs = {l['id_livreur']: l for l in json.load(f)}

with open('dataset_json/Commande.json', encoding='utf-8') as f:
    commandes = json.load(f)

with open('dataset_json/Commande_Plat.json', encoding='utf-8') as f:
    commande_plats = json.load(f)

with open('dataset_json/Course.json', encoding='utf-8') as f:
    courses = {c['id_commande']: c for c in json.load(f)}

# Construire la structure dénormalisée
result = []

for commande in commandes:
    cmd_id = commande['id_commande']

    # Rassembler les plats de cette commande avec leur quantité et détails
    plats_commande = []
    for cp in commande_plats:
        if cp['id_commande'] == cmd_id:
            plat_info = plats.get(cp['id_plat'], {})
            plat_copy = plat_info.copy()
            plat_copy['quantite'] = cp['quantite']
            plats_commande.append(plat_copy)

    # Ajouter client, restaurant, livreur, course
    client_info = clients.get(commande['id_client'], {})
    restaurant_info = restaurants.get(commande['id_restaurant'], {})
    course_info = courses.get(cmd_id, {})
    livreur_info = livreurs.get(course_info.get('id_livreur', ''), {})

    doc = {
        'commande': commande,
        'client': client_info,
        'restaurant': restaurant_info,
        'plats': plats_commande,
        'course': course_info,
        'livreur': livreur_info
    }
    result.append(doc)

# Sauvegarde du fichier JSON dénormalisé
with open('dataset_json/dataset_complet.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=4, ensure_ascii=False)