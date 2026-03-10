#!/bin/sh

# Arrêter le script si une commande échoue
set -e

# Appliquer les migrations
echo "➡️ Exécution des migrations Django..."
python manage.py makemigrations
python manage.py migrate

# Créer un superuser automatiquement (optionnel)
# Tu peux commenter si tu veux le faire manuellement
# python manage.py createsuperuser --noinput --username admin --email admin@example.com

# Lancer le serveur Django
echo "➡️ Démarrage du serveur Django..."
exec "$@"
