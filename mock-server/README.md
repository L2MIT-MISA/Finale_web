# mock-server : faux backend pour le front Connecteo

Simule l'IA et les pylônes sans toucher au code de `src/`. Aucune dépendance (Node 18+).

## Installation (une fois)
1. Copier `mock-server/env.local.example` vers `.env.local` à la racine du projet.
2. (Conseillé) `echo "mock-server/" >> .git/info/exclude`

## Utilisation
```bash
node mock-server/server.mjs   # terminal 1
npm run dev                   # terminal 2
```
(Relancer `npm run dev` si Vite tournait déjà : il lit `.env.local` au démarrage.)

## Ce qui est simulé
| Appel du front | Simulé par |
|---|---|
| `POST {VITE_AI_API_URL}/assistant` body `{ "texte": "…" }` | `simulerIA()` dans `ia-mock.mjs` |
| photos des lieux (`images[].url`) | `GET /mock-images/:i-:k.svg` |
| `GET /api/pylones/bbox` et `/api/pylones` | ~900 pylônes générés |

Réponses de l'IA simulée (toutes au format du JSON réel) :
- n'importe quel texte → 15 lieux de démo à Antananarivo, avec `images`, `note_google`, `avis`, `sources_citees` ;
- `marary` / `maroary` → cas « référentiel seul » : 1 lieu, sans image, position approximative, Google indisponible ;
- texte de moins de 3 caractères → `statut: "clarification_necessaire"`, aucun lieu.

Non simulé : connexion/inscription (Supabase Auth). Nominatim, OSRM et Google Maps sont les vrais services.

## Options
`PORT=8001 node mock-server/server.mjs` · `DELAY_MS=0` (sans délai)

## Tout enlever
Supprimer le dossier `mock-server/` et `.env.local` (ou y remettre les vraies valeurs).
Le front appelle alors la vraie IA sur `VITE_AI_API_URL`.
