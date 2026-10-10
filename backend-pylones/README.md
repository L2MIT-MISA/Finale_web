# Backend Pylônes

API qui expose les données des pylônes réseau (5G/4G/3G/2G) pour la coloration
de l'itinéraire selon la couverture réseau.

## Endpoint

`GET /api/pylones/reseau` → retourne un tableau de pylônes

## Lancer

```bash
npm install
npm start
# ou
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
