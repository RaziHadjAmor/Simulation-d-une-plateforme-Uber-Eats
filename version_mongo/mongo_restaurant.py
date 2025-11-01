import threading
import time
import random
from pymongo import MongoClient

# Connexion
try:
    client = MongoClient("mongodb://localhost:27017/?replicaSet=rs0")
    db = client["ubereats_db"]
except Exception:
    print("❌ ERREUR: Connexion à MongoDB échouée.")
    exit()

RESTAURANT_ID = None

def ecouteur_restaurant():
    """Surveille les commandes assignées à CE restaurant."""
    
    pipeline = [{
        '$match': {
            'operationType': 'update',
            'updateDescription.updatedFields.statut': 'accepted_en_preparation',
            'fullDocument.restaurant_id': RESTAURANT_ID
        }
    }]
    
    try:
        # --- CORRECTION : Ajout de full_document='updateLookup' ---
        with db.commandes.watch(pipeline, full_document='updateLookup') as stream:
            for change in stream:
                commande = change['fullDocument']
                commande_id = commande['commande_id']
                print(f"\n[RESTAURANT] Nouvelle commande reçue : {commande_id}")
                
                print("  - Contenu à préparer :")
                for item in commande.get('plats_details', []):
                    print(f"    - {item.get('quantite')}x {item.get('nom')}")

                temps_preparation = random.randint(5, 12)
                print(f"[RESTAURANT] Préparation en cours... ({temps_preparation} secondes)")
                time.sleep(temps_preparation)
                
                # Mise à jour du statut -> déclenchera le Change Stream du Manager
                db.commandes.update_one(
                    {"commande_id": commande_id},
                    {"$set": {"statut": "ready_awaiting_livreur"}}
                )
                print(f"✅ [RESTAURANT] Commande {commande_id} prête pour la livraison !")
                
    except Exception as e:
        print(f"[Écouteur Restaurant] Erreur : {e}")

if __name__ == "__main__":
    while True:
        rest_id_input = input("Veuillez entrer l'ID de votre restaurant (ex: rest_01) : ")
        if db.restaurants.find_one({"id_restaurant": rest_id_input}):
            RESTAURANT_ID = rest_id_input
            break
        else:
            print("❌ ID de restaurant non valide.")

    nom_restaurant = db.restaurants.find_one({"id_restaurant": RESTAURANT_ID}).get('nom', RESTAURANT_ID)
    print(f"🍽️  Restaurant '{nom_restaurant}' ({RESTAURANT_ID}) ouvert et attend les commandes.")
    
    thread_ecoute = threading.Thread(target=ecouteur_restaurant, daemon=True)
    thread_ecoute.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n👋 Fermeture du restaurant {RESTAURANT_ID}.")
    finally:
        client.close()