import csv
import json
import os

def csv_to_json(csv_filepath, json_filename):
    # Création du dossier dataset_json s'il n'existe pas
    os.makedirs('dataset_json', exist_ok=True)
    
    data = []
    with open(csv_filepath, encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            data.append(row)
    # Chemin complet pour le fichier JSON dans dataset_json
    json_filepath = os.path.join('dataset_json', json_filename)
    with open(json_filepath, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

# Appels de conversion avec enregistrement dans dataset_json
csv_to_json('dataset_csv/restaurants.csv', 'restaurants.json')
csv_to_json('dataset_csv/plats.csv', 'plats.json')
csv_to_json('dataset_csv/livreurs.csv', 'livreurs.json')