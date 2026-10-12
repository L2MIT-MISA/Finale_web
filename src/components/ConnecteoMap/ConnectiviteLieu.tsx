import { useEffect, useState } from 'react';
import {
    chargerPylonesReseau,
    techDuPoint,
    couleurTech,
    labelTech,
    distanceM,
    SEUIL_M
} from './reseau';
import type { Pylone } from './reseau';
import './style/ConnectiviteLieu.css';

interface Props {
    position: { lat: number; lng: number };
}

function ConnectiviteLieu({ position }: Props) {
    const [pylones, setPylones] = useState<Pylone[] | null>(null);
    const [erreur, setErreur] = useState<string | null>(null);

    useEffect(() => {
        let alive = true;
        chargerPylonesReseau()
            .then((data) => {
                if (alive) setPylones(data);
            })
            .catch((err) => {
                if (alive) setErreur(err instanceof Error ? err.message : 'Erreur');
            });
        return () => {
            alive = false;
        };
    }, []);

    if (erreur) {
        return <div className="connectivite-vide">Information indisponible.</div>;
    }
    if (!pylones) {
        return <div className="connectivite-vide">Analyse en cours…</div>;
    }

    // Pylône le plus proche (pour la distance affichée)
    let dMin = Infinity;
    for (const p of pylones) {
        const d = distanceM(position, p);
        if (d < dMin) dMin = d;
    }

    const tech = techDuPoint(position, pylones) ?? 'none';
    const couleur = couleurTech(tech);
    const label = labelTech(tech);
    const horsPortee = Number.isFinite(dMin) && dMin > SEUIL_M;

    return (
        <div className="connectivite-lieu">
            <div className="connectivite-badge" style={{ background: couleur }}>
                {label}
            </div>
            <div className="connectivite-detail">
                {Number.isFinite(dMin)
                    ? `Antenne la plus proche à ${Math.round(dMin)} m`
                    : 'Aucune antenne répertoriée'}
                {horsPortee && ' — hors de portée estimée'}
            </div>
        </div>
    );
}

export default ConnectiviteLieu;
