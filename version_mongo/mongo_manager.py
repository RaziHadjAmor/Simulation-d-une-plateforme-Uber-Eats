import threading
import time
from datetime import datetime
from pymongo import MongoClient

# Connexion
try:
    client = MongoClient("mongodb://localhost:27017/?replicaSet=rs0")
    db = client["ubereats_db"]
except Exception:
    print("❌ ERREUR: Connexion à MongoDB échouée.")
    exit()

def demarrer_timer_livraison(commande_id):
    """Démarre un minuteur de 60s pour trouver un livreur."""
    def verifier_timeout():
        time.sleep(60)
        
        # Utiliser find_one_and_update pour être atomique
        commande_annulee = db.commandes.find_one_and_update(
            {"commande_id": commande_id, "statut": "offre_disponible"}, # Ne s'applique que si elle est tjs en offre
            {"$set": {"statut": "annulee_timeout"}}
        )
        
        if commande_annulee: # Si on a bien annulé la commande
            print(f"\n[MANAGER] TIMEOUT: Aucun livreur n'a accepté {commande_id} à temps.")
            db.notifications.insert_one({
                "type": "AUCUN_LIVREUR", 
                "commande_id": commande_id, 
                "message": "Désolé, aucun livreur n'est disponible. Commande annulée."
            })
            
    threading.Thread(target=verifier_timeout, daemon=True).start()

def moderer_commande(commande_doc):
    """Affiche la commande et demande la modération."""
    commande_id = commande_doc['commande_id']
    print("\n" + "="*30)
    print(f"[MANAGER] MODÉRATION REQUISE pour {commande_id}")
    print(f"  - Client: {commande_doc.get('client_id', 'N/A')}")
    print(f"  - Adresse: {commande_doc.get('adresse_client', 'N/A')}")
    print(f"  - Restaurant: {commande_doc.get('restaurant_id', 'N/A')}")
    print(f"  - Total: {commande_doc.get('total_euros', 'N/A')} €")
    print("  - Contenu:")
    for item in commande_doc.get('plats_details', []):
        print(f"    - {item.get('quantite')}x {item.get('nom')} ({item.get('id_plat')})")
    print("="*30)
    
    decision = input(f"Accepter la commande {commande_id} ? (oui/non): ").lower()
    
    if decision == 'oui':
        db.commandes.update_one(
            {"commande_id": commande_id},
            {"$set": {"statut": "accepted_en_preparation"}}
        )
        print(f"[MANAGER] Commande {commande_id} validée -> Restaurant.")
    else:
        db.commandes.update_one(
            {"commande_id": commande_id},
            {"$set": {"statut": "rejetee_manager"}}
        )
        # --- CORRECTION BUG 2 : Envoyer une notification de rejet ---
        db.notifications.insert_one({
            "type": "COMMANDE_REJETEE", 
            "commande_id": commande_id, 
            "message": "Votre commande a été rejetée par le manager."
        })
        print(f"[MANAGER] Commande {commande_id} rejetée.")

def ecouteur_nouvelles_commandes():
    """Surveille la collection 'commandes' pour les NOUVELLES commandes (operationType 'insert')."""
    pipeline = [{
        '$match': {
            'operationType': 'insert',
            'fullDocument.statut': 'pending_moderation'
        }
    }]
    try:
        with db.commandes.watch(pipeline) as stream:
            for change in stream:
                commande = change['fullDocument']
                threading.Thread(target=moderer_commande, args=(commande,)).start()
    except Exception as e:
        print(f"[Écouteur NOUVEAU] Erreur : {e}")

def ecouteur_commandes_pretes():
    """Surveille la collection 'commandes' pour les commandes PRÊTES."""
    pipeline = [{
        '$match': {
            'operationType': 'update',
            'updateDescription.updatedFields.statut': 'ready_awaiting_livreur'
        }
    }]
    try:
        # --- CORRECTION BUG 1 : Ajouter full_document='updateLookup' ---
        with db.commandes.watch(pipeline, full_document='updateLookup') as stream:
            for change in stream:
                commande_doc = change['fullDocument']
                commande_id = commande_doc['commande_id']
                print(f"\n[MANAGER] Commande {commande_id} prête. Envoi de l'offre aux livreurs...")
                
                resto = db.restaurants.find_one({"id_restaurant": commande_doc.get("restaurant_id")})
                adresse_resto = resto.get("adresse", "Adresse inconnue") if resto else "Adresse inconnue"
                
                offre = {
                    "commande_id": commande_id,
                    "restaurant_adresse": adresse_resto,
                    "client_adresse": commande_doc.get('adresse_client', 'N/A'),
                    "retribution": "8€" # Exemple
                }
                # Mettre à jour la commande avec l'offre (ce que le livreur écoutera)
                db.commandes.update_one(
                    {"commande_id": commande_id},
                    {"$set": {"statut": "offre_disponible", "offre_livraison": offre}}
                )
                demarrer_timer_livraison(commande_id)
    except Exception as e:
        print(f"[Écouteur PRÊT] Erreur : {e}")

def ecouteur_commandes_livrees():
    """
    (NOUVEAU) Similaire au thread 'attendre_livraison_et_sauvegarder' de Redis.
    Écoute la collection 'notifications' pour savoir quand une commande est livrée.
    """
    pipeline = [{
        '$match': {
            'operationType': 'insert',
            'fullDocument.type': 'COMMANDE_LIVREE'
        }
    }]
    try:
        # On ne veut voir que les nouveaux événements
        start_at = db.notifications.watch(pipeline).next()['_id']
        with db.notifications.watch(pipeline, resume_after=start_at) as stream:
            for change in stream:
                notification = change['fullDocument']
                commande_id = notification.get('commande_id')
                print(f"\n[MANAGER-INFO] La commande {commande_id} a été livrée avec succès.")
                # Ici, on pourrait appeler une fonction d'archivage ou de compta
                # Pour ce POC, on met à jour le statut final dans la commande
                db.commandes.update_one(
                    {"commande_id": commande_id},
                    {"$set": {"statut": "livree", "date_livraison": datetime.now().isoformat()}}
                )
    except Exception as e:
        print(f"[Écouteur LIVRÉ] Erreur : {e}")


def afficher_historique():
    """Affiche l'historique des commandes terminées."""
    print("\n" + "="*50)
    print("📜 HISTORIQUE DES COMMANDES (du plus récent au plus ancien) 📜")
    print("="*50)
    
    historique = db.commandes.find({
        "statut": {"$in": ["livree", "rejetee_manager", "annulee_timeout"]}
    }).sort("date_creation", -1)
    
    count = 0
    for cmd in historique:
        count += 1
        print(f"\n--- Commande: {cmd.get('commande_id', 'N/A')} ---")
        print(f"  Date: {cmd.get('date_creation', 'N/A')}")
        print(f"  Statut Final: {cmd.get('statut', 'N/A')}")
        print(f"  Client: {cmd.get('client_id', 'N/A')}")
        print(f"  Adresse: {cmd.get('adresse_client', 'N/A')}")
        print(f"  Livreur: {cmd.get('id_livreur', 'N/A')}")
        print(f"  Total: {cmd.get('total_euros', 'N/A')} €")
    
    if count == 0:
        print("Aucune commande dans l'historique.")
    print("="*50)

if __name__ == "__main__":
    print("🤖 Manager en ligne. Surveillance des commandes en cours...")
    print("Tapez 'historique' pour voir les commandes passées, 'quitter' pour arrêter.")
    
    # Démarrer les TROIS écouteurs dans des threads
    t_nouveau = threading.Thread(target=ecouteur_nouvelles_commandes, daemon=True)
    t_pretes = threading.Thread(target=ecouteur_commandes_pretes, daemon=True)
    t_livrees = threading.Thread(target=ecouteur_commandes_livrees, daemon=True) # Nouveau thread
    
    t_nouveau.start()
    t_pretes.start()
    t_livrees.start()
    
    try:
        while True:
            commande_manager = input().strip().lower()
            if commande_manager == 'historique':
                afficher_historique()
            elif commande_manager == 'quitter':
                break
    except KeyboardInterrupt:
        print("\n👋 Arrêt manuel du Manager.")
    finally:
        print("Fin du programme Manager.")
        client.close()