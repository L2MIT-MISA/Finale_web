import { supabase } from './supabase';


const AUTH_DOMAIN = 'zbzghokzcdiozscitetk.supabase.co';

function usernameToEmail(username: string): string {
  return `${username.toLowerCase()}@${AUTH_DOMAIN}`;
}

/**
 * Vérifie si un nom d'utilisateur est disponible.
 *
 * true  = disponible
 * false = déjà utilisé
 */
export async function isUsernameAvailable(username: string): Promise<boolean> {
  const normalizedUsername = username
    .trim()
    .toLowerCase();

  const { data, error } = await supabase.rpc(
    'is_username_available',
    {
      p_username: normalizedUsername,
    }
  );

  if (error) {
    throw error;
  }

  return data === true;
}

/**
 * Inscription
 */
export async function signUp(username: string,password: string) 
{
  const normalizedUsername = username
    .trim()
    .toLowerCase();

  const { data, error } =await supabase.auth.signUp({email: usernameToEmail(normalizedUsername),password,
      options: {
        data: {
          username: normalizedUsername,
        },
      },
    });

  return {
    data,
    error,
  };
}

/**
 * Connexion
 */
export async function signIn(username: string,password: string) {
  const normalizedUsername = username
    .trim()
    .toLowerCase();

  const { data, error } =
    await supabase.auth.signInWithPassword({
      email: usernameToEmail(normalizedUsername),
      password,
    });

  return {
    data,
    error,
  };
}

/**
 * Déconnexion
 */
export async function signOut() {
  return await supabase.auth.signOut();
}

/**
 * Récupérer le profil de l'utilisateur connecté
 */
export async function getCurrentUserProfile() {
  const {data: { user },
} = await supabase.auth.getUser();

  if (!user) {
    return {
      user: null,
      profile: null,
      error: null,
    };
  }

  const { data: profile, error } =
    await supabase
      .from('users')
      .select(
        'id, username, role, created_at'
      )
      .eq('id', user.id)
      .single();

  return {
    user,
    profile,
    error,
  };
}