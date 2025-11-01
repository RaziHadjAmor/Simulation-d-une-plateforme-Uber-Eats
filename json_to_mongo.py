import json
import os
from pymongo import MongoClient

# Connexion à MongoDB (assurez-vous qu'il tourne avec le Replica Set !)
try:
    client = MongoClient("mongodb://localhost:27017/?replicaSet=rs0")
    db = client["ubereats_db"]
    client.server_info() # Teste la connexion
    print("✅ Connexion à MongoDB réussie.")
except Exception as e:
    print("❌ ERREUR: Impossible de se connecter à MongoDB.")
    print("   Assurez-vous d'avoir lancé MongoDB avec docker-compose up")
    print(f"   Détail: {e}")
    exit()

FICHIER_JSON = "dataset_json/donnees_completes.json"

def importer_donnees():
    # 1. Charger le fichier JSON
    if not os.path.exists(FICHIER_JSON):
        print(f"❌ ERREUR: Le fichier '{FICHIER_JSON}' est introuvable.")
        return
    
    with open(FICHIER_JSON, 'r', encoding='utf-8') as f:
        donnees = json.load(f)
    print(f"✅ Fichier '{FICHIER_JSON}' chargé.")

    # 2. Nettoyer les collections existantes
    print("\nNettoyage des collections existantes...")
    db.restaurants.drop()
    db.livreurs.drop()
    db.commandes.drop() # Vider aussi les commandes précédentes

    # 3. Insérer les données
    try:
        # Insérer les restaurants (avec leur menu imbriqué)
        if "restaurants" in donnees:
            db.restaurants.insert_many(donnees["restaurants"])
            print(f"-> {len(donnees['restaurants'])} restaurants importés.")
            # Créer un index de recherche sur le nom
            db.restaurants.create_index("nom")
            print("   (Index de recherche créé sur 'nom')")

        # Insérer les clients
        if "clients" in donnees:
            db.clients.insert_many(donnees["clients"])
            print(f"-> {len(donnees['clients'])} clients importés.")

        # Insérer les livreurs
        if "livreurs" in donnees:
            db.livreurs.insert_many(donnees["livreurs"])
            print(f"-> {len(donnees['livreurs'])} livreurs importés.")
            
        print("\n🎉 SUCCÈS ! Toutes les données ont été importées dans MongoDB.")
    
    except Exception as e:
        print(f"❌ ERREUR lors de l'importation : {e}")

if __name__ == "__main__":
    importer_donnees()