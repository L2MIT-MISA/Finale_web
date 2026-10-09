import type { SecurityData } from './types';

// Données de DÉMONSTRATION pour PanneauSecurite.
// Ce format est le contrat attendu de l'API :
//   GET /api/security?lat=-18.91&lng=47.52
// Pour passer en production, renvoyez le même objet avec isDemo: false
// (ou sans isDemo) et passez-le via la prop `securityData`.

export const MOCK_SECURITY_DATA: SecurityData = {
    isDemo: true,
    score: 82,

    police: {
        count: 2,
        nearestDistance: 850 // mètres
        // availability: '24h/24'   (optionnel)
    },

    hospitals: {
        count: 3,
        nearestDistance: 1200 // mètres
    },

    emergency: {
        access: 'Bonne', // Élevée | Bonne | Moyenne | Faible
        availability: '24h/24' // optionnel
    },

    pharmacies: {
        count: 8,
        nearestDistance: 300 // mètres
    },

    connectivity: {
        mobile: 80, // pourcentage
        internet: 70,
        lora: 90
    },

    accessibility: {
        roads: 85, // pourcentage de routes accessibles
        emergencyTime: 8 // minutes
    },

    resilience: {
        connectivity: 'Élevée',
        medical: 'Bonne',
        alternatives: 'Moyenne'
    }
};
