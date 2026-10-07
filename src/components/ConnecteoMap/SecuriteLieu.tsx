import { useEffect, useMemo, useState } from 'react';
import PanneauSecurite from './PanneauSecurite';
import { useSecurityData } from './useSecurityData';
import type { Lieu } from './types';

/*
 * À placer dans la section « Sécurité » du panneau du bas.
 *
 *     <SecuriteLieu lieu={selected} />
 *
 * Le bouton « Afficher plus » est inclus. Les données (police, hôpitaux,
 * pharmacies…) ne sont chargées qu'au clic.
 *
 * Si ton parent a déjà son propre bouton, passe son état :
 *
 *     <SecuriteLieu lieu={selected} ouvert={plusOuvert} />
 */
interface LieuSimple {
    nom: string;
    sousTitre?: string;
    position: { lat: number; lng: number };
}

interface Props {
    lieu: LieuSimple | null | undefined;
    /** Optionnel : état « Afficher plus » géré par le parent. */
    ouvert?: boolean;
}

function SecuriteLieu({ lieu: source, ouvert: ouvertParent }: Props) {
    const [ouvertLocal, setOuvertLocal] = useState(false);
    const controle = ouvertParent !== undefined;
    const ouvert = controle ? ouvertParent : ouvertLocal;

    // Valeurs simples pour garder une référence stable
    // (sinon la requête serait relancée à chaque rendu du parent).
    const lat = source?.position.lat;
    const lng = source?.position.lng;
    const nom = source?.nom;
    const sousTitre = source?.sousTitre;

    const lieu = useMemo<Lieu | null>(() => {
        if (lat === undefined || lng === undefined || nom === undefined) return null;
        return { lat, lng, nom, libelle: nom, adresse: sousTitre ?? '', bbox: null };
    }, [lat, lng, nom, sousTitre]);

    // Nouveau lieu : on referme
    useEffect(() => {
        setOuvertLocal(false);
    }, [lat, lng]);

    // On ne charge les données que si la section est ouverte
    const { data, chargement, erreur } = useSecurityData(ouvert ? lieu : null);

    if (!lieu) return null;

    return (
        <div className="secu-wrap">
            {!controle && (
                <button
                    type="button"
                    className="secu-plus"
                    onClick={() => setOuvertLocal((v) => !v)}
                    aria-expanded={ouvert}
                >
                    {ouvert ? 'Afficher moins' : 'Afficher plus'}
                </button>
            )}
            {ouvert && (
                <PanneauSecurite
                    integre
                    lieu={lieu}
                    securityData={data}
                    chargement={chargement}
                    erreur={erreur}
                />
            )}
        </div>
    );
}

export default SecuriteLieu;
