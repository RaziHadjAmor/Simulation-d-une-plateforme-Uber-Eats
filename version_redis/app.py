import subprocess
import platform
import time
import os

def run_in_new_terminal(script_name, python_executable="python"):
    """
    Lance un script Python dans une nouvelle fenêtre de terminal selon le système d'exploitation.
    Windows, macOS et Linux sont pris en charge.
    """
    current_os = platform.system()
    
    # Sur certains systèmes, la commande Python peut être 'python3'
    if current_os != "Windows" and python_executable == "python":
        python_executable = "python3"

    # Obtenir le chemin absolu du script
    script_path = os.path.abspath(script_name)

    try:
        if current_os == "Windows":
            # La commande 'start' ouvre une nouvelle fenêtre.
            # 'cmd /k' garde la fenêtre ouverte après la fin du script.
            subprocess.Popen(f'start cmd /k "{python_executable} {script_path}"', shell=True)
        elif current_os == "Darwin":  # macOS
            # Pour macOS, nous utilisons AppleScript pour dire à l'application Terminal d'exécuter notre script.
            # Nous devons passer une commande complète à "do script".
            subprocess.Popen([
                'osascript',
                '-e',
                f'tell application "Terminal" to do script "{python_executable} {script_path}"'
            ])
        elif current_os == "Linux":
            # gnome-terminal est courant sur de nombreuses distributions Linux (comme Ubuntu).
            # Les utilisateurs d'autres environnements (KDE, XFCE) pourraient avoir besoin de modifier cela.
            # Par exemple : 'konsole -e' ou 'xfce4-terminal -e'.
            try:
                subprocess.Popen(['gnome-terminal', '--', python_executable, script_path])
            except FileNotFoundError:
                print("\n[ERREUR] 'gnome-terminal' non trouvé.")
                print("Essayez d'installer GNOME Terminal ou modifiez 'app.py' pour utiliser votre terminal (ex: 'konsole', 'xfce4-terminal').")
                return False
        else:
            print(f"\nDésolé, votre système d'exploitation ({current_os}) n'est pas géré automatiquement.")
            print(f"Veuillez lancer manuellement le script : {python_executable} {script_name}")
            return False
            
        return True

    except Exception as e:
        print(f"\nUne erreur est survenue en tentant de lancer {script_name}: {e}")
        return False


if __name__ == "__main__":
    # Liste des scripts à lancer
    scripts_to_launch = [
        "version_redis/redis_client.py",
        "version_redis/redis_manager.py",
        "version_redis/redis_restaurant.py",
        "version_redis/redis_livreur.py", 
    ]
    
    print("🚀 Démarrage de la simulation UberEats...")
    print("Chaque acteur sera lancé dans une nouvelle fenêtre de terminal.")
    
    for script in scripts_to_launch:
        print(f"-> Lancement de {script}...")
        if os.path.exists(script):
            if run_in_new_terminal(script):
                # Pause entre les lancements pour permettre aux fenêtres de s'ouvrir correctement
                time.sleep(1.5)
            else:
                print(f"   Impossible de lancer {script} automatiquement.")
        else:
            print(f"\n[ERREUR] Le fichier '{script}' est introuvable.")
            print("Assurez-vous que les 5 fichiers .py sont dans le même dossier.")
            break
            
    print("\n✅ Tous les acteurs ont été lancés. Vous pouvez maintenant interagir avec le client.")