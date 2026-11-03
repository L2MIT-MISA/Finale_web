import type { Provider } from "@supabase/supabase-js";
import { supabase } from "./supabase";

const PAGE_DE_RETOUR_KEY = "connecteo-page-apres-connexion";
const ERREUR_CONNEXION_KEY = "connecteo-erreur-connexion";
const CONFIDENTIALITE_KEY = "connecteo-confidentialite-acceptee";

// Version de la politique de confidentialité : la changer redemande l'accord de chacun.
export const VERSION_CONFIDENTIALITE = "2026-11-03";

// ================================
// CONNEXION GOOGLE / FACEBOOK
// ================================

// Retour sur la racine du site : elle existe partout (Vercel comme nginx), contrairement à une adresse « /user ».
function adresseDeRetour() {
  return `${window.location.origin}/`;
}

async function seConnecterAvec(fournisseur: Provider) {
  return await supabase.auth.signInWithOAuth({
    provider: fournisseur,
    options: {
      redirectTo: adresseDeRetour(),
    },
  });
}

export async function signInWithGoogle() {
  return await seConnecterAvec("google");
}

export async function signInWithFacebook() {
  return await seConnecterAvec("facebook");
}

// ================================
// RETOUR APRÈS CONNEXION
// ================================

/** À appeler avant d'ouvrir la page de connexion : l'utilisateur y reviendra une fois connecté. */
export function memoriserLaPageActuelle() {
  const page = window.location.hash;

  try {
    if (page && page !== "#pages/Auth") {
      sessionStorage.setItem(PAGE_DE_RETOUR_KEY, page);
    }
  } catch {
    /* stockage indisponible */
  }
}

/** Message d'erreur laissé par un retour de Google ou Facebook (lu une seule fois). */
export function lireErreurDeConnexion(): string | null {
  try {
    const message = sessionStorage.getItem(ERREUR_CONNEXION_KEY);
    sessionStorage.removeItem(ERREUR_CONNEXION_KEY);
    return message;
  } catch {
    return null;
  }
}

function messageLisible(code: string | null, description: string | null) {
  if (code === "access_denied") {
    return "Connexion annulée. Vous pouvez réessayer quand vous voulez.";
  }

  return `La connexion n'a pas abouti${description ? ` : ${description}` : ""}. Réessayez dans un instant.`;
}

/**
 * À appeler une fois au chargement du site. Gère le retour de Google ou Facebook :
 * - erreur (refus, annulation) : message affiché sur la page de connexion, adresse nettoyée ;
 * - succès : la bibliothèque a déjà ouvert la session ; on renvoie l'utilisateur sur sa page d'origine.
 * Retourne la fonction qui arrête l'écoute.
 */
export function suivreLeRetourDeConnexion(): () => void {
  const adresse = new URL(window.location.href);
  const erreur = adresse.searchParams.get("error") ?? new URLSearchParams(adresse.hash.slice(1)).get("error");

  if (erreur) {
    const description =
      adresse.searchParams.get("error_description") ?? new URLSearchParams(adresse.hash.slice(1)).get("error_description");

    try {
      sessionStorage.setItem(ERREUR_CONNEXION_KEY, messageLisible(erreur, description));
    } catch {
      /* stockage indisponible */
    }

    ["error", "error_code", "error_description"].forEach((cle) => adresse.searchParams.delete(cle));
    adresse.hash = "#pages/Auth";
    window.history.replaceState(window.history.state, "", adresse.toString());
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }

  const { data } = supabase.auth.onAuthStateChange((evenement) => {
    if (evenement !== "SIGNED_IN") return;

    let page: string | null = null;

    try {
      page = sessionStorage.getItem(PAGE_DE_RETOUR_KEY);
      sessionStorage.removeItem(PAGE_DE_RETOUR_KEY);
    } catch {
      /* stockage indisponible */
    }

    // Retour seulement depuis la page de connexion ou l'accueil vide : jamais au milieu d'une autre page.
    if (page && (window.location.hash === "" || window.location.hash === "#pages/Auth")) {
      window.location.hash = page;
    } else if (window.location.hash === "#pages/Auth") {
      window.location.hash = "#pages/Home";
    }
  });

  return () => data.subscription.unsubscribe();
}

// ================================
// POLITIQUE DE CONFIDENTIALITÉ
// ================================

export function confidentialiteAcceptee(): boolean {
  try {
    return localStorage.getItem(CONFIDENTIALITE_KEY) === VERSION_CONFIDENTIALITE;
  } catch {
    return false;
  }
}

export function enregistrerAccordConfidentialite(accepte: boolean) {
  try {
    if (accepte) {
      localStorage.setItem(CONFIDENTIALITE_KEY, VERSION_CONFIDENTIALITE);
    } else {
      localStorage.removeItem(CONFIDENTIALITE_KEY);
    }
  } catch {
    /* stockage indisponible */
  }
}

// ================================
// UTILISATEUR CONNECTÉ
// ================================

export async function getCurrentUserProfile() {
  const { data, error } = await supabase.auth.getUser();

  if (error || !data.user) {
    return { profile: null, error: error ?? new Error("Non connecté") };
  }

  const user = data.user;
  const meta = user.user_metadata;

  // Google et Facebook fournissent "full_name" (ou "name")
  const fullName: string = meta.full_name ?? meta.name ?? user.email ?? "";

  // Profil d'affichage uniquement : aucun droit ne doit être décidé côté navigateur.
  const profile = {
    id: user.id,
    email: user.email ?? "",
    first_name: fullName.split(" ")[0],
    avatar_url: meta.avatar_url || meta.picture,
  };

  return { profile, error: null };
}

// ================================
// DÉCONNEXION
// ================================

export async function signOut() {
  return await supabase.auth.signOut();
}
