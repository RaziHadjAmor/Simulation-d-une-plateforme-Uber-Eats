import json
import os

def fusionner_fichiers_json():
    """
    Lit les fichiers JSON des restaurants, plats, clients et livreurs,
    les fusionne en une structure unique et cohérente, puis sauvegarde
    le résultat dans un nouveau fichier.
    """
    fichiers_sources = {
        "restaurants": "dataset_json/restaurants.json",
        "plats": "dataset_json/plats.json",
        "livreurs": "dataset_json/livreurs.json"
    }
    
    donnees_brutes = {}
    
    # --- 1. Lecture de tous les fichiers sources ---
    print("Lecture des fichiers sources...")
    for cle, nom_fichier in fichiers_sources.items():
        if not os.path.exists(nom_fichier):
            print(f"❌ ERREUR: Le fichier '{nom_fichier}' est introuvable. Arrêt du script.")
            return
        try:
            with open(nom_fichier, 'r', encoding='utf-8') as f:
                donnees_brutes[cle] = json.load(f)
            print(f"  - Fichier '{nom_fichier}' chargé.")
        except json.JSONDecodeError:
            print(f"❌ ERREUR: Le fichier '{nom_fichier}' contient un JSON invalide.")
            return
    
    # --- 2. Création de la structure de données finale ---
    print("\nFusion et structuration des données...")
    
    # Créer un dictionnaire pour un accès rapide aux restaurants par leur ID
    restaurants_map = {resto['id_restaurant']: resto for resto in donnees_brutes["restaurants"]}
    
    # Initialiser une liste vide pour le menu de chaque restaurant
    for resto_id in restaurants_map:
        restaurants_map[resto_id]['menu'] = []

    # Associer chaque plat à son restaurant
    for plat in donnees_brutes["plats"]:
        id_resto_associe = plat.get("id_restaurant")
        if id_resto_associe in restaurants_map:
            # Ajouter le plat au menu du bon restaurant
            restaurants_map[id_resto_associe]['menu'].append(plat)
        else:
            print(f"  - ⚠️ AVERTISSEMENT: Le plat '{plat.get('id_plat')}' a un id_restaurant '{id_resto_associe}' qui ne correspond à aucun restaurant connu.")

    # Préparer le JSON final
    donnees_finales = {
        "restaurants": list(restaurants_map.values()),
        "livreurs": donnees_brutes["livreurs"]
    }
    print("-> Fusion terminée.")

    # --- 3. Sauvegarde du fichier JSON fusionné ---
    fichier_destination = "dataset_json/donnees_completes.json"
    try:
        with open(fichier_destination, 'w', encoding='utf-8') as f:
            # indent=4 pour une belle mise en forme, ensure_ascii=False pour bien gérer les accents
            json.dump(donnees_finales, f, indent=4, ensure_ascii=False)
        print(f"\n🎉 SUCCÈS ! Les données ont été fusionnées dans '{fichier_destination}'.")
    except Exception as e:
        print(f"\n❌ ERREUR lors de la sauvegarde du fichier : {e}")

if __name__ == "__main__":
    fusionner_fichiers_json()