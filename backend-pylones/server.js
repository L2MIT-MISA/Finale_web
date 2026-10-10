import express from 'express';
import cors from 'cors';
import neo4j from 'neo4j-driver';
import 'dotenv/config';
import { createServer } from 'http';

const app = express();
app.use(cors());

console.log('   Configuration Neo4j :');
console.log('   URI      =', process.env.NEO4J_URI);
console.log('   USER     =', process.env.NEO4J_USER);
console.log('   DATABASE =', process.env.NEO4J_DATABASE);
console.log('   PORT     =', process.env.PORT);

// CONNEXION NEO4J
const driver = neo4j.driver(
    process.env.NEO4J_URI,
    neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASSWORD)
);

driver.verifyConnectivity()
    .then(() => console.log('Connexion Neo4j OK'))
    .catch((err) => console.error('Erreur Neo4j :', err.message));

// FONCTIONS UTILITAIRES
async function query(cypher, params = {}) {
    const session = driver.session({
        database: process.env.NEO4J_DATABASE || 'neo4j'
    });
    try {
        const result = await session.run(cypher, params);
        return result.records;
    } finally {
        await session.close();
    }
}

// Convertit les entiers Neo4j en JS natif
function toNative(record) {
    const out = {};
    record.keys.forEach((key) => {
        const value = record.get(key);
        out[key] = neo4j.isInt(value) ? value.toNumber() : value;
    });
    return out;
}

// Normalise une valeur "tech_*" en booléen.
// Accepte : true/false, 1/0, '1'/'0', 'oui'/'non', 'Oui'/'Non', 'true'/'false'.
function estVrai(value) {
    if (value === true) return true;
    if (value === false || value === null || value === undefined) return false;
    if (typeof value === 'number') return value !== 0;
    const s = String(value).trim().toLowerCase();
    return s === '1' || s === 'true' || s === 'oui' || s === 'yes' || s === 'vrai';
}

// Retourne la tech dominante d'un enregistrement pylône.
// Priorité : 5g > 4g > 3g > 2g > none
function techDominante(rec) {
    if (estVrai(rec.tech_5g)) return '5g';
    if (estVrai(rec.tech_4g)) return '4g';
    if (estVrai(rec.tech_3g)) return '3g';
    if (estVrai(rec.tech_2g)) return '2g';
    return 'none';
}

// ROUTES

// Route racine : liste des endpoints
app.get('/', (req, res) => {
    res.json({
        message: 'API Connecteo operationnelle',
        endpoints: {
            pylones: '/api/pylones',
            pyloneParCode: '/api/pylones/:codeSite',
            pylonesBbox: '/api/pylones/bbox?minLat=...&minLng=...&maxLat=...&maxLng=...',
            pylonesNetwork: '/api/pylones/network?minLat=...&minLng=...&maxLat=...&maxLng=...'
        }
    });
});

// Route : tous les pylones
app.get('/api/pylones', async (req, res) => {
    try {
        console.log('Requete /api/pylones');
        const records = await query(`
            MATCH (p:Pylone)
            WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
            RETURN
                p.nom             AS nom,
                p.code_site       AS code_site,
                p.code_operateur  AS code_operateur,
                p.type_site       AS type_site,
                p.lat             AS lat,
                p.lon             AS lon,
                p.hauteur_m       AS hauteur_m,
                p.nom_commune     AS nom_commune,
                p.nom_district    AS nom_district,
                p.nom_region      AS nom_region,
                p.milieu          AS milieu,
                p.proprietaire    AS proprietaire,
                p.source_energie  AS source_energie,
                p.tech_2g         AS tech_2g,
                p.tech_3g         AS tech_3g,
                p.tech_4g         AS tech_4g,
                p.tech_5g         AS tech_5g
            LIMIT 5000
        `);
        console.log(`   ${records.length} pylones envoyes`);
        res.json(records.map(toNative));
    } catch (err) {
        console.error('Erreur /api/pylones :', err.message);
        res.status(500).json({ error: err.message });
    }
});

// Route : pylones dans une bounding box (utile si beaucoup de points)
// IMPORTANT : cette route DOIT etre ddeclardee AVANT /api/pylones/:codeSite.
// Express matche les routes dans l'ordre de ddeclaration, et ":codeSite" est
// un parametre gdenderique qui capture n'importe quel segment — y compris le
// mot "bbox". Si /:codeSite detait ddeclardee avant, une requete vers
// /api/pylones/bbox serait interceptdee avec codeSite = "bbox" et renverrait
// toujours 404, sans jamais atteindre le vrai handler bbox.
app.get('/api/pylones/bbox', async (req, res) => {
    try {
        const { minLat, minLng, maxLat, maxLng } = req.query;

        if (!minLat || !minLng || !maxLat || !maxLng) {
            return res.status(400).json({
                error: 'Parametres manquants : minLat, minLng, maxLat, maxLng'
            });
        }

        const records = await query(
            `MATCH (p:Pylone)
             WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
               AND p.lat >= $minLat AND p.lat <= $maxLat
               AND p.lon >= $minLng AND p.lon <= $maxLng
             RETURN
                p.nom            AS nom,
                p.code_site      AS code_site,
                p.code_operateur AS code_operateur,
                p.type_site      AS type_site,
                p.lat            AS lat,
                p.lon            AS lon,
                p.hauteur_m      AS hauteur_m,
                p.nom_commune    AS nom_commune,
                p.nom_region     AS nom_region,
                p.proprietaire   AS proprietaire,
                p.tech_2g        AS tech_2g,
                p.tech_3g        AS tech_3g,
                p.tech_4g        AS tech_4g,
                p.tech_5g        AS tech_5g
             LIMIT 1000`,
            {
                minLat: parseFloat(minLat),
                minLng: parseFloat(minLng),
                maxLat: parseFloat(maxLat),
                maxLng: parseFloat(maxLng)
            }
        );
        res.json(records.map(toNative));
    } catch (err) {
        console.error('Erreur /api/pylones/bbox :', err.message);
        res.status(500).json({ error: err.message });
    }
});

// ============================================================
// Route LEGERE : uniquement lat/lon + tech dominante
// Utilisee par le client pour colorier les polylignes d'itineraire
// selon la couverture reseau (5G/4G = vert, 3G = jaune, 2G = orange).
// IMPORTANT : aussi declaree AVANT /api/pylones/:codeSite.
// ============================================================
app.get('/api/pylones/network', async (req, res) => {
    try {
        const { minLat, minLng, maxLat, maxLng } = req.query;
        const useBbox = minLat && minLng && maxLat && maxLng;

        const cypher = useBbox
            ? `MATCH (p:Pylone)
               WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
                 AND p.lat >= $minLat AND p.lat <= $maxLat
                 AND p.lon >= $minLng AND p.lon <= $maxLng
               RETURN p.lat AS lat, p.lon AS lon,
                      p.tech_5g AS tech_5g,
                      p.tech_4g AS tech_4g,
                      p.tech_3g AS tech_3g,
                      p.tech_2g AS tech_2g`
            : `MATCH (p:Pylone)
               WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
               RETURN p.lat AS lat, p.lon AS lon,
                      p.tech_5g AS tech_5g,
                      p.tech_4g AS tech_4g,
                      p.tech_3g AS tech_3g,
                      p.tech_2g AS tech_2g`;

        const params = useBbox
            ? {
                minLat: parseFloat(minLat),
                minLng: parseFloat(minLng),
                maxLat: parseFloat(maxLat),
                maxLng: parseFloat(maxLng)
            }
            : {};

        const records = await query(cypher, params);

        const data = records
            .map((rec) => {
                const lat = Number(rec.get('lat'));
                const lon = Number(rec.get('lon'));
                if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

                const tech = techDominante({
                    tech_5g: rec.get('tech_5g'),
                    tech_4g: rec.get('tech_4g'),
                    tech_3g: rec.get('tech_3g'),
                    tech_2g: rec.get('tech_2g')
                });

                return { lat, lon, tech };
            })
            .filter(Boolean);

        console.log(`Requete /api/pylones/network : ${data.length} pylones`);
        res.json(data);
    } catch (err) {
        console.error('Erreur /api/pylones/network :', err.message);
        res.status(500).json({ error: err.message });
    }
});

// Route : un pylone par code_site
// Ddeclardee APRES /bbox et /network pour la raison expliqudee ci-dessus.
app.get('/api/pylones/:codeSite', async (req, res) => {
    try {
        const records = await query(
            `MATCH (p:Pylone {code_site: $codeSite})
             RETURN
                p.nom          AS nom,
                p.code_site    AS code_site,
                p.type_site    AS type_site,
                p.lat          AS lat,
                p.lon          AS lon,
                p.proprietaire AS proprietaire
             LIMIT 1`,
            { codeSite: req.params.codeSite }
        );
        if (records.length === 0) {
            return res.status(404).json({ error: 'Pylone non trouve' });
        }
        res.json(toNative(records[0]));
    } catch (err) {
        console.error('Erreur /api/pylones/:codeSite :', err.message);
        res.status(500).json({ error: err.message });
    }
});

// ============================================================
// LORA : lecture temps reel depuis Neo4j + diffusion WebSocket
// ============================================================

async function chargerPylones() {
    try {
        const records = await query(`
            MATCH (p:Pylone)
            WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
            RETURN p.nom AS nom, p.code_site AS code_site, p.lat AS lat, p.lon AS lon
        `);
        return records.map(toNative);
    } catch (err) {
        console.error('Erreur chargement pylones :', err.message);
        return [];
    }
}

let pylonesCache = [];
const INTERVALLE_LECTURE_S = 2;

// httpServer commun a Express (routes REST) et au WebSocket (flux temps reel)
const httpServer = createServer(app);
// const wss = new WebSocketServer({ server: httpServer });

// (diffusion LoRa — laissee telle quelle, non utilisee dans ce focus)
// eslint-disable-next-line no-unused-vars
function diffuserEtat(etat) {
    const message = JSON.stringify({ type: 'lora_update', dispositifs: etat });
    // wss.clients.forEach(...)
}

// DEMARRAGE
const PORT = process.env.PORT || 3001;

async function demarrer() {
    pylonesCache = await chargerPylones();
    console.log(`   ${pylonesCache.length} pylones charges`);

    httpServer.listen(PORT, () => {
        console.log(`   API demarree sur http://localhost:${PORT}`);
        console.log(`   Test : http://localhost:${PORT}/api/pylones`);
        console.log(`   Reseau : http://localhost:${PORT}/api/pylones/network`);
    });
}

demarrer();