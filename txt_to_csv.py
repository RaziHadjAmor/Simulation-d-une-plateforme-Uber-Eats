import csv
import os

def convertir_txt_en_csv(fichiers_txt):
    """
    Prend une liste de noms de fichiers .txt et les convertit en fichiers .csv.
    Le contenu est lu et réécrit pour garantir un format CSV propre.
    """
    print("Démarrage de la conversion...")
    
    # On boucle sur chaque nom de fichier fourni dans la liste
    for fichier_txt in fichiers_txt:
        # Vérifier si le fichier source existe avant de continuer
        if not os.path.exists(fichier_txt):
            print(f"-> ❌ ERREUR : Le fichier '{fichier_txt}' est introuvable. Il est ignoré.")
            continue

        # Construire le nouveau nom de fichier en remplaçant l'extension
        # os.path.splitext sépare le nom de l'extension de manière fiable
        nom_base, _ = os.path.splitext(fichier_txt)
        fichier_csv = f"{nom_base}.csv"
        
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
        "dataset_txt/livreurs.txt",
        "dataset_txt/clients.txt"
    ]
    
    convertir_txt_en_csv(fichiers_a_convertir)