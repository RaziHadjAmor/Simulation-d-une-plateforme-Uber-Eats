import redis
import json

# Connexion à la base de données Redis
try:
    r = redis.Redis(decode_responses=True)
    r.ping()
    print("✅ Connexion à Redis réussie.")
except redis.exceptions.ConnectionError as e:
    print(f"❌ ERREUR: Impossible de se connecter à Redis. Assurez-vous que votre conteneur Docker est en cours d'exécution.")
    exit()

def afficher_menu_principal():
    """Affiche le menu des actions disponibles."""
    print("\n" + "="*40)
    print("🛠️ Outil d'Administration en Ligne de Commande pour Redis 🛠️")
    print("="*40)
    print("\n--- Commandes de Lecture (Read) ---")
    print("1. Afficher les détails d'un restaurant (HGETALL)")
    print("2. Lister le menu d'un restaurant (SMEMBERS)")
    print("\n--- Commandes de Création / Mise à jour (Create/Update) ---")
    print("3. Créer un nouveau restaurant (HSET)")
    print("4. Ajouter un plat au menu d'un restaurant (SADD, HSET)")
    print("5. [Opération avancée] Incrémenter la popularité (INCR)")
    print("\n--- Commandes de Suppression (Delete) ---")
    print("6. Supprimer un restaurant entier (DEL)")
    print("7. Supprimer un plat du menu d'un restaurant (SREM)")
    print("\n--- Autres Commandes ---")
    print("8. Vérifier l'existence d'une clé (EXISTS)")
    print("9. [Opération avancée] Renommer la clé d'un client (RENAME)")
    print("\n0. Quitter")
    print("="*40)

# --- Fonctions pour chaque action ---

def afficher_restaurant():
    rest_id = input("Entrez l'ID du restaurant (ex: rest_01): ")
    key = f"restaurant:{rest_id}"
    if not r.exists(key):
        print(f"❌ ERREUR: Le restaurant '{rest_id}' n'existe pas.")
        return
    
    details = r.hgetall(key)
    popularite = r.get(f"restaurant:{rest_id}:popularite") or "0"
    
    print("\n--- Détails du restaurant ---")
    for champ, valeur in details.items():
        print(f"  - {champ.capitalize()}: {valeur}")
    print(f"  - Popularité (vues): {popularite}")
    print(f"Commande Redis utilisée : HGETALL {key}")

def lister_menu():
    rest_id = input("Entrez l'ID du restaurant (ex: rest_01): ")
    key_menu = f"restaurant:{rest_id}:plats"
    if not r.exists(key_menu):
        print(f"❌ ERREUR: Le restaurant '{rest_id}' n'existe pas ou n'a pas de menu.")
        return
        
    plat_ids = r.smembers(key_menu)
    print(f"\n--- Menu de {rest_id} ---")
    if not plat_ids:
        print("Le menu est vide.")
    for plat_id in plat_ids:
        nom_plat = r.hget(f"plat:{plat_id}", "nom")
        print(f"  - {plat_id}: {nom_plat}")
    print(f"Commande Redis utilisée : SMEMBERS {key_menu}")

def creer_restaurant():
    print("\n--- Création d'un nouveau restaurant ---")
    rest_id = input("Nouvel ID (ex: rest_99): ")
    key = f"restaurant:{rest_id}"
    key_index = "restaurants:ids" # Clé de l'index
    
    if r.exists(key):
        print(f"❌ ERREUR: L'ID '{rest_id}' existe déjà.")
        return
    
    nom = input("Nom du restaurant: ")
    adresse = input("Adresse du restaurant: ")
    
    # Utiliser un pipeline pour la transaction
    pipe = r.pipeline()
    pipe.hset(key, mapping={"nom": nom, "adresse": adresse})
    pipe.sadd(key_index, rest_id) # Ajouter au Set d'index
    pipe.execute()
    
    print(f"✅ Restaurant '{nom}' créé avec succès !")
    print(f"Commandes Redis utilisées (dans un pipeline) :")
    print(f"1. HSET {key} nom \"{nom}\" adresse \"{adresse}\"")
    print(f"2. SADD {key_index} {rest_id}")


def ajouter_plat():
    rest_id = input("ID du restaurant où ajouter le plat (ex: rest_01): ")
    if not r.exists(f"restaurant:{rest_id}"):
        print(f"❌ ERREUR: Le restaurant '{rest_id}' n'existe pas.")
        return
        
    print("\n--- Ajout d'un nouveau plat ---")
    plat_id = input("Nouvel ID du plat (ex: plat_999): ")
    key_plat = f"plat:{plat_id}"
    key_menu = f"restaurant:{rest_id}:plats"
    
    if r.exists(key_plat):
        print(f"❌ ERREUR: L'ID de plat '{plat_id}' existe déjà.")
        return
        
    nom = input("Nom du plat: ")
    prix = input("Prix du plat: ")
    description = input("Description du plat: ")
    
    # Utiliser un pipeline pour la transaction
    pipe = r.pipeline()
    # Ajout du plat en tant que Hash
    pipe.hset(key_plat, mapping={
        "nom": nom, 
        "prix": prix, 
        "description": description, 
        "id_restaurant": rest_id
    })
    # Ajout de l'ID du plat au Set du menu du restaurant
    pipe.sadd(key_menu, plat_id)
    pipe.execute()
    
    print(f"✅ Plat '{nom}' ajouté au menu de {rest_id} !")
    print(f"Commandes Redis utilisées (dans un pipeline) :")
    print(f"1. HSET {key_plat} ...")
    print(f"2. SADD {key_menu} {plat_id}")

def incrementer_popularite():
    rest_id = input("Entrez l'ID du restaurant à populariser (ex: rest_01): ")
    key = f"restaurant:{rest_id}:popularite"
    
    nouvelle_valeur = r.incr(key)
    print(f"✅ Le compteur de popularité pour {rest_id} est maintenant de {nouvelle_valeur}.")
    print(f"Commande Redis utilisée : INCR {key}")

def supprimer_restaurant():
    rest_id = input("Entrez l'ID du restaurant à SUPPRIMER (ex: rest_01): ")
    key_resto = f"restaurant:{rest_id}"
    key_menu = f"restaurant:{rest_id}:plats"
    key_index = "restaurants:ids"
    
    if not r.exists(key_resto):
        print(f"❌ ERREUR: Le restaurant '{rest_id}' n'existe pas.")
        return

    confirmation = input(f"Êtes-vous sûr de vouloir supprimer DÉFINITIVEMENT le restaurant {rest_id} et tout son menu ? (oui/non): ").lower()
    if confirmation == 'oui':
        # Récupérer les plats AVANT de supprimer le menu
        plat_ids = r.smembers(key_menu)
        
        # Utiliser un pipeline pour tout supprimer
        pipe = r.pipeline()
        pipe.delete(key_resto)  # Supprimer le Hash du restaurant
        pipe.delete(key_menu)   # Supprimer le Set du menu
        pipe.srem(key_index, rest_id) # Retirer de l'index global
        
        # Supprimer aussi les Hash de chaque plat associé
        for plat_id in plat_ids:
            pipe.delete(f"plat:{plat_id}")
            
        pipe.execute()
        
        print(f"✅ Restaurant {rest_id} et ses {len(plat_ids)} plats associés ont été supprimés.")
        print(f"Commandes Redis utilisées : SMEMBERS, DEL, SREM (dans un pipeline)")
    else:
        print("Suppression annulée.")

def supprimer_plat():
    rest_id = input("ID du restaurant (ex: rest_01): ")
    plat_id = input("ID du plat à SUPPRIMER du menu (ex: plat_001): ")
    key_menu = f"restaurant:{rest_id}:plats"
    key_plat = f"plat:{plat_id}"
    
    # SREM renvoie 1 si l'élément a été supprimé, 0 sinon
    if r.srem(key_menu, plat_id) == 1:
        # Supprimer aussi le Hash du plat lui-même
        r.delete(key_plat)
        print(f"✅ Plat {plat_id} supprimé du menu de {rest_id} et de la base.")
        print(f"Commandes Redis utilisées : SREM {key_menu} {plat_id} ET DEL {key_plat}")
    else:
        print(f"❌ ERREUR: Le plat {plat_id} n'a pas été trouvé dans le menu de {rest_id}.")

def verifier_existence():
    key = input("Entrez la clé exacte à vérifier (ex: client:cli_001 ou plat:plat_001): ")
    if r.exists(key):
        print(f"✅ La clé '{key}' EXISTE.")
    else:
        print(f"❌ La clé '{key}' N'EXISTE PAS.")
    print(f"Commande Redis utilisée : EXISTS {key}")
    
def renommer_client():
    ancien_id = input("Ancien ID du client (ex: client:cli_001): ")
    if not r.exists(ancien_id):
        print(f"❌ ERREUR: La clé '{ancien_id}' n'existe pas.")
        return
    nouveau_id = input("Nouveau ID du client (ex: client:new_001): ")
    if r.exists(nouveau_id):
        print(f"❌ ERREUR: La nouvelle clé '{nouveau_id}' existe déjà.")
        return
        
    # Utiliser un pipeline pour être atomique
    pipe = r.pipeline()
    pipe.rename(ancien_id, nouveau_id) # Renommer le Hash
    pipe.srem("clients:ids", ancien_id.split(":")[1]) # Retirer l'ancien ID de l'index
    pipe.sadd("clients:ids", nouveau_id.split(":")[1]) # Ajouter le nouveau ID à l'index
    pipe.execute()
    
    print(f"✅ Le client a été renommé de '{ancien_id}' à '{nouveau_id}' (index mis à jour).")
    print(f"Commandes Redis utilisées : RENAME, SREM, SADD (dans un pipeline)")

# --- Boucle principale du programme ---

def main():
    while True:
        afficher_menu_principal()
        choix = input("Votre choix : ")
        
        if choix == '1':
            afficher_restaurant()
        elif choix == '2':
            lister_menu()
        elif choix == '3':
            creer_restaurant()
        elif choix == '4':
            ajouter_plat()
        elif choix == '5':
            incrementer_popularite()
        elif choix == '6':
            supprimer_restaurant()
        elif choix == '7':
            supprimer_plat()
        elif choix == '8':
            verifier_existence()
        elif choix == '9':
            renommer_client()
        elif choix == '0':
            print("👋 Au revoir !")
            break
        else:
            print("❌ Choix non valide. Veuillez réessayer.")
        
        input("\nAppuyez sur Entrée pour continuer...")

if __name__ == "__main__":
    main()