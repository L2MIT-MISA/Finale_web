import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;

const supabasePublishableKey =
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

if (!supabaseUrl || !supabasePublishableKey) {
  throw new Error(
    "Configuration Supabase absente : définir VITE_SUPABASE_URL et VITE_SUPABASE_PUBLISHABLE_KEY avant le build."
  );
}

// PKCE : au retour de Google ou Facebook, l'adresse ne porte qu'un code à usage unique (?code=…), échangé
// puis retiré par la bibliothèque. Le mode implicite mettait les jetons dans le « # », déjà utilisé par le routage.
export const supabase = createClient(supabaseUrl, supabasePublishableKey, {
  auth: {
    flowType: "pkce",
    detectSessionInUrl: true,
    persistSession: true,
    autoRefreshToken: true,
  },
});
