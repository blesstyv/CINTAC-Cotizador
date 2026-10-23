#!/usr/bin/env bash

set -o errexit


echo "========================================"
echo "CINTAC Cotizador - Build de producción"
echo "========================================"


echo "Instalando dependencias..."

python -m pip install \
    -r requirements.txt


echo "Recolectando archivos estáticos..."

python manage.py collectstatic \
    --no-input


echo "Aplicando migraciones..."

python manage.py migrate \
    --no-input


echo "Verificando datos maestros..."

python manage.py cargar_datos


echo "========================================"
echo "Build finalizado correctamente."
echo "========================================"