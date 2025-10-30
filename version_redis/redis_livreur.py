import redis
import time
import json
import threading
import random

# Connexion à Redis
r = redis.Redis(decode_responses=True)
LIVREUR_ID = None
mission_en_cours = False
# NOUVELLE VARIABLE : pour suivre l'offre sur laquelle on a misé
bid_en_attente = None 

def ecouteur_livreur():
    """
    Écoute les offres de livraison générales et les notifications
    concernant ses missions assignées.
    """
    global mission_en_cours, bid_en_attente
    pubsub = r.pubsub()
    pubsub.subscribe(['offres_livraisons', 'notifications'])
    
    nom_livreur = r.hget(f"livreur:{LIVREUR_ID}", "nom")
    print(f"🚲 Livreur {nom_livreur} ({LIVREUR_ID}) est en service et attend des missions.")

    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            channel = message['channel']
            
            # --- Logique de réception d'une offre ---
            # On ne peut recevoir une offre que si on est ni en mission, ni en attente d'une réponse
            if (channel == 'offres_livraisons' 
                and not mission_en_cours 
                and not bid_en_attente):
                
                # Vérifier si la commande n'est pas déjà prise (double sécurité)
                if r.exists(f"commande_verrou:{data['commande_id']}"):
                    print(f"\n[LIVREUR] Offre pour {data['commande_id']} reçue, mais déjà verrouillée. On ignore.")
                    continue

                print("\n" + "="*30)
                print(f"[LIVREUR] Nouvelle offre de livraison !")
                print(f"  ID Commande: {data['commande_id']}")
                print(f"  De: {data['restaurant_adresse']}")
                print(f"  À: {data['client_adresse']}")
                print(f"  Rétribution: {data['retribution']}")
                
                reponse = input("Accepter cette mission ? (oui/non): ").lower()
                if reponse == 'oui':
                    # --- CORRECTION LOGIQUE ---
                    # 1. Tenter de "verrouiller" atomiquement l'offre
                    # SETNX = SET if Not eXists. Renvoie 1 (True) si la clé a été créée, 0 (False) si elle existait déjà.
                    # On met une expiration (EX 60) au cas où le manager plante.
                    a_reussi_le_lock = r.set(f"commande_verrou:{data['commande_id']}", LIVREUR_ID, nx=True, ex=60)

                    if a_reussi_le_lock:
                        # 2. On a le "lock" ! On est le premier (ou le seul) à avoir répondu.
                        # On se met en attente de la confirmation finale du manager.
                        bid_en_attente = data['commande_id'] 
                        print("[LIVREUR] Offre acceptée. Envoi de la réponse au manager...")
                        r.publish('reponses_livreurs', json.dumps({
                            "commande_id": data['commande_id'],
                            "livreur_id": LIVREUR_ID
                        }))
                    else:
                        # 3. On n'a pas eu le lock, un autre livreur a été plus rapide.
                        print("[LIVREUR] Trop tard ! Un autre livreur a déjà répondu.")
                        # On ne fait rien, on reste disponible pour la prochaine offre.

            # --- Logique de réception des notifications ---
            elif channel == 'notifications':
                type_notif = data.get('type')
                cmd_id_notif = data.get('commande_id')

                # CAS 1: C'EST POUR MOI ! J'ai gagné l'offre.
                if (type_notif == "LIVREUR_ASSIGNE" 
                    and data.get('livreur_id') == LIVREUR_ID):
                    
                    mission_en_cours = True # Je suis officiellement en mission
                    bid_en_attente = None # Je ne suis plus en attente
                    
                    print(f"\n[LIVREUR] Mission confirmée pour la commande {cmd_id_notif} !")
                    
                    # Simuler la livraison
                    print("[LIVREUR] Récupération de la commande...")
                    time.sleep(random.randint(3, 6))
                    print("[LIVREUR] En route vers l'adresse du client...")
                    time.sleep(random.randint(8, 15))
                    print(f"✅ [LIVREUR] Commande {cmd_id_notif} livrée !")
                    
                    notification_livraison = {
                        "type": "COMMANDE_LIVREE",
                        "commande_id": cmd_id_notif,
                        "message": f"Votre commande {cmd_id_notif} a été livrée. Bon appétit !"
                    }
                    r.publish('notifications', json.dumps(notification_livraison))
                    
                    mission_en_cours = False # Je suis de nouveau disponible
                    r.delete(f"commande_verrou:{cmd_id_notif}") # Nettoyer le verrou
                    print(f"\n🚲 Livreur {nom_livreur} de nouveau disponible.")

                # CAS 2: J'AI PERDU L'OFFRE (ou une offre à laquelle je n'ai pas participé a été prise)
                # Si la notif concerne la commande que j'attendais, mais qu'elle est pour qqn d'autre
                elif (type_notif == "LIVREUR_ASSIGNE" 
                      and cmd_id_notif == bid_en_attente 
                      and data.get('livreur_id') != LIVREUR_ID):
                    
                    print(f"\n[LIVREUR] La mission {cmd_id_notif} a été assignée à {data.get('livreur_id')}.")
                    bid_en_attente = None # Je redevient disponible pour d'autres offres

                # CAS 3: L'OFFRE A EXPIRÉ ou A ÉTÉ REJETÉE
                elif (type_notif in ["AUCUN_LIVREUR", "COMMANDE_REJETEE"] 
                      and cmd_id_notif == bid_en_attente):
                      
                    print(f"\n[LIVREUR] La mission {cmd_id_notif} a été annulée/rejetée.")
                    bid_en_attente = None # Je redeviens disponible
                    r.delete(f"commande_verrou:{cmd_id_notif}") # Nettoyer le verrou

if __name__ == "__main__":
    # Demander au livreur de s'identifier
    while True:
        livreur_id_input = input("Veuillez entrer votre ID de livreur (ex: livr_01) : ")
        if r.exists(f"livreur:{livreur_id_input}"):
            LIVREUR_ID = livreur_id_input
            break
        else:
            print("❌ ID de livreur non valide. Veuillez réessayer.")

    # Lancer l'écouteur dans un thread
    thread_ecoute = threading.Thread(target=ecouteur_livreur, daemon=True)
    thread_ecoute.start()
    
    try:
        # Garder le script principal en vie pour permettre les inputs
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n👋 Fin de service pour le livreur {LIVREUR_ID}.")