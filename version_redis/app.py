import subprocess
import platform
import time
import os

def run_in_new_terminal(script_name, python_executable="python"):
    """
    Launches a Python script in a new terminal window, detecting the OS.
    """
    current_os = platform.system()
    
    # Ensure the python executable is correct for the OS
    if current_os != "Windows" and python_executable == "python":
        python_executable = "python3"

    # Get the full path to the script to avoid issues with working directories
    script_path = os.path.abspath(script_name)

    try:
        if current_os == "Windows":
            # The 'start' command opens a new window. 
            # 'cmd /k' keeps the window open after the script finishes.
            subprocess.Popen(f'start cmd /k "{python_executable} {script_path}"', shell=True)
        elif current_os == "Darwin":  # macOS
            # For macOS, we use AppleScript to tell the Terminal app to run our script.
            # We must pass a full command to "do script".
            subprocess.Popen([
                'osascript',
                '-e',
                f'tell application "Terminal" to do script "{python_executable} {script_path}"'
            ])
        elif current_os == "Linux":
            # gnome-terminal is common on many Linux distributions (like Ubuntu).
            # Users of other environments (KDE, XFCE) might need to change this.
            # For example: 'konsole -e' or 'xfce4-terminal -e'.
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
    # The order in which scripts are launched. 
    # It's good to start background services first.
    scripts_to_launch = [
        "NouvelleVersion/redis_client.py",
        "NouvelleVersion/redis_manager.py",
        "NouvelleVersion/redis_restaurant.py",
        "NouvelleVersion/redis_livreur.py", 
    ]
    
    print("🚀 Démarrage de la simulation UberEats...")
    print("Chaque acteur sera lancé dans une nouvelle fenêtre de terminal.")
    
    for script in scripts_to_launch:
        print(f"-> Lancement de {script}...")
        if os.path.exists(script):
            if run_in_new_terminal(script):
                # Pause between launches to allow windows to open cleanly
                time.sleep(1.5)
            else:
                print(f"   Impossible de lancer {script} automatiquement.")
        else:
            print(f"\n[ERREUR] Le fichier '{script}' est introuvable.")
            print("Assurez-vous que les 5 fichiers .py sont dans le même dossier.")
            break
            
    print("\n✅ Tous les acteurs ont été lancés. Vous pouvez maintenant interagir avec le client.")