import { useEffect, useState } from "react";
import type { Connectivite, Lieu } from "../../pages/Search/searchTypes";
import { chargerConnectiviteEnCache } from "../../services/connectivite";

const SIMULTANES = 3;

// Connectivité de chaque lieu de la liste : celle fournie par l'IA, sinon calculée depuis les pylônes proches.
// Valeur `undefined` = calcul en cours, `null` = aucune donnée.
export function useConnectivites(lieux: Lieu[]): Record<string, Connectivite | null | undefined> {
  const [calculees, setCalculees] = useState<Record<string, Connectivite | null>>({});

  useEffect(() => {
    let annule = false;
    const file = lieux.filter((l) => l.connectivite === null);
    let suivant = 0;

    async function travailleur() {
      while (!annule && suivant < file.length) {
        const lieu = file[suivant++];
        const resultat = await chargerConnectiviteEnCache(lieu.position.lat, lieu.position.lng);
        if (!annule) setCalculees((c) => ({ ...c, [lieu.id]: resultat }));
      }
    }

    for (let i = 0; i < Math.min(SIMULTANES, file.length); i++) void travailleur();
    return () => { annule = true; };
  }, [lieux]);

  const sortie: Record<string, Connectivite | null | undefined> = {};
  for (const l of lieux) sortie[l.id] = l.connectivite ?? (l.id in calculees ? calculees[l.id] : undefined);
  return sortie;
}
