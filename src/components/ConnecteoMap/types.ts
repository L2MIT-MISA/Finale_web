// Types partagés entre Carte.tsx, PanneauSecurite.tsx et useSecurityData.ts

export interface Bbox {
    sud: number;
    nord: number;
    ouest: number;
    est: number;
}

export interface Lieu {
    lat: number;
    lng: number;
    nom: string;
    libelle: string;
    adresse: string;
    bbox: Bbox | null;
}

export interface ServiceProche {
    count: number;
    nearestDistance: number | null; // mètres
    availability?: string;
}

export interface SecurityData {
    isDemo?: boolean;
    score: number;
    police: ServiceProche;
    hospitals: ServiceProche;
    pharmacies: ServiceProche;
    emergency?: {
        access: string; // Élevée | Bonne | Moyenne | Faible
        availability?: string;
    };
    connectivity?: {
        mobile: number; // pourcentage
        internet: number;
        lora: number;
    };
    accessibility?: {
        roads?: number; // pourcentage
        emergencyTime?: number; // minutes
    };
    resilience?: {
        connectivity: string;
        medical: string;
        alternatives: string;
    };
}
