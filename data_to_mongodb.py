from pymongo import MongoClient
import csv

client = MongoClient('mongodb://localhost:27017/')
db = client['ubereats']
col_commandes = db['commandes']

# Exemple pour importer les commandes et les plats associés
with open('Commande.csv', encoding='utf-8') as cfile, \
     open('Commande_Plat.csv', encoding='utf-8') as pfile:
    cmdreader = csv.DictReader(cfile)
    platreader = list(csv.DictReader(pfile))
    for row in cmdreader:
        plats_cmd = [p for p in platreader if p['id_commande'] == row['id_commande']]
        doc = {
            "id_commande": row["id_commande"],
            "statut": row["statut"],
            "date_": row["date_"],
            "id_client": row["id_client"],
            "id_restaurant": row["id_restaurant"],
            "plats": plats_cmd
        }
        col_commandes.insert_one(doc)