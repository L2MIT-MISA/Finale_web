# Connectéo

Application web React/TypeScript avec Vite, associée à une API Python pour la recherche de lieux. Le front et le backend se compilent et se démarrent séparément.

## Prérequis

- Node.js compatible avec Vite 8 : `20.19+` ou `22.12+`.
- npm, fourni avec Node.js.
- Python 3.10 ou supérieur pour le backend.
- Pour toutes les fonctions du backend : PostgreSQL avec les schémas et tables attendus, et une clé d’API Gemini (Groq en secours, facultatif). Aucun modèle d’IA local n’est utilisé.
- Supabase et une clé Google Maps pour les fonctions concernées du front.

## Installation du front

À la racine du projet :

```bash
npm ci
```

`npm ci` installe les dépendances exactement selon `package-lock.json`.

### Variables d’environnement du front

Créer un fichier `.env.local` à la racine du projet. Vite lit ces variables au démarrage et les inclut dans le build.

```dotenv
VITE_SUPABASE_URL=https://<votre-projet>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<votre-cle-publique-supabase>

VITE_GOOGLE_MAPS_API_KEY=<votre-cle-google-maps>

VITE_AI_API_URL=http://127.0.0.1:8000
VITE_SEARCH_API_URL=http://127.0.0.1:8000
```

`VITE_SUPABASE_URL` et `VITE_SUPABASE_PUBLISHABLE_KEY` sont nécessaires à l’initialisation du client Supabase. La clé Google Maps est nécessaire aux fonctionnalités de carte qui l’utilisent. Les URL d’API pointent par défaut vers `http://127.0.0.1:8000` et peuvent être omises si le backend est lancé sur cette adresse.

Les variables préfixées par `VITE_` sont exposées au navigateur après compilation. N’y placer aucun mot de passe, clé privée ou clé de service.

## Lancer en développement

Dans un terminal, à la racine du projet :

```bash
npm run dev
```

Le front est généralement disponible à l’adresse `http://localhost:5173`.

Dans un second terminal, démarrer le backend selon les étapes de la section [Backend Python](#backend-python). Le front contacte l’API à l’adresse définie par `VITE_AI_API_URL` et `VITE_SEARCH_API_URL`.

Pour rendre le serveur de développement accessible depuis le réseau local :

```bash
npm run dev -- --host 0.0.0.0
```

## Compiler le front pour la production

```bash
npm run build
```

Cette commande exécute le contrôle TypeScript (`tsc -b`), puis construit les fichiers statiques avec Vite. Les fichiers générés sont placés dans `dist/`.

Pour tester localement le build :

```bash
npm run preview
```

Le serveur de prévisualisation utilise généralement `http://localhost:4173`.

Les variables `VITE_*` sont intégrées au moment du build. Pour changer les URL d’API ou les clés publiques utilisées par le site, définir les bonnes valeurs avant `npm run build`, puis reconstruire le front.

Le build Vite ne compile pas et n’inclut pas le backend Python : celui-ci doit être déployé et exécuté séparément. En production, le serveur web qui distribue `dist/` doit aussi être configuré pour renvoyer la page d’entrée pour les routes de l’application.

## Vérifications du front

Vérification TypeScript et compilation de production :

```bash
npm run build
```

Lint :

```bash
npm run lint
```

## Backend Python

Le backend se trouve dans `backend/scriptpy/`. Il fournit notamment l’API de recherche et de conversation.

### Configurer le backend

Créer `backend/scriptpy/.env` :

```dotenv
DATABASE_URL=postgresql://<utilisateur>:<mot-de-passe>@localhost:5432/<base>

AGENT_FOURNISSEUR=gemini
AGENT_API_CLE=<votre-cle-gemini>
AGENT_SECOURS_FOURNISSEUR=groq
AGENT_SECOURS_CLE=<votre-cle-groq>

PORT=8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Recherche web facultative
GOOGLE_API_KEY=
GOOGLE_CX=
BRAVE_API_KEY=
```

Les variables Google et Brave sont facultatives. La disponibilité de la recherche web dépend des fournisseurs configurés et accessibles. `CORS_ORIGINS` doit contenir l’origine du front ; le backend autorise toutes les origines par défaut si cette variable n’est pas définie.

Ne pas versionner ce fichier ni y placer de secrets dans des fichiers suivis par Git.

### Base de données

Le backend se connecte à une base PostgreSQL déjà configurée. Il attend notamment les tables du référentiel et des infrastructures utilisées par le code, ainsi que `collecte.fragment_lieu`.

Le fichier `backend/scriptpy/schema_rag.sql` prépare la partie RAG : il crée les extensions `vector`, `pg_trgm` et `unaccent`, le schéma `collecte`, la table des fragments et ses index. Il ne crée pas les tables du référentiel géographique ou des infrastructures. Ces données et schémas doivent donc être installés séparément dans la base cible.

Après avoir configuré `DATABASE_URL`, appliquer le schéma RAG si nécessaire :

```bash
psql "$DATABASE_URL" -f backend/scriptpy/schema_rag.sql
```

L’extension PostGIS et les tables attendues par le référentiel doivent déjà être disponibles. Vérifier l’état réel de la base avant d’appliquer un script de migration. `migration_vecteurs_768.sql` concerne une migration de dimension des vecteurs ; ne pas l’exécuter comme une étape standard d’installation.

### IA par API

L’assistant utilise uniquement des API : Gemini en principal, Groq en secours. Créer les clés sur https://aistudio.google.com/apikey et https://console.groq.com/keys, puis les placer dans `backend/scriptpy/.env` (jamais dans un fichier suivi par Git). Toutes les variables sont listées dans `backend/scriptpy/.env.example` et expliquées dans `backend/scriptpy/LISEZMOI.md`. Sans clé, le site fonctionne sans IA.

La recherche vectorielle est désactivée par défaut (`VECTEURS_FOURNISSEUR=off`). Avec `VECTEURS_FOURNISSEUR=gemini`, les vecteurs ont 768 dimensions, cohérentes avec `schema_rag.sql`.

### Installer et démarrer le backend

Depuis la racine du projet :

```bash
npm run backend:install
npm run backend
```

La première commande crée l’environnement Python `backend/scriptpy/.venv` et installe les dépendances de `requirements.txt`. La seconde démarre l’API sur le port défini par `PORT`, qui vaut `8000` par défaut.

Le backend affiche un diagnostic des services au démarrage. L’état de l’API est consultable à `http://localhost:8000/sante`. Une base de données ou une IA indisponible (clé absente, quota atteint) peut désactiver certaines fonctions sans empêcher le serveur de démarrer : le site répond alors sans IA.

## Tests du backend

Les tests utilisent `unittest` et des services simulés. Depuis le dossier du backend :

```bash
cd backend/scriptpy
.venv/bin/python -m unittest discover -s tests -v
```

## Démarrage rapide avec le serveur simulé

Le dépôt contient un serveur de démonstration pour simuler certaines réponses de l’API, sans installer le backend Python.

Dans un premier terminal :

```bash
node mock-server/server.mjs
```

Dans un second terminal :

```bash
npm run dev
```

Le fichier `mock-server/env.local.example` peut être copié vers `.env.local` à la racine pour configurer le front avec le mock. Redémarrer Vite après toute modification de `.env.local`.

Le mock ne remplace pas Supabase Auth ; l’authentification et certaines fonctions externes nécessitent toujours leur configuration réelle. Si le port `8000` est déjà occupé, démarrer le mock sur un autre port, puis mettre à jour les URL d’API du front.

## Résumé des commandes

| Besoin | Commande |
|---|---|
| Installer les dépendances du front | `npm ci` |
| Démarrer le front | `npm run dev` |
| Compiler le front pour la production | `npm run build` |
| Prévisualiser le build | `npm run preview` |
| Vérifier le lint | `npm run lint` |
| Installer le backend Python | `npm run backend:install` |
| Démarrer le backend | `npm run backend` |
| Tester le backend | `cd backend/scriptpy && .venv/bin/python -m unittest discover -s tests -v` |

## Dépannage

- **Le front ne démarre pas** : vérifier la version de Node.js, puis relancer `npm ci`.
- **Erreur Supabase au chargement** : vérifier `VITE_SUPABASE_URL` et `VITE_SUPABASE_PUBLISHABLE_KEY` dans `.env.local`, puis redémarrer Vite.
- **La carte ne s’affiche pas** : vérifier la clé `VITE_GOOGLE_MAPS_API_KEY` et les autorisations associées dans Google Cloud.
- **Le front ne joint pas le backend** : vérifier que l’API écoute au bon port et que `VITE_AI_API_URL`, `VITE_SEARCH_API_URL` et `CORS_ORIGINS` sont cohérents.
- **Le diagnostic PostgreSQL signale des tables absentes** : `schema_rag.sql` ne crée que la partie RAG ; installer ou restaurer les schémas du référentiel et des infrastructures requis.
- **Le diagnostic signale l’agent IA indisponible** : vérifier `AGENT_FOURNISSEUR`, `AGENT_API_CLE` et le modèle (`MODELE`) ; une clé refusée ou un quota atteint est indiqué dans le journal du démarrage.