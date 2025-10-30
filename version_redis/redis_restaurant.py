import redis
import time
import json
import threading
import random

# Connexion à Redis
r = redis.Redis(decode_responses=True)
RESTAURANT_ID = None

def ecouteur_restaurant():
    """
    Écoute les commandes envoyées par le manager, simule leur préparation,
    et notifie quand elles sont prêtes.
    """
    pubsub = r.pubsub()
    pubsub.subscribe('commandes_restaurants')
    
    # Récupérer le nom du restaurant pour un affichage plus convivial
    nom_restaurant = r.hget(f"restaurant:{RESTAURANT_ID}", "nom")
    print(f"🍽️  Restaurant '{nom_restaurant}' ({RESTAURANT_ID}) est ouvert et attend les commandes.")

    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            
            # Le restaurant ne réagit que si la commande est pour lui
            if data.get('restaurant_id') == RESTAURANT_ID:
                commande_id = data['commande_id']
                print(f"\n[RESTAURANT] Nouvelle commande reçue : {commande_id}")
                
                # Afficher le détail des plats commandés
                print("  - Contenu à préparer :")
                for item in data['plats_details']:
                    plat_id = item['id_plat']
                    quantite = item['quantite']
                    nom_plat = r.hget(f"plat:{plat_id}", "nom") or "Plat inconnu"
                    print(f"    - {quantite}x {nom_plat}")

                # Simuler le temps de préparation
                temps_preparation = random.randint(5, 12)
                print(f"[RESTAURANT] Préparation en cours... (environ {temps_preparation} secondes)")
                time.sleep(temps_preparation)
                
                print(f"✅ [RESTAURANT] La commande {commande_id} est prête pour la livraison !")
                
                # Notifier le manager que la commande est prête
                r.publish('commandes_pretes', json.dumps({"commande_id": commande_id}))

if __name__ == "__main__":
    # Demander au restaurateur de s'identifier
    while True:
        rest_id_input = input("Veuillez entrer l'ID de votre restaurant (ex: rest_01) : ")
        # Vérifier si l'ID du restaurant existe dans la base de données
        if r.exists(f"restaurant:{rest_id_input}"):
            RESTAURANT_ID = rest_id_input
            break
        else:
            print("❌ ID de restaurant non valide. Veuillez réessayer.")

    # Lancer l'écouteur dans un thread pour ne pas bloquer
    thread_ecoute = threading.Thread(target=ecouteur_restaurant, daemon=True)
    thread_ecoute.start()
    
    try:
        # Garder le script principal en vie
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n👋 Fermeture du restaurant {RESTAURANT_ID}.")
