import { useState, type FormEvent } from 'react';
import {
  getCurrentUserProfile,
  isUsernameAvailable,
  signIn,
  signUp,
} from '../../services/auth';

import './Auth.css';

function Auth() {
  const [isLogin, setIsLogin] = useState(true);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');

  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setMessage('');

    const cleanUsername = username.trim();

    // Vérification du nom d'utilisateur
    if (!cleanUsername) {
      setMessage("Veuillez saisir votre nom d'utilisateur.");
      return;
    }

    // Vérification du mot de passe
    if (!password) {
      setMessage('Veuillez saisir votre mot de passe.');
      return;
    }

    // Vérification de la confirmation
    if (!isLogin && password !== confirmation) {
      setMessage('Les mots de passe ne correspondent pas.');
      return;
    }

    setLoading(true);

    // ==========================
    // CONNEXION
    // ==========================

    if (isLogin) {
      const { error } = await signIn(
        cleanUsername,
        password
      );

      if (error) {
        setLoading(false);

        setMessage(
          "Nom d'utilisateur ou mot de passe incorrect."
        );

        return;
      }

      // Récupérer le profil et le rôle
      const {profile,error: profileError,} = await getCurrentUserProfile();

      setLoading(false);

    if (profileError || !profile) {
        console.error('ERREUR PROFIL :', profileError);

        setMessage(
          'Impossible de récupérer les informations du compte.'
        );

        return;
      }
      
      // Redirection selon le rôle
      if (profile.role === 'ADMIN') {
        window.location.hash='pages/Admin';
      } else {
        window.location.hash='pages/Home';
      }

      return;
    }


    // ==========================
    // INSCRIPTION
    // ==========================

    try {
    const available =
    await isUsernameAvailable(cleanUsername);

    if (!available) {
        setLoading(false);

        setMessage(
        "Ce nom d'utilisateur est déjà utilisé."
        );

        return;
    }
    } catch (error) {
    setLoading(false);

    setMessage(
        "Impossible de vérifier le nom d'utilisateur."
    );

    return;
    }

    const { error } = await signUp(
      cleanUsername,
      password
    );

    setLoading(false);

    
    if (error) {
        console.error('ERREUR SUPABASE :', error);

        setMessage(
            `Erreur : ${error.message}`
        );

        return;
    }
    setMessage(
      'Compte créé avec succès. Vous pouvez maintenant vous connecter.'
    );



     // Redirection vers la page de l'utilisateur simple
      window.location.hash='Page/User';

  }

  return (
    <div className="auth-page">

      <div className="auth-card">

        {/* Logo */}
        <div className="auth-logo">
          <div className="logo-circle">
            <div className="logo-circle-middle">
              <div className="logo-circle-inner"></div>
            </div>
          </div>

          <h1>Connectéo</h1>
        </div>

        {/* Titre */}
        <div className="auth-header">

          <h2>
            {isLogin ? 'Connexion': 'Créer un compte'}
          </h2>

          <p>
            {isLogin ? 'Accédez à votre espace personnel' : 'Créez votre compte Connectéo'}
          </p>

        </div>

        {/* Formulaire */}
        <form className="auth-form" onSubmit={handleSubmit}>

          {/* Username */}
          <div className="input-group">

            <div className="input-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M20 21C20 18.2386 17.3137 16 14 16H10C6.68629 16 4 18.2386 4 21"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />

                <circle
                  cx="12"
                  cy="8"
                  r="4"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />
              </svg>
            </div>

            <input
              type="text"
              value={username}
              onChange={(event) =>
                setUsername(event.target.value)
              }
              placeholder="Nom d'utilisateur"
              autoComplete="username"
            />

          </div>

          {/* Password */}
          <div className="input-group">

            <div className="input-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect
                  x="5"
                  y="10"
                  width="14"
                  height="10"
                  rx="2"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />

                <path
                  d="M8 10V7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7V10"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>
            </div>

            <input
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              placeholder="Mot de passe"
              autoComplete={
                isLogin
                  ? 'current-password'
                  : 'new-password'
              }
            />

          </div>

          {/* Confirmation */}
          {!isLogin && (
            <div className="input-group">

              <div className="input-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <rect
                    x="5"
                    y="10"
                    width="14"
                    height="10"
                    rx="2"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  />

                  <path
                    d="M8 10V7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7V10"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>

              <input
                type="password"
                value={confirmation}
                onChange={(event) =>
                  setConfirmation(event.target.value)
                }
                placeholder="Confirmer le mot de passe"
                autoComplete="new-password"
              />

            </div>
          )}

          {/* Message */}
          {message && (
            <div className="auth-message">
              {message}
            </div>
          )}

          {/* Bouton */}
          <button
            className="auth-button"
            type="submit"
            disabled={loading}
          >
            {loading ? 'Chargement...': isLogin? 'Se connecter': "S'inscrire"}
          </button>

        </form>

        {/* Changement connexion / inscription */}
        <div className="auth-switch">

          {isLogin ? (
            <>
              <span>Pas encore de compte ?</span>

              <button
                type="button"
                onClick={() => {
                  setIsLogin(false);
                  setMessage('');
                }}
              >
                S'inscrire
              </button>
            </>
          ) : (
            <>
              <span>Vous avez déjà un compte ?</span>

              <button
                type="button"
                onClick={() => {
                  setIsLogin(true);
                  setMessage('');
                }}
              >
                Se connecter
              </button>
            </>
          )}

        </div>

      </div>

    </div>
  );
}

export default Auth;