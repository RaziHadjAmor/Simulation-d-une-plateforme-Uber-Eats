import redis
import json
import os

def importer_donnees_depuis_json(fichier_json="dataset_json/donnees_completes.json"):
    """
    Vide la base de données Redis et la peuple avec les données
    contenues dans le fichier JSON complet.
    """
    # 1. Connexion à Redis
    try:
        r = redis.Redis(decode_responses=True)
        r.ping() # Vérifie que la connexion est active
    except redis.exceptions.ConnectionError as e:
        print(f"❌ ERREUR: Impossible de se connecter à Redis.")
        print("   Veuillez vous assurer que votre conteneur Docker 'UberEatsRedis' est bien en cours d'exécution.")
        print(f"   Détail de l'erreur : {e}")
        return

    # 2. Charger les données depuis le fichier JSON
    if not os.path.exists(fichier_json):
        print(f"❌ ERREUR: Le fichier '{fichier_json}' est introuvable. Assurez-vous qu'il est dans le même dossier que ce script.")
        return
    try:
        with open(fichier_json, 'r', encoding='utf-8') as f:
            donnees = json.load(f)
        print(f"✅ Fichier '{fichier_json}' chargé avec succès.")
    except json.JSONDecodeError:
        print(f"❌ ERREUR: Le contenu de '{fichier_json}' n'est pas un JSON valide.")
        return

    # 3. Nettoyer la base de données Redis avant l'importation
    print("\nNettoyage de la base de données Redis (FLUSHDB)...")
    r.flushdb()

    # 4. Importer les données en utilisant les structures Redis appropriées
    try:
        # Importer les restaurants et leurs plats
        print("Importation des restaurants et de leurs menus...")
        for resto in donnees.get("restaurants", []):
            resto_id = resto['id_restaurant']
            # Créer un Hash pour le restaurant
            r.hset(f"restaurant:{resto_id}", mapping={
                "nom": resto.get("nom", "N/A"),
                "adresse": resto.get("adresse", "N/A")
            })
            # Gérer le menu associé
            for plat in resto.get("menu", []):
                plat_id = plat['id_plat']
                # Créer un Hash pour le plat
                r.hset(f"plat:{plat_id}", mapping={
                    "nom": plat.get("nom", "N/A"),
                    "description": plat.get("description", ""),
                    "prix": plat.get("prix", "0.00"),
                    "id_restaurant": resto_id
                })
                # Ajouter l'ID du plat au Set du menu du restaurant
                r.sadd(f"restaurant:{resto_id}:plats", plat_id)

        # Importer les clients
        print("Importation des clients...")
        for client in donnees.get("clients", []):
            r.hset(f"client:{client['id_client']}", mapping=client)

        # Importer les livreurs
        print("Importation des livreurs...")
        for livreur in donnees.get("livreurs", []):
            r.hset(f"livreur:{livreur['id_livreur']}", mapping=livreur)
            
        print("\n🎉 SUCCÈS ! Toutes les données ont été importées dans Redis.")

    except KeyError as e:
        print(f"❌ ERREUR: Une clé attendue est manquante dans le fichier JSON : {e}")
    except Exception as e:
        print(f"❌ ERREUR inattendue lors de l'importation : {e}")


if __name__ == "__main__":
    importer_donnees_depuis_json()
