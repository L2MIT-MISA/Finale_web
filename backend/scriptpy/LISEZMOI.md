# Connectéo : recherche de lieux de Madagascar (RAG + Google + résultats en JSON)

## IA par API : Gemini, puis Groq en secours
L'IA passe uniquement par des API (aucun modèle local), avec LangChain, et se choisit dans `.env` (modèle : `.env.example`, noms seulement).

| Variable | Rôle |
|---|---|
| `AGENT_FOURNISSEUR` | `off`, `gemini` ou `groq`. Absente : `gemini` si `AGENT_API_CLE` est renseignée, sinon `off` |
| `AGENT_API_CLE`, `MODELE` | clé et modèle du fournisseur principal (jamais `GOOGLE_API_KEY`, réservée à Custom Search) |
| `AGENT_SECOURS_FOURNISSEUR`, `AGENT_SECOURS_CLE`, `AGENT_SECOURS_MODELE` | secours essayé si le principal répond 429, est hors quota, lent ou en panne |
| `AGENT_CHAINE` | chaîne complète, dans l'ordre : `gemini,groq,cerebras,openrouter` (`mistral` facultatif). Un fournisseur sans clé est ignoré |
| `<NOM>_API_CLE`, `<NOM>_MODELES` | clé et modèles (virgules) de chaque fournisseur : `GEMINI_`, `GROQ_`, `CEREBRAS_`, `OPENROUTER_`, `MISTRAL_` |
| `AGENT_APPELS_PAR_MINUTE`, `AGENT_APPELS_PAR_JOUR` | plafonds par fournisseur (10 et 200 par défaut) ; au-delà : secours, puis réponses sans IA |
| `VECTEURS_FOURNISSEUR` | `off` (défaut) ou `gemini` (768 dimensions, clé `AGENT_API_CLE`). Groq n'a pas de vecteurs |
| `INDEXATION_AUTO` | `off` par défaut : rien n'est vectorisé sans décision (`python indexation.py`) |
| `HOTE_API` | adresse d'écoute, `127.0.0.1` par défaut |
| `MAPILLARY_JETON`, `GOOGLE_PLACES_CLE` | images facultatives (Google Places : compte de facturation requis, photos jamais mises en cache) |

Modèles par défaut (mesurés le 30/10/2026) : Gemini `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`
(`gemini-2.5-flash` est fermé aux nouveaux comptes ; 20 requêtes par jour et par modèle en gratuit) ; Groq
`openai/gpt-oss-120b`, `qwen/qwen3.8-27b` ; Cerebras `gpt-oss-120b`, `qwen-3.8-27b` (5 requêtes/min) ; OpenRouter
`google/gemma-4-31b-it:free`, `nvidia/nemotron-3.5-super-vl:free` (50 requêtes/jour pour tout le compte, liste changeante).
Chaque modèle a son quota : quand Google répond « retry in 23h », le modèle est écarté jusqu'au renouvellement. Les quotas gratuits ne sont pas publiés de
façon fixe : les lire dans Google AI Studio et la console Groq, puis régler les plafonds. Sur l'offre gratuite de Gemini,
Google peut utiliser les contenus envoyés pour améliorer ses produits : à mentionner dans la politique de confidentialité.
Ce qui part chez le fournisseur : le message (e-mails, numéros et adresses IP masqués), un historique court, les résultats
trouvés. Jamais de clé, d'identifiant de session ni de `DATABASE_URL` ; ni la clé ni les messages ne sont journalisés.

Comportement de l'assistant :
- recherche de lieux : règles, puis IA si la phrase est ambiguë ; OpenStreetMap, référentiel, RAG et web ; galerie
  d'images avec crédits (OpenStreetMap, site officiel, Google Places, Mapillary, Wikimedia Commons, Wikipédia) ;
- question de connaissance (« Connais-tu Andry Rasoanaivo ? ») : recherche web d'abord, puis agent LangChain
  (outils `rechercher_sur_le_web` et `lire_une_page`), réponse rédigée et sources affichées sous le message.
  Sans IA, les résultats web sont présentés comme un moteur de recherche ;
- urgence : numéros immédiatement, sans IA.

### Déploiement sur le VPS
```
cd ~/Finale_web && git fetch && git checkout ia-api-configurable && git pull
backend/scriptpy/.venv/bin/pip install -r backend/scriptpy/requirements.txt
nano backend/scriptpy/.env        # AGENT_FOURNISSEUR=gemini, AGENT_API_CLE=..., AGENT_SECOURS_FOURNISSEUR=groq, AGENT_SECOURS_CLE=...
chmod 600 backend/scriptpy/.env
sudo systemctl restart connecteo-api && journalctl -u connecteo-api -n 40 --no-pager
```
Le front doit être recompilé (`VITE_AI_API_URL=/api npm run build`, puis copie de `dist/` vers `/var/www/connecteo`) pour
afficher les sources web et attendre 40 s au lieu de 25 s.

Vérifications : le diagnostic du démarrage (journal) indique « Agent IA (LangChain) OK » pour chaque fournisseur ;
`curl -s http://127.0.0.1:8000/sante/rapide` renvoie `"ia": "ok"` ; dans le site, « Connais-tu Andry Rasoanaivo ? »
donne une réponse avec ses sources, et « restaurant à Antananarivo » des lieux avec photos.

Retour arrière immédiat : `AGENT_FOURNISSEUR=off` dans `.env` puis `sudo systemctl restart connecteo-api` (le site
fonctionne alors avec les règles, les résultats web et les réponses sans IA).

## Lancer tout le programme (une seule commande)
```
pip install -r requirements.txt
sudo apt install postgresql-16-pgvector          # adapter au numéro de version de PostgreSQL
# scripts SQL, dans cet ordre : schema_madagascar.sql, ajout_province.sql, vues_triggers.sql, schema_rag.sql
export DATABASE_URL=postgresql://utilisateur:mdp@localhost:5432/madagascar
export GOOGLE_API_KEY=... GOOGLE_CX=...          # Google Programmable Search (facultatif)
export AGENT_FOURNISSEUR=gemini AGENT_API_CLE=...  # IA (sinon réponses sans IA)
python demarrer.py
```
`demarrer.py` fait tout seul : diagnostic des services (PostgreSQL, IA, vecteurs, recherche web), indexation automatique des fichiers JSON si `INDEXATION_AUTO=on` (au démarrage puis toutes les 10 minutes, seulement ce qui a changé), API sur `http://127.0.0.1:8000`. **Aucun module ne se lance à la main.**

## Ce que déclenche la barre de recherche du site
Le site appelle une seule route : `POST /recherche {"requete": "cacao"}`. Le basculement est automatique :
1. requête sans mot utile (« aide ») → **fenêtre de précision** (voir plus bas), sans rien chercher ;
2. sinon, en parallèle : lieux officiels (PostgreSQL) + connaissances (pgvector, par le sens et par mots-clés) ;
3. des connaissances existent → **le résultat est renvoyé tout de suite** avec les lieux et leurs coordonnées ; l'IA rédige ses 2 phrases ensuite ;
4. rien trouvé → Google se lance en arrière-plan, l'IA extrait les lieux des pages, les coordonnées sont vérifiées, **la base apprend** (la même recherche n'ira plus sur Google) ;
5. toujours rien → fenêtre de précision (une seule fois, jamais de boucle).

Le site relit `GET /resultats/<id_resultat>` toutes les 2 secondes tant que `statut` vaut `en_cours`. Exemple complet : `interface_exemple.html` (carte Leaflet, liste, fenêtre de précision, urgence).

## Fichier JSON de résultat (`donnees/resultats/<id>.json`)
Exemples : `exemples/resultat_exemple.json` (le texte de `reponse.texte` y est simulé par le test) et `exemples/resultat_clarification_exemple.json`.

| Champ | Contenu |
|---|---|
| `statut` | `en_cours` · `termine` · `clarification_necessaire` · `urgence` · `erreur` |
| `requete` | `texte_original`, `mots_cles`, `intention` (`lieu` ou `theme`) |
| `reponse` | `texte` (2 phrases de l'IA), `source_principale` (`referentiel` · `base_connaissances` · `google` · `aucune`), `recherche_google` (`non_necessaire` · `en_cours` · `terminee` · `indisponible`) |
| `lieux[]` | `nom`, `niveau`, `code_officiel`, `region`, `district`, `produit`, `categorie`, `description`, `coordonnees` (`latitude`, `longitude`, `precision`), `note_google` (`note`, `nombre_avis` ou null), `avis`, `sources_citees`, `mots_cles`, `pertinence`, `confiance`, `origine`, `source` |
| `carte` | `centre`, `emprise` (sud, nord, ouest, est), `zoom_suggere` |
| `sources[]` | références des sources utilisées (fichier ou page web) |
| `clarification` | si `statut` = `clarification_necessaire` : `type` (`choix_categorie` ou `saisie_libre`), `raison`, `question`, `options[]` (`id`, `libelle`, `style`), `texte_libre_autorise`, `option_choisie`, `requete_initiale` |
| `urgence` | si `statut` = `urgence` : `message`, `contacts[]` |
| `avertissements[]` | tout ce qui a été dégradé ou écarté (base arrêtée, coordonnées inventées ignorées...) |

`coordonnees.precision` : `precis` (site) · `centroide` (centre d'une ville, d'une zone, d'une commune) · `repli_hierarchique` (position du secteur parent, ex. centre du pays). **Un lieu sans coordonnées n'est jamais renvoyé.**

## Fenêtre de précision (requête floue, comme sur la maquette)
- Le site affiche `clarification.question` et un bouton par `options[]` (`style: danger` = rouge).
- Clic sur une option → `POST /recherche/preciser {"id_resultat", "id_option", "texte_libre"}`.
- Si l'option exige une précision (ex. « Dans quelle ville ? »), la réponse est une clarification de type `saisie_libre` : le site affiche un champ de texte puis renvoie la même route avec `texte_libre`.
- « Une urgence » ne passe ni par l'IA ni par Google : le site affiche `urgence.message` et `urgence.contacts`.
- **À faire par l'équipe : renseigner `NUMEROS_D_URGENCE` dans `config.py` après vérification** (vide par défaut, un avertissement le signale). Options et questions : `OPTIONS_DE_CLARIFICATION` dans `config.py`.

## Données (trois dossiers, indexés automatiquement)
| Dossier | Format |
|---|---|
| `donnees/lieux/` | un fichier = un lieu (voir `exemples/lieu_template.json`) |
| `donnees/produits/` | liste d'enregistrements : vos 4 fichiers (cacao, vanille, canne à sucre, produits agricoles) |
| `donnees/complementaires/` | même format : `communes_infos.json` (1 079 communes : population, électricité, réseau mobile, pylônes) |

Clés des enregistrements (casse, accents, espaces et `_` ignorés : `Note_Google` = `Note Google`) : `Produit`, `Zone` ou `Région`, `District`, `Lieu`, `Catégorie`, `Code`, `Niveau`, `Latitude`, `Longitude`, `Precision`, `Note_Google`, `Nb_avis_Google`, `Description` ou `Autres`, `Avis`, `Sources` ou `Source`.

Nettoyage automatique à l'indexation : coordonnées en texte acceptées ; **signe moins oublié ou latitude/longitude inversées réparés** ; lieu « Madagascar » = position de repli ; liens OpenStreetMap retirés ; précision déduite (5 décimales ou plus et pas de géocodage OSM = `precis`, sinon `centroide`) ; un enregistrement sans nom de lieu mais avec produit, région et coordonnées est nommé « Produit (Région) ».

**Bilan de vos fichiers :** 70 enregistrements, 16 produits ; 2 latitudes corrigées (cacao : Sambava, vallée de la Bemarivo) ; 5 doublons produit/lieu entre fichiers (fusionnés dans les résultats) ; seulement 5 notes Google sur 70 ; seuls 5 points sont de vrais sites, les autres sont des centres de zones.

**Ce qui manque encore** (aucune donnée vérifiable fournie, rien d'inventé) : services de santé, numéros d'urgence, lieux célèbres, traditions. Modèle à remplir : `exemples/modele_services_sante.json` (à déposer dans `donnees/complementaires/` une fois rempli et vérifié).

Régénérer la fiche des communes : `python nettoyage.py --excel fichier.xlsx` puis `python generer_fichier_complementaire.py`. 625 communes sans pylône n'ont aucune coordonnée et sont exclues.

## Rapidité
Résultat affiché avant la rédaction de l'IA · l'IA ne rédige que 2 phrases (les lieux viennent directement de pgvector) · cache de 10 minutes sur les requêtes identiques (et pas de travail en double) · référentiel et pgvector interrogés en parallèle · pages Google lues en parallèle · modèles gardés en mémoire et préchauffés · indexation incrémentale (seul ce qui change est re-vectorisé) · index HNSW et GIN.

## Qui fait quoi
| Fichier | Rôle |
|---|---|
| `demarrer.py`, `api.py`, `diagnostic.py` | lancement unique, routes du site, état des services |
| `recherche.py` | **orchestrateur** (le programme principal) |
| `prompts.py` | **prompts système** (résumé rapide, extraction Google) |
| `base_donnees.py` | **tout le SQL** (référentiel PostGIS + pgvector) |
| `agent_ia.py` | agent LangChain : fournisseurs (Gemini, Groq), secours, quotas, outils web |
| `modele_ia.py` | vecteurs Gemini et réponses JSON |
| `connaissances_json.py`, `indexation.py` | fichiers JSON → fragments → vecteurs → pgvector |
| `recherche_web.py`, `coordonnees.py` | Google, pages web, géocodage, vérification des coordonnées |
| `classement.py`, `resultat_json.py`, `clarification.py`, `requete.py`, `modeles.py` | classement, fichier résultat, précisions, requête, structures |
| `nettoyage.py`, `generer_fichier_complementaire.py` | Excel → CSV propres → fiches des communes |
| `config.py` | tous les réglages (seuils, poids de classement, synonymes, options de précision) |

## Tests et limites
`TEST_DATABASE_URL=postgresql://... python tests/test_pipeline.py` : indexation incrémentale, mode rapide, cache, format produits, vos fichiers réels, Google et ses protections, pannes (base, vecteurs, modèle), clarification, urgence, API.
- **Testé** sur un vrai PostgreSQL 16 (PostGIS + pgvector) avec vos données, avec de **faux** modèles, Google et géocodeur. **Non testé** : appels réels à Gemini, Groq, Google et Nominatim.
- `SEUIL_SIMILARITE_FRAGMENT` est à **calibrer** avec les vrais vecteurs Gemini après la première indexation.
- Reste à écrire : import des CSV nettoyés dans PostgreSQL ; nettoyage de la feuille `SR.2.2` ; la correspondance `E = GULFSAT` est à confirmer (ignorée dans les fiches des communes).
