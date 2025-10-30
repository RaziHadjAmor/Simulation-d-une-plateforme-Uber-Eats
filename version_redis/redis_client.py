import redis
import time
import json
import threading
import uuid

# --- Implémentation de l'Arbre Binaire de Recherche (ABR) ---

class Node:
    """Nœud de l'arbre contenant un restaurant."""
    def __init__(self, key, data):
        self.key = key  # La clé de tri (le nom du restaurant)
        self.data = data  # Les données complètes du restaurant
        self.left = None
        self.right = None

class BinarySearchTree:
    """Structure de données de l'Arbre Binaire de Recherche."""
    def __init__(self):
        self.root = None

    def insert(self, key, data):
        """Méthode publique pour insérer un nouveau restaurant."""
        if not self.root:
            self.root = Node(key, data)
        else:
            self._insert_recursive(self.root, key, data)

    def _insert_recursive(self, current_node, key, data):
        """Algorithme d'insertion récursif."""
        if key < current_node.key:
            if current_node.left is None:
                current_node.left = Node(key, data)
            else:
                self._insert_recursive(current_node.left, key, data)
        elif key > current_node.key: # Utiliser elif pour éviter d'insérer si la clé existe déjà
            if current_node.right is None:
                current_node.right = Node(key, data)
            else:
                self._insert_recursive(current_node.right, key, data)
        # else: La clé existe déjà, on ne fait rien (ou on pourrait mettre à jour data)
    
    def search(self, key):
        """Méthode publique pour rechercher un restaurant par son nom."""
        return self._search_recursive(self.root, key)

    def _search_recursive(self, current_node, key):
        """Algorithme de recherche récursif."""
        if current_node is None or current_node.key == key:
            return current_node.data if current_node else None
        
        if key < current_node.key:
            return self._search_recursive(current_node.left, key)
        else:
            return self._search_recursive(current_node.right, key)

# --- Fin de l'implémentation de l'ABR ---


# Connexion à Redis
r = redis.Redis(decode_responses=True)
processus_termine = threading.Event()

def ecouteur_client(commande_id):
    """Écoute les notifications concernant sa commande."""
    pubsub = r.pubsub()
    pubsub.subscribe('notifications')
    
    for message in pubsub.listen():
        if processus_termine.is_set():
            break # Sortir si le programme principal se termine
        if message['type'] == 'message':
            data = json.loads(message['data'])
            if data.get('commande_id') == commande_id:
                print(f"\n🔔 [NOTIFICATION CLIENT] : {data['message']}")
                if data.get('type') in ["COMMANDE_LIVREE", "COMMANDE_REJETEE", "AUCUN_LIVREUR"]:
                    print("-> Fin du processus de commande. Vous pouvez quitter avec Ctrl+C.")
                    processus_termine.set()

def charger_et_afficher_restaurants():
    """Récupère les restaurants, les charge dans l'ABR et les affiche."""
    print("="*30)
    print("🍽️ RESTAURANTS DISPONIBLES 🍽️")
    print("="*30)
    
    # Utilisation de KEYS comme dans votre code original
    restaurant_keys = r.keys("restaurant:*") 
    restaurants_data = {}
    abr_restaurants = BinarySearchTree()
    
    # Filtrer pour ne garder que les clés de restaurants (pas les :plats)
    # Et trier pour un affichage ordonné
    valid_restaurant_keys = sorted([k for k in restaurant_keys if ":plats" not in k])

    for rest_key in valid_restaurant_keys:
        rest_id = rest_key.split(":")[1]
        data = r.hgetall(rest_key)
        # Vérifier si data n'est pas vide et contient 'nom' avant d'insérer
        if data and 'nom' in data:
            restaurants_data[rest_id] = data
            abr_restaurants.insert(data['nom'].lower(), data)
            print(f"- {data['nom']} ({rest_id})")
        else:
             print(f"- Restaurant ID {rest_id} trouvé mais données invalides ou nom manquant.")


    print("="*50)
    return restaurants_data, abr_restaurants

def afficher_menu_restaurant(rest_id, rest_data):
    """Affiche le menu détaillé d'un restaurant."""
    # Assurer que rest_data est bien un dictionnaire avant d'accéder aux clés
    nom_resto = rest_data.get('nom', 'Nom inconnu')
    adresse_resto = rest_data.get('adresse', 'Adresse inconnue')
    
    print(f"\n--- Menu de {nom_resto} ({rest_id}) ---")
    print(f"    Adresse: {adresse_resto}")
    
    # 1. Récupérer les IDs (toujours non ordonnés à ce stade)
    plat_ids_set = r.smembers(f"restaurant:{rest_id}:plats")
    
    if not plat_ids_set:
        print("  -> Ce restaurant n'a pas de plats enregistrés.")
        return # Important de retourner ici pour éviter une erreur plus loin

    # 2. Convertir le set en liste et le trier (alphabétiquement)
    plat_ids_list_sorted = sorted(list(plat_ids_set))
    
    # 3. Boucler sur la liste triée pour afficher
    for plat_id in plat_ids_list_sorted: 
        plat_data = r.hgetall(f"plat:{plat_id}")
        # Vérifier si plat_data n'est pas vide (bonne pratique)
        if plat_data:
             print(f"  - [{plat_id}] {plat_data.get('nom', 'Nom inconnu')} - {plat_data.get('prix', '?.??')}€")
        else:
             print(f"  - [{plat_id}] Détails introuvables.")

if __name__ == "__main__":
    CLIENT_ID = f"client_{uuid.uuid4().hex[:4]}"
    COMMANDE_ID = f"cmd_{uuid.uuid4().hex[:6]}"
    
    print(f"👤 Bienvenue Client {CLIENT_ID}")
    
    restaurants, abr_restaurants = charger_et_afficher_restaurants()
    
    thread_ecoute = threading.Thread(target=ecouteur_client, args=(COMMANDE_ID,), daemon=True)
    thread_ecoute.start()

    main_loop_active = True
    try:
        while main_loop_active:
            action = input("\nQue souhaitez-vous faire ? ('commander', 'rechercher', 'quitter'): ").lower()

            if action == 'rechercher':
                nom_recherche = input("Entrez le nom exact du restaurant à rechercher : ").lower()
                resultat = abr_restaurants.search(nom_recherche)
                if resultat:
                    print("\n✅ Restaurant trouvé !")
                    print(f"   Nom: {resultat.get('nom', 'N/A')}") # Utiliser .get pour sécurité
                    print(f"   Adresse: {resultat.get('adresse', 'N/A')}")
                else:
                    print("\n❌ Restaurant non trouvé.")
                continue

            elif action == 'quitter':
                main_loop_active = False
                break

            elif action == 'commander':
                restaurant_choisi_id = ""
                while restaurant_choisi_id not in restaurants:
                    restaurant_choisi_id = input("Veuillez entrer l'ID du restaurant pour voir son menu et commander (ex: rest_01): ")
                    if restaurant_choisi_id not in restaurants:
                         print("❌ ID de restaurant non valide.")
                
                # S'assurer que les données du restaurant existent avant d'afficher le menu
                if restaurant_choisi_id in restaurants:
                    afficher_menu_restaurant(restaurant_choisi_id, restaurants[restaurant_choisi_id])
                else:
                    # Ce cas ne devrait pas arriver avec la boucle while ci-dessus, mais c'est une sécurité
                    print(f"Erreur interne: Impossible de trouver les données pour {restaurant_choisi_id}")
                    continue 

                plats_commande = []
                while True:
                    plat_choisi_id = input("Entrez l'ID d'un plat à ajouter (ou 'fin' pour terminer) : ")
                    if plat_choisi_id.lower() == 'fin':
                        if not plats_commande:
                            print("Votre panier est vide. Veuillez ajouter au moins un plat.")
                            continue
                        break # Sortir de la boucle d'ajout de plats
                    
                    # Vérifier si le plat appartient bien au menu du restaurant choisi
                    if r.sismember(f"restaurant:{restaurant_choisi_id}:plats", plat_choisi_id):
                        quantite_str = input(f"Quantité pour {plat_choisi_id} ? ")
                        try:
                            quantite = int(quantite_str)
                            if quantite > 0:
                                plats_commande.append({"id_plat": plat_choisi_id, "quantite": quantite})
                                print(f"Plat {plat_choisi_id} ajouté au panier.")
                            else:
                                print("❌ La quantité doit être supérieure à zéro.")
                        except ValueError:
                            print("❌ Quantité non valide. Veuillez entrer un nombre entier.")
                    else:
                        print("❌ Erreur: ID de plat invalide pour ce restaurant.")

                # --- NOUVEAU : CALCUL ET AFFICHAGE DU TOTAL ---
                total_commande = 0.0
                print("\n--- Récapitulatif de votre commande ---")
                for item in plats_commande:
                    plat_id = item['id_plat']
                    quantite = item['quantite']
                    # Récupérer les détails du plat depuis Redis
                    plat_data = r.hgetall(f"plat:{plat_id}")
                    nom_plat = plat_data.get('nom', plat_id) # Nom ou ID si nom absent
                    prix_str = plat_data.get('prix', '0') # Prix ou '0' si absent
                    
                    try:
                        # Tenter de convertir le prix en nombre
                        prix_unitaire = float(prix_str)
                        # Calculer le total pour cet item et l'ajouter au total général
                        total_item = prix_unitaire * quantite
                        total_commande += total_item
                        # Afficher la ligne du récapitulatif
                        print(f"  - {quantite}x {nom_plat} ({prix_unitaire:.2f}€/unité) = {total_item:.2f}€")
                    except (ValueError, TypeError):
                        # Gérer le cas où le prix n'est pas un nombre valide
                        print(f"  - {quantite}x {nom_plat} (Prix '{prix_str}' invalide, non compté)")
                        
                print("-" * 40)
                print(f"💰 TOTAL DE LA COMMANDE : {total_commande:.2f} €")
                print("-" * 40)
                # --- FIN DU CALCUL ET AFFICHAGE ---

                adresse_livraison = input("Votre adresse de livraison ? : ")
                
                commande = {
                    "client_id": CLIENT_ID, "commande_id": COMMANDE_ID,
                    "plats_details": plats_commande, "adresse_client": adresse_livraison,
                    "restaurant_id": restaurant_choisi_id,
                    "total_euros": f"{total_commande:.2f}" # Ajout du total à la commande envoyée
                }
                
                r.publish('commandes_clients', json.dumps(commande))
                print(f"\n🚀 Commande {COMMANDE_ID} (Total: {total_commande:.2f}€) envoyée. En attente de la suite...")
                
                # Boucle d'attente corrigée qui peut être interrompue
                while not processus_termine.is_set():
                    time.sleep(0.5)
                
                main_loop_active = False # Fin du programme après la commande
            else:
                print("Action non reconnue.")

    except KeyboardInterrupt:
        print("\n👋 Au revoir !")
    finally:
        # Signale au thread d'écoute de s'arrêter proprement
        processus_termine.set()