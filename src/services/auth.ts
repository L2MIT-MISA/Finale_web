import { supabase } from './supabase';






// ================================
// CONNEXION GOOGLE
// ================================

export async function signInWithGoogle()
{
    return await supabase.auth.signInWithOAuth({
        provider: "google",

        options: {
            redirectTo: `${window.location.origin}/user`,
        },
    });
}

// Connexion avec Facebook
export async function signInWithFacebook() {
    const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'facebook',
        options: {
            redirectTo: `${window.location.origin}/user`,
        },
    });

    return {
        data,
        error,
    };
}

// ================================
// UTILISATEUR CONNECTÉ
// ================================

export async function getCurrentUserProfile()
{
    const { data, error } = await supabase.auth.getUser();

    if (error || !data.user)
    {
        return { profile: null, error: error ?? new Error("Non connecté") };
    }

    const user = data.user;
    const meta = user.user_metadata;

    // Google et Facebook fournissent "full_name" (ou "name")
    const fullName: string = meta.full_name ?? meta.name ?? user.email ?? "";

    const profile = {
        id: user.id,
        email: user.email ?? "",
        first_name: fullName.split(" ")[0],
        avatar_url:  data.user?.user_metadata?.avatar_url || data.user?.user_metadata?.picture,
        role: "USER",
    };

    return { profile, error: null };
}


// ================================
// DÉCONNEXION
// ================================

export async function signOut()
{
    return await supabase.auth.signOut();
}