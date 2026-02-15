import os
import shutil

# Liste de vos applications à réinitialiser
APPS = ['shop', 'dashboard'] 

def reset():
    print("--- DÉBUT DU RESET COMPLET ---")
    
    # 1. Supprimer la BDD
    db_path = 'db.sqlite3'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✅ Base de données {db_path} supprimée.")
    else:
        print(f"⚠️  Base de données {db_path} introuvable.")

    # 2. Nettoyer les migrations
    for app_name in APPS:
        migration_dir = os.path.join(app_name, 'migrations')
        if os.path.exists(migration_dir):
            files = os.listdir(migration_dir)
            for file in files:
                file_path = os.path.join(migration_dir, file)
                # On supprime tout sauf __init__.py et __pycache__
                if file != '__init__.py' and file != '__pycache__':
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            print(f"✅ Migrations nettoyées pour l'app : {app_name}")
        else:
            print(f"⚠️  Dossier {migration_dir} introuvable.")

    print("\n--- RESET TERMINÉ ---")
    print("Lancez maintenant :")
    print("1. python manage.py makemigrations")
    print("2. python manage.py migrate")
    print("3. python manage.py createsuperuser")

if __name__ == "__main__":
    reset()