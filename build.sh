set -o errexit

pip install -r requirements.text

python manage.py collectstatic --no-input
python manage.py migrate