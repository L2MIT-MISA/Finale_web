import { useState, useEffect } from "react";
import {
  signInWithGoogle,
  signInWithFacebook,
  signOut,
  confidentialiteAcceptee,
  enregistrerAccordConfidentialite,
  lireErreurDeConnexion
} from "../../services/auth";
import { supabase } from "../../services/supabase";

import "./Auth.css";



function Auth() {
  const [message, setMessage] = useState("");

  const [loading, setLoading] = useState(false);

  const [imageIndex, setImageIndex] = useState(0);

  const [accepte, setAccepte] = useState(confidentialiteAcceptee);

  const [connecte, setConnecte] = useState<string | null>(null);


  /* =====================================================
     ÉTAT DE LA SESSION ET ERREUR DE RETOUR
  ===================================================== */

  useEffect(() => {
    const erreur = lireErreurDeConnexion();

    if (erreur) {
      setMessage(erreur);
    }

    supabase.auth.getSession().then(({ data }) => {
      const utilisateur = data.session?.user;
      setConnecte(utilisateur ? utilisateur.email ?? utilisateur.user_metadata?.full_name ?? "votre compte" : null);
    });

    const { data: ecoute } = supabase.auth.onAuthStateChange((_evenement, session) => {
      setConnecte(session?.user ? session.user.email ?? "votre compte" : null);
    });

    return () => ecoute.subscription.unsubscribe();
  }, []);


  function changerAccord(valeur: boolean) {
    setAccepte(valeur);
    enregistrerAccordConfidentialite(valeur);

    if (valeur) {
      setMessage("");
    }
  }


  async function handleSignOut() {
    setLoading(true);
    await signOut();
    setLoading(false);
  }


  /* =====================================================
     IMAGES
  ===================================================== */

  const images = [
    "/images/auth/login_1.jpeg",
    "/images/auth/login_2.jpeg",
    "/images/auth/login_3.png"
  ];


  /* =====================================================
     CHANGEMENT AUTOMATIQUE DE L'IMAGE
  ===================================================== */

  useEffect(() => {
    const interval = setInterval(() => {
      setImageIndex((index) => {
        return (index + 1) % images.length;
      });

    }, 10000);


    return () => {
      clearInterval(interval);
    };

  }, []);



  /* =====================================================
     CONNEXION GOOGLE
  ===================================================== */

  async function handleGoogleLogin() {
    if (!accepte) {
      setMessage("Veuillez d'abord accepter la politique de confidentialité.");
      return;
    }

    setMessage("");

    setLoading(true);


    const { error } =
      await signInWithGoogle();


    if (error) {
      setLoading(false);

      setMessage(
        "Impossible de se connecter avec Google."
      );
    }
  }

  /* =====================================================
     CONNEXION FACEBOOK
  ===================================================== */
  async function handleFacebookLogin() {
    if (!accepte) {
      setMessage("Veuillez d'abord accepter la politique de confidentialité.");
      return;
    }

    setMessage("");
    setLoading(true);

    const { error } = await signInWithFacebook();

    if (error) {
      setLoading(false);

      setMessage(
        "Impossible de se connecter avec Facebook."
      );
    }
  }

  /* =====================================================
     AFFICHAGE
  ===================================================== */

  return (
    <div className="pages">

      <div className="auth-page">


        {/* =================================================
                   PARTIE GAUCHE
                ================================================= */}

        <div className="auth-left">


          {/* IMAGE */}

          <div className="auth-image-container">

            <img
              src={images[imageIndex]}
              className="auth-background"
              alt="Illustration Connectéo"
            />

            <div className="auth-overlay"></div>

          </div>


          {/* TEXTE */}

          <div className="auth-left-content">


            <h1>
              Trouver le bon service ne
              <br />
              devrait jamais être compliqué.
            </h1>


            <div className="auth-footer-text">

              <p>
                L'équipe Connectéo-Antananarivo
              </p>

            </div>
          </div>

        </div>


        {/* =================================================
                   PARTIE DROITE
                ================================================= */}

        <div className="auth-right">


          <div className="auth-card">


            {/* TITRE */}

            <div className="auth-title">

              <h2>
                Bon retour parmi nous
              </h2>

              <p>
                Connectez-vous à votre espace Connectéo.
              </p>

            </div>


            {/* DÉJÀ CONNECTÉ */}

            {connecte && (
              <div className="auth-connecte">
                <p>
                  Vous êtes connecté avec <strong>{connecte}</strong>.
                </p>

                <div className="auth-connecte-actions">
                  <button type="button" className="sso-button" onClick={() => { window.location.hash = "#pages/Home"; }}>
                    Retour à l'accueil
                  </button>

                  <button type="button" className="sso-button" onClick={handleSignOut} disabled={loading}>
                    Se déconnecter
                  </button>
                </div>
              </div>
            )}


            {/* BOUTONS SSO */}

            {!connecte && (
            <form className="auth-form">

              {/* POLITIQUE DE CONFIDENTIALITÉ */}

              <label className="auth-consentement">
                <input
                  type="checkbox"
                  checked={accepte}
                  onChange={(e) => changerAccord(e.target.checked)}
                />

                <span>
                  J'ai lu et j'accepte la{" "}
                  <a href="#pages/Confidentialite">politique de confidentialité</a>
                  {" "}de Connectéo.
                </span>
              </label>


              {/* GOOGLE */}

              <button
                type="button"
                className="sso-button"
                onClick={handleGoogleLogin}
                disabled={loading || !accepte}
              >

                <img
                  src="/images/auth/google.png"
                  alt="Google"
                  className="sso-icon"
                />

                <span>
                  Continuer avec Google
                </span>

              </button>


              {/* FACEBOOK */}

              <button
                type="button"
                className="sso-button"
                disabled={loading || !accepte}
                onClick={handleFacebookLogin}
              >

                <img
                  src="/images/auth/facebook.png"
                  alt="Facebook"
                  className="sso-icon"
                />

                <span>
                  Continuer avec Facebook
                </span>

              </button>


            </form>
            )}


            {/* MESSAGE */}

            {message && (
              <div className="auth-message">
                {message}
              </div>
            )}
          </div>

        </div>


      </div>

    </div>
  );
}


export default Auth;