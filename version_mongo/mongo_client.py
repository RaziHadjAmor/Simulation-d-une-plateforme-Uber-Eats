import uuid
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

CLIENT_ID = f"client_{uuid.uuid4().hex[:4]}"
COMMANDE_ID = f"cmd_{uuid.uuid4().hex[:6]}"
processus_termine = threading.Event()

def ecouteur_client(db_notifications_collection, commande_id):
    """
    Écoute les NOUVELLES insertions dans la collection 'notifications'
    qui correspondent à notre ID de commande.
    """
    print("-> Thread d'écoute démarré. En attente de notifications...")
    
    pipeline = [{
        '$match': {
            'operationType': 'insert',
            'fullDocument.commande_id': commande_id
        }
    }]
    
    try:
        # Nous commençons à écouter juste avant de passer la commande.
        # Nous ne voulons que les événements futurs.
        start_at = db_notifications_collection.watch(pipeline).next()['_id']
        
        with db_notifications_collection.watch(pipeline, resume_after=start_at) as stream:
            for change in stream:
                if processus_termine.is_set():
                    break
                    
                notification = change['fullDocument']
                type_notif = notification.get('type', 'N/A')
                message = notification.get('message', 'Message vide')
                
                print(f"\n🔔 [NOTIFICATION CLIENT] : {message}") # Affichage de tous les messages

                # Gérer la fin du processus
                if type_notif in ["COMMANDE_LIVREE", "COMMANDE_REJETEE", "AUCUN_LIVREUR"]:
                    print("-> Fin du processus de commande. Vous pouvez quitter avec Ctrl+C.")
                    processus_termine.set()

    except Exception as e:
        if not processus_termine.is_set():
            print(f"Erreur dans l'écouteur : {e}")

# ... (Les fonctions charger_et_afficher_restaurants, afficher_menu_restaurant, 
# rechercher_par_nom_exact, et rechercher_par_prefixe restent INCHANGÉES) ...

def charger_et_afficher_restaurants():
    """Récupère les restaurants depuis MongoDB."""
    print("="*30)
    print("🍽️ RESTAURANTS DISPONIBLES 🍽️")
    print("="*30)
    try:
        restaurants = list(db.restaurants.find({}, {"nom": 1, "id_restaurant": 1, "_id": 0}).sort("nom", 1))
        if not restaurants:
            print("Aucun restaurant trouvé. Avez-vous lancé 'json_to_mongo.py' ?")
            return None
        for resto in restaurants:
            print(f"- {resto['nom']} ({resto['id_restaurant']})")
        print("="*50)
        return {r['id_restaurant']: r for r in restaurants}
    except Exception as e:
        print(f"Erreur lors du chargement des restaurants : {e}")
        return None

def afficher_menu_restaurant(rest_id):
    """Affiche le menu d'un restaurant (stocké en documents imbriqués)."""
    resto = db.restaurants.find_one({"id_restaurant": rest_id})
    if not resto:
        print("Restaurant non trouvé.")
        return None
        
    print(f"\n--- Menu de {resto['nom']} ({rest_id}) ---")
    print(f"    Adresse: {resto.get('adresse', 'N/A')}")
    
    if not resto.get("menu"):
        print("  -> Ce restaurant n'a pas de plats enregistrés.")
        return None

    for plat in resto["menu"]:
        print(f"  - [{plat['id_plat']}] {plat.get('nom', 'N/A')} - {plat.get('prix', '?.??')}€")
        print(f"      ↳ {plat.get('description', 'Aucune description')}")
    return resto["menu"]

def rechercher_par_nom_exact(nom):
    """Remplace l'ABR."""
    print(f"\nRecherche exacte pour '{nom}':")
    resultat = db.restaurants.find_one({"nom": {"$regex": f"^{nom}$", "$options": "i"}})
    if resultat:
        print(f"  ✅ Restaurant trouvé : {resultat['nom']} (ID: {resultat['id_restaurant']})")
    else:
        print("  ❌ Restaurant non trouvé.")

def rechercher_par_prefixe(prefixe):
    """Remplace le Trie."""
    print(f"\nRecherche avancée pour '{prefixe}':")
    resultats = list(db.restaurants.find(
        {"nom": {"$regex": f"^{prefixe}", "$options": "i"}},
        {"nom": 1, "id_restaurant": 1, "_id": 0}
    ).sort("nom", 1))
    
    if not resultats:
        print(f"  ❌ Aucun restaurant trouvé commençant par '{prefixe}'.")
    else:
        print(f"\n✅ Restaurants trouvés pour '{prefixe}' :")
        for resto in resultats:
            print(f"   - {resto['nom']} (ID: {resto['id_restaurant']})")


if __name__ == "__main__":
    print(f"👤 Bienvenue Client {CLIENT_ID}")
    
    restaurants = charger_et_afficher_restaurants()
    if not restaurants:
        exit()
        
    main_loop_active = True
    try:
        while main_loop_active:
            action = input("\nQue souhaitez-vous faire ? ('commander', 'rechercher' [nom exact], 'prefixe' [recherche avancée], 'quitter'): ").lower()

            if action == 'rechercher':
                nom_recherche = input("Entrez le nom EXACT du restaurant : ").lower()
                rechercher_par_nom_exact(nom_recherche)
                continue
            elif action == 'prefixe':
                prefixe = input("Entrez le DÉBUT du nom du restaurant : ").lower()
                if prefixe: rechercher_par_prefixe(prefixe)
                else: print("Veuillez entrer au moins un caractère.")
                continue
            elif action == 'quitter':
                main_loop_active = False
                break
            elif action == 'commander':
                restaurant_choisi_id = ""
                while restaurant_choisi_id not in restaurants:
                    restaurant_choisi_id = input("Veuillez entrer l'ID du restaurant pour commander : ")
                
                menu_disponible = afficher_menu_restaurant(restaurant_choisi_id)
                if not menu_disponible:
                    print("Ce restaurant n'a pas de menu, impossible de commander.")
                    continue
                
                menu_map = {p['id_plat']: p for p in menu_disponible}
                plats_commande = []
                while True:
                    plat_choisi_id = input("Entrez l'ID d'un plat à ajouter (ou 'fin' pour terminer) : ")
                    if plat_choisi_id.lower() == 'fin':
                        if not plats_commande:
                            print("Panier vide. Veuillez ajouter un plat.")
                            continue
                        break 
                    
                    if plat_choisi_id in menu_map:
                        try:
                            quantite_str = input(f"Quantité pour {plat_choisi_id} ? ")
                            quantite = int(quantite_str) 
                            if quantite > 0:
                                plats_commande.append({"id_plat": plat_choisi_id, "quantite": quantite, "nom": menu_map[plat_choisi_id]['nom'], "prix_unitaire": menu_map[plat_choisi_id]['prix']})
                                print(f"Plat {plat_choisi_id} ajouté.")
                            else:
                                print("❌ La quantité doit être supérieure à zéro.")
                        except ValueError:
                            print("❌ Quantité non valide. Veuillez entrer un nombre entier.")
                    else:
                        print("❌ Erreur: ID de plat invalide.")

                total_commande = 0.0
                print("\n--- Récapitulatif de votre commande ---")
                for item in plats_commande:
                    prix_unitaire = float(item.get('prix_unitaire', 0))
                    total_item = prix_unitaire * item['quantite']
                    total_commande += total_item
                    print(f"  - {item['quantite']}x {item['nom']} ({prix_unitaire:.2f}€/unité) = {total_item:.2f}€")
                print("-" * 40)
                print(f"💰 TOTAL DE LA COMMANDE : {total_commande:.2f} €")
                print("-" * 40)

                adresse_livraison = input("Votre adresse de livraison ? : ")
                
                commande_doc = {
                    "commande_id": COMMANDE_ID,
                    "client_id": CLIENT_ID,
                    "restaurant_id": restaurant_choisi_id,
                    "adresse_client": adresse_livraison,
                    "plats_details": plats_commande,
                    "total_euros": f"{total_commande:.2f}",
                    "statut": "pending_moderation",
                    "date_creation": datetime.now().isoformat()
                }
                
                # Démarrer le thread d'écoute AVANT d'insérer la commande
                # Il écoute la collection 'notifications'
                thread_ecoute = threading.Thread(target=ecouteur_client, args=(db.notifications, COMMANDE_ID), daemon=True)
                thread_ecoute.start()

                # Insérer la commande dans la collection `commandes`
                db.commandes.insert_one(commande_doc)
                print(f"\n🚀 Commande {COMMANDE_ID} envoyée. En attente des notifications...")
                
                while not processus_termine.is_set():
                    time.sleep(0.5)
                
                main_loop_active = False
            else:
                print("Action non reconnue.")

    except KeyboardInterrupt:
        print("\n👋 Au revoir !")
    finally:
        processus_termine.set()
        client.close()