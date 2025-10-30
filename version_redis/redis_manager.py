import redis
import time
import json
import threading
from datetime import datetime

# Connexion à Redis
r = redis.Redis(decode_responses=True)
commandes_en_attente = {} # Dictionnaire pour le suivi des commandes actives

# --- Fonctions existantes (enregistrer, timer, modérer) ---
def enregistrer_commande_finale(commande_id, statut_final):
    """Enregistre l'état final d'une commande dans la base de données Redis."""
    if commande_id in commandes_en_attente:
        commande_data = commandes_en_attente[commande_id]
        
        commande_a_sauvegarder = {
            "id_client": commande_data.get("client_id", "N/A"),
            "id_restaurant": commande_data.get("restaurant_id", "N/A"),
            "date": datetime.now().isoformat(),
            "statut_final": statut_final,
            "adresse_livraison": commande_data.get("adresse_client", "N/A"),
            "plats_details": json.dumps(commande_data.get("plats_details", [])), 
            "id_livreur": commande_data.get("livreur_assigne", "N/A")
        }
        
        r.hset(f"commande:{commande_id}", mapping=commande_a_sauvegarder)
        print(f"\n[MANAGER-BDD] Commande {commande_id} enregistrée: '{statut_final}'.")
        
        del commandes_en_attente[commande_id]

def demarrer_timer_livraison(commande_id):
    """Démarre un minuteur de 60s pour trouver un livreur."""
    def verifier_timeout():
        time.sleep(60) # Délai d'attente
        if commande_id in commandes_en_attente and "livreur_assigne" not in commandes_en_attente[commande_id]:
            print(f"\n[MANAGER] TIMEOUT: Aucun livreur n'a accepté {commande_id} à temps.")
            notification_echec = {"type": "AUCUN_LIVREUR", "commande_id": commande_id, "message": "Désolé, aucun livreur n'est disponible. Commande annulée."}
            r.publish('notifications', json.dumps(notification_echec))
            enregistrer_commande_finale(commande_id, "annulee_timeout")
    threading.Thread(target=verifier_timeout, daemon=True).start()

def moderer_commande(data):
    """Affiche la commande au manager et attend sa décision (oui/non)."""
    commande_id = data['commande_id']
    print("\n" + "="*30)
    print(f"[MANAGER] MODÉRATION REQUISE pour {commande_id}")
    print(f"  - Client: {data.get('client_id', 'Inconnu')}")
    
    print("  - Contenu de la commande :")
    try:
        for item in data.get('plats_details', []):
            plat_id = item.get('id_plat', '?')
            quantite = item.get('quantite', '?')
            nom_plat = r.hget(f"plat:{plat_id}", "nom") or "Plat inconnu"
            print(f"    - {quantite}x {nom_plat} ({plat_id})")
    except Exception as e:
        print(f"    - ERREUR lors de l'affichage des plats: {e}")
    
    print("="*30)
    
    decision = ""
    while decision not in ["oui", "non"]:
        decision = input(f"Accepter la commande {commande_id} ? (oui/non): ").lower()

    if decision == "oui":
        print(f"[MANAGER] Commande {commande_id} validée -> Restaurant.")
        r.publish('commandes_restaurants', json.dumps(data))
    else:
        print(f"[MANAGER] Commande {commande_id} rejetée.")
        notification_rejet = {"type": "COMMANDE_REJETEE", "commande_id": commande_id, "message": "Votre commande a été rejetée par le manager."}
        r.publish('notifications', json.dumps(notification_rejet))
        enregistrer_commande_finale(commande_id, "rejetee_manager")

# --- Nouvelle Fonction pour l'Historique ---
def afficher_historique():
    """Récupère et affiche l'historique de toutes les commandes terminées."""
    print("\n" + "="*50)
    print("📜 HISTORIQUE DES COMMANDES 📜")
    print("="*50)
    
    # Utiliser KEYS (simple pour POC) ou SCAN (mieux pour production)
    commandes_keys = r.keys("commande:cmd_*") 
    
    if not commandes_keys:
        print("Aucune commande dans l'historique pour le moment.")
        return

    # Trier les clés pour un affichage chronologique approximatif (basé sur l'ID)
    commandes_keys.sort() 
    
    for key in commandes_keys:
        details = r.hgetall(key)
        cmd_id = key.split(":")[1]
        
        print(f"\n--- Commande: {cmd_id} ---")
        print(f"  Client: {details.get('id_client', 'N/A')}")
        print(f"  Restaurant: {details.get('id_restaurant', 'N/A')}")
        print(f"  Date: {details.get('date', 'N/A')}")
        print(f"  Statut Final: {details.get('statut_final', 'N/A')}")
        print(f"  Livreur: {details.get('id_livreur', 'N/A')}")
        # Afficher les plats (optionnel, peut être long)
        try:
            plats = json.loads(details.get('plats_details', '[]'))
            print("  Contenu:")
            for item in plats:
                 print(f"    - {item.get('quantite')}x {item.get('id_plat')}")
        except json.JSONDecodeError:
            print("  Contenu: Erreur de format")
            
    print("="*50)
    print(f"Commandes Redis utilisées : KEYS commande:cmd_*, HGETALL commande:<id>")

# --- Thread d'Écoute (inchangé) ---
def ecouteur_commandes():
    """Thread qui écoute les messages Pub/Sub."""
    pubsub = r.pubsub()
    pubsub.subscribe(['commandes_clients', 'commandes_pretes', 'reponses_livreurs'])
    print("🤖 Manager en ligne. Tapez 'historique' pour voir les commandes passées, 'quitter' pour arrêter.")

    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel']
            data = json.loads(message['data'])

            if channel == 'commandes_clients':
                commandes_en_attente[data['commande_id']] = data
                threading.Thread(target=moderer_commande, args=(data,)).start()

            elif channel == 'commandes_pretes':
                commande_id = data['commande_id']
                if commande_id in commandes_en_attente:
                    print(f"\n[MANAGER] {commande_id} prête. Recherche livreur...")
                    # Ici la logique de recherche intelligente ou simple
                    offre = {
                        "commande_id": commande_id,
                        "restaurant_adresse": r.hget(f"restaurant:{commandes_en_attente[commande_id]['restaurant_id']}", "adresse"),
                        "client_adresse": commandes_en_attente[commande_id]['adresse_client'],
                        "retribution": "8€" # Exemple
                    }
                    r.publish('offres_livraisons', json.dumps(offre))
                    demarrer_timer_livraison(commande_id)
            
            elif channel == 'reponses_livreurs':
                commande_id = data['commande_id']
                livreur_id = data['livreur_id']
                if commande_id in commandes_en_attente and "livreur_assigne" not in commandes_en_attente[commande_id]:
                    print(f"\n[MANAGER] {livreur_id} accepte {commande_id}.")
                    commandes_en_attente[commande_id]["livreur_assigne"] = livreur_id
                    
                    notification = {
                        "type": "LIVREUR_ASSIGNE", "commande_id": commande_id,
                        "livreur_id": livreur_id,
                        "message": f"Livreur {livreur_id} assigné."
                    }
                    r.publish('notifications', json.dumps(notification))

                    # Écoute pour sauvegarder après livraison
                    def attendre_livraison_et_sauvegarder(cmd_id):
                        ps = r.pubsub(ignore_subscribe_messages=True)
                        ps.subscribe("notifications")
                        for msg in ps.listen():
                            notif_data = json.loads(msg['data'])
                            if notif_data.get("type") == "COMMANDE_LIVREE" and notif_data.get("commande_id") == cmd_id:
                                enregistrer_commande_finale(cmd_id, "livree")
                                ps.unsubscribe()
                                break
                    
                    threading.Thread(target=attendre_livraison_et_sauvegarder, args=(commande_id,), daemon=True).start()

# --- Boucle Principale pour l'Interaction Manager ---
if __name__ == "__main__":
    # Démarrer l'écouteur en arrière-plan
    thread_ecoute = threading.Thread(target=ecouteur_commandes, daemon=True)
    thread_ecoute.start()
    
    try:
        # Boucle principale pour les commandes manuelles du manager
        while True:
            commande_manager = input().strip().lower()
            if commande_manager == 'historique':
                afficher_historique()
            elif commande_manager == 'quitter':
                break
            # On pourrait ajouter d'autres commandes ici (ex: 'statistiques')
            
    except KeyboardInterrupt:
        print("\n👋 Arrêt manuel du Manager.")
    finally:
        print("Fin du programme Manager.")