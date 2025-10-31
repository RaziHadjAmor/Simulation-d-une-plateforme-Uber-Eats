import redis
import time
import json
import threading
from datetime import datetime

# Connexion à Redis
r = redis.Redis(decode_responses=True)
commandes_en_attente = {} # Dictionnaire pour le suivi des commandes actives

# --- Fonctions (enregistrer, timer, modérer) ---

def enregistrer_commande_finale(commande_id, statut_final):
    """Enregistre l'état final d'une commande dans la base de données Redis."""
    if commande_id in commandes_en_attente:
        commande_data = commandes_en_attente[commande_id]
        
        # Pré-calculer le nom du restaurant pour le stockage
        id_resto_sauvegarde = commande_data.get('restaurant_id', 'N/A')
        nom_resto_sauvegarde = r.hget(f"restaurant:{id_resto_sauvegarde}", "nom") or "Restaurant inconnu"
        
        commande_a_sauvegarder = {
            "date": datetime.now().isoformat(),
            "id_client": commande_data.get("client_id", "N/A"),
            "id_restaurant": id_resto_sauvegarde, 
            "nom_restaurant": nom_resto_sauvegarde,
            "statut_final": statut_final,
            "adresse_livraison": commande_data.get("adresse_client", "N/A"),
            "plats_details": json.dumps(commande_data.get("plats_details", [])), 
            "id_livreur": commande_data.get("livreur_assigne", "N/A"),
            "total_euros": commande_data.get("total_euros", "0.00") 
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
    print(f"  - Adresse Client: {data.get('adresse_client', 'Adresse inconnue')}")
    
    # 1. Pré-calculer les valeurs compliquées
    id_resto = data.get('restaurant_id', 'Inconnu')
    nom_resto = r.hget(f"restaurant:{id_resto}", "nom") or "Restaurant inconnu"
    
    # 2. Utiliser les variables simples dans la f-string
    print(f"  - Restaurant: {nom_resto} ({id_resto})")
    
    print("  - Contenu de la commande :")
    try:
        for item in data.get('plats_details', []):
            plat_id = item.get('id_plat', '?')
            quantite = item.get('quantite', '?')
            nom_plat = r.hget(f"plat:{plat_id}", "nom") or "Plat inconnu"
            print(f"    - {quantite}x {nom_plat} ({plat_id})")
    except Exception as e:
        print(f"    - ERREUR lors de l'affichage des plats: {e}")

    print(f"  - Total à payer: {data.get('total_euros', 'N/A')} €")
    
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

# --- Fonction d'Historique ---
def afficher_historique():
    """Récupère, trie par date et affiche l'historique de toutes les commandes terminées."""
    print("\n" + "="*50)
    print("📜 HISTORIQUE DES COMMANDES (du plus récent au plus ancien) 📜")
    print("="*50)
    
    commandes_keys = r.keys("commande:cmd_*") 
    
    if not commandes_keys:
        print("Aucune commande dans l'historique pour le moment.")
        return

    # 1. Récupérer toutes les commandes dans une liste
    all_commandes = []
    for key in commandes_keys:
        details = r.hgetall(key)
        details['id'] = key.split(":")[1] # Garder l'ID
        all_commandes.append(details)
    
    # 2. Trier la liste de dictionnaires par la clé 'date', en ordre décroissant (reverse=True)
    try:
        sorted_commandes = sorted(all_commandes, key=lambda cmd: cmd.get('date', '1970-01-01T00:00:00'), reverse=True)
    except Exception as e:
        print(f"Erreur lors du tri des dates : {e}. Affichage non trié.")
        sorted_commandes = all_commandes

    # 3. Afficher la liste triée avec les détails enrichis
    for details in sorted_commandes:
        cmd_id = details.get('id', 'N/A')
        id_resto = details.get('id_restaurant', 'N/A')
        
        # Utiliser le nom du restaurant déjà sauvegardé
        nom_resto = details.get('nom_restaurant', r.hget(f"restaurant:{id_resto}", "nom") or "Restaurant inconnu")
        
        print(f"\n--- Commande: {cmd_id} ---")
        print(f"  Date: {details.get('date', 'N/A')}")
        print(f"  Statut Final: {details.get('statut_final', 'N/A')}")
        print(f"  Client: {details.get('id_client', 'N/A')}")
        print(f"  Adresse Livraison: {details.get('adresse_livraison', 'N/A')}")
        print(f"  Restaurant: {nom_resto} ({id_resto})")
        print(f"  Livreur: {details.get('id_livreur', 'N/A')}")
        print(f"  Total Payé: {details.get('total_euros', 'N/A')} €")
        
        try:
            plats = json.loads(details.get('plats_details', '[]'))
            print("  Contenu:")
            for item in plats:
                plat_id = item.get('id_plat', '?')
                quantite = item.get('quantite', '?')
                # Récupérer le nom du plat
                nom_plat = r.hget(f"plat:{plat_id}", "nom") or plat_id
                print(f"    - {quantite}x {nom_plat} ({plat_id})")
        except json.JSONDecodeError:
            print("  Contenu: Erreur de format")
            
    print("="*50)
    print(f"Commandes Redis utilisées : KEYS, HGETALL, HGET")

# --- Thread d'Écoute  ---
def ecouteur_commandes():
    """Thread qui écoute les messages Pub/Sub."""
    pubsub = r.pubsub()
    pubsub.subscribe(['commandes_clients', 'commandes_pretes', 'reponses_livreurs'])
    print("🤖 Manager en ligne. Tapez 'historique' pour voir les commandes passées, 'quitter' pour arrêter.")
    print("(Note : Lorsqu'une commande arrive, vous serez invité à la modérer en appuyant sur Entrée.)")

    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel']
            try:
                data = json.loads(message['data'])
            except json.JSONDecodeError:
                print(f"[MANAGER] Erreur: Message non-JSON reçu sur {channel}")
                continue

            if channel == 'commandes_clients':
                commandes_en_attente[data['commande_id']] = data
                threading.Thread(target=moderer_commande, args=(data,)).start()

            elif channel == 'commandes_pretes':
                commande_id = data['commande_id']
                if commande_id in commandes_en_attente:
                    print(f"\n[MANAGER] {commande_id} prête. Recherche livreur...")
                    
                    id_resto = commandes_en_attente[commande_id].get('restaurant_id', 'N/A')
                    adresse_resto = r.hget(f"restaurant:{id_resto}", "adresse") or "Adresse inconnue"
                    
                    offre = {
                        "commande_id": commande_id,
                        "restaurant_adresse": adresse_resto,
                        "client_adresse": commandes_en_attente[commande_id].get('adresse_client', 'N/A'),
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
                        r_thread = redis.Redis(decode_responses=True)
                        ps = r_thread.pubsub(ignore_subscribe_messages=True)
                        ps.subscribe("notifications")
                        for msg in ps.listen():
                            try:
                                notif_data = json.loads(msg['data'])
                                if notif_data.get("type") == "COMMANDE_LIVREE" and notif_data.get("commande_id") == cmd_id:
                                    enregistrer_commande_finale(cmd_id, "livree")
                                    ps.unsubscribe()
                                    break
                            except json.JSONDecodeError:
                                print(f"[Thread Sauvegarde] Erreur décodage message: {msg.get('data')}")
                    
                    threading.Thread(target=attendre_livraison_et_sauvegarder, args=(commande_id,), daemon=True).start()

# --- Boucle Principale pour l'Interaction Manager ---
if __name__ == "__main__":
    thread_ecoute = threading.Thread(target=ecouteur_commandes, daemon=True)
    thread_ecoute.start()
    
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