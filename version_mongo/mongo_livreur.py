import threading
import time
import random
from pymongo import MongoClient, ReturnDocument

# Connexion
try:
    client = MongoClient("mongodb://localhost:27017/?replicaSet=rs0")
    db = client["ubereats_db"]
except Exception:
    print("❌ ERREUR: Connexion à MongoDB échouée.")
    exit()

LIVREUR_ID = None
mission_en_cours = False
bid_en_attente = None # ID de la commande sur laquelle on mise

def accepter_mission(commande_doc):
    """Logique d'acceptation de la mission."""
    global mission_en_cours, bid_en_attente
    
    commande_id = commande_doc['commande_id']
    offre = commande_doc['offre_livraison']
    
    print("\n" + "="*30)
    print(f"[LIVREUR] Nouvelle offre de livraison !")
    print(f"  ID Commande: {commande_id}")
    print(f"  De: {offre.get('restaurant_adresse', 'N/A')}")
    print(f"  À: {offre.get('client_adresse', 'N/A')}")
    print(f"  Rétribution: {offre.get('retribution', 'N/A')}")
    
    reponse = input("Accepter cette mission ? (oui/non): ").lower()
    
    if reponse == 'oui':
        bid_en_attente = commande_id
        
        # --- Remplacement de SETNX ---
        try:
            resultat = db.commandes.find_one_and_update(
                {
                    "commande_id": commande_id, 
                    "statut": "offre_disponible"
                },
                {
                    "$set": {
                        "statut": "assigned_delivering",
                        "id_livreur": LIVREUR_ID
                    }
                },
                return_document=ReturnDocument.AFTER 
            )
            
            if resultat:
                # --- SUCCÈS ! ON A EU LA COURSE ---
                mission_en_cours = True
                bid_en_attente = None
                print(f"\n[LIVREUR] Mission {commande_id} confirmée pour moi !")
                
                # --- NOUVEAU SUIVI ÉTAPE 1 : ASSIGNÉ ---
                db.notifications.insert_one({
                    "type": "LIVREUR_ASSIGNE", "commande_id": commande_id,
                    "livreur_id": LIVREUR_ID, "message": f"Le livreur {LIVREUR_ID} a accepté votre commande."
                })
                
                # Simuler la récupération
                print("[LIVREUR] Récupération de la commande...")
                time.sleep(random.randint(3, 6))
                
                # --- NOUVEAU SUIVI ÉTAPE 2 : RÉCUPÉRÉ ---
                print("[LIVREUR] Commande récupérée au restaurant.")
                db.notifications.insert_one({
                    "type": "COMMANDE_RECUPEREE", "commande_id": commande_id,
                    "message": "Votre commande a été récupérée au restaurant."
                })

                # Simuler la livraison
                print("[LIVREUR] En route vers l'adresse du client...")
                time.sleep(random.randint(8, 15))
                
                # Mettre à jour le statut final
                db.commandes.update_one(
                    {"commande_id": commande_id},
                    {"$set": {"statut": "livree"}}
                )
                print(f"✅ [LIVREUR] Commande {commande_id} livrée !")
                
                # --- NOUVEAU SUIVI ÉTAPE 3 : LIVRÉ ---
                db.notifications.insert_one({
                    "type": "COMMANDE_LIVREE",
                    "commande_id": commande_id,
                    "message": f"Votre commande {commande_id} a été livrée. Bon appétit !"
                })
                
                mission_en_cours = False
                print(f"\n🚲 Livreur {LIVREUR_ID} de nouveau disponible.")
                
            else:
                # --- ECHEC ! TROP TARD ---
                print("[LIVREUR] Trop tard ! Un autre livreur a déjà pris cette mission.")
                bid_en_attente = None
        
        except Exception as e:
            print(f"Erreur lors de l'acceptation : {e}")
            bid_en_attente = None
    else:
        print("[LIVREUR] Offre refusée.")


def ecouteur_livreur():
    """Surveille les nouvelles offres de livraison."""
    global mission_en_cours, bid_en_attente
    
    # On surveille les mises à jour qui changent le statut en 'offre_disponible'
    pipeline = [{
        '$match': {
            'operationType': 'update',
            'updateDescription.updatedFields.statut': 'offre_disponible'
        }
    }]
    
    try:
        with db.commandes.watch(pipeline, full_document='updateLookup') as stream:
            for change in stream:
                if not mission_en_cours and not bid_en_attente:
                    commande = change['fullDocument']
                    threading.Thread(target=accepter_mission, args=(commande,)).start()
                else:
                    print("[LIVREUR] Nouvelle offre reçue, mais je suis occupé. On ignore.")
                    
    except Exception as e:
        print(f"[Écouteur Livreur] Erreur : {e}")

if __name__ == "__main__":
    while True:
        livreur_id_input = input("Veuillez entrer votre ID de livreur (ex: livr_01) : ")
        if db.livreurs.find_one({"id_livreur": livreur_id_input}):
            LIVREUR_ID = livreur_id_input
            break
        else:
            print("❌ ID de livreur non valide.")

    nom_livreur = db.livreurs.find_one({"id_livreur": LIVREUR_ID}).get('nom', LIVREUR_ID)
    print(f"🚲 Livreur {nom_livreur} ({LIVREUR_ID}) est en service et attend des missions.")
    
    thread_ecoute = threading.Thread(target=ecouteur_livreur, daemon=True)
    thread_ecoute.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n👋 Fin de service pour le livreur {LIVREUR_ID}.")
    finally:
        client.close()