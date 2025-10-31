import csv
import os

def convertir_txt_en_csv(fichiers_txt, dossier_destination="dataset_csv"):
    """
    Prend une liste de noms de fichiers .txt et les convertit en fichiers .csv.
    Le contenu est lu et réécrit pour garantir un format CSV propre.
    """
    print("Démarrage de la conversion...")

    # Créer le dossier de destination (ex: "dataset_csv") s'il n'existe pas
    os.makedirs(dossier_destination, exist_ok=True)
    print(f"Vérification/Création du dossier de destination : {dossier_destination}")
    
    # On boucle sur chaque nom de fichier fourni dans la liste
    for fichier_txt in fichiers_txt:
        # Vérifier si le fichier source existe avant de continuer
        if not os.path.exists(fichier_txt):
            print(f"-> ❌ ERREUR : Le fichier '{fichier_txt}' est introuvable. Il est ignoré.")
            continue

        # Construire le chemin de destination
        # 1. Obtenir le nom de base du fichier (ex: "restaurants")
        nom_fichier_sans_ext = os.path.splitext(os.path.basename(fichier_txt))[0]
        # 2. Créer le nouveau nom de fichier .csv (ex: "restaurants.csv")
        nom_csv = f"{nom_fichier_sans_ext}.csv"
        # 3. Créer le chemin complet de destination (ex: "dataset_csv/restaurants.csv")
        fichier_csv = os.path.join(dossier_destination, nom_csv)
        
        try:
            # Ouvrir le fichier source en lecture ('r') et le fichier de destination en écriture ('w')
            # newline='' est une option importante pour éviter les lignes vides supplémentaires dans le CSV
            with open(fichier_txt, mode='r', encoding='utf-8') as fin, \
                 open(fichier_csv, mode='w', encoding='utf-8', newline='') as fout:
                
                # Utiliser le module CSV pour lire le fichier source, même si c'est un .txt
                # Cela gère correctement les délimiteurs et les éventuelles guillemets
                lecteur_csv = csv.reader(fin)
                
                # Utiliser le module CSV pour écrire dans le fichier de destination
                ecrivain_csv = csv.writer(fout)
                
                # Copier chaque ligne du fichier source vers le fichier de destination
                for ligne in lecteur_csv:
                    ecrivain_csv.writerow(ligne)
            
            print(f"-> ✅ SUCCÈS : Le fichier '{fichier_txt}' a été converti en '{fichier_csv}'.")

        except Exception as e:
            print(f"-> ❌ ERREUR lors de la conversion de '{fichier_txt}' : {e}")

    print("\nConversion terminée.")

if __name__ == "__main__":
    # Liste des fichiers que vous souhaitez convertir.
    # Vous pouvez ajouter ou supprimer des noms de fichiers ici.
    fichiers_a_convertir = [
        "dataset_txt/restaurants.txt",
        "dataset_txt/plats.txt",
        "dataset_txt/livreurs.txt"
    ]
    
    convertir_txt_en_csv(fichiers_a_convertir)