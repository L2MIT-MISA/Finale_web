import { useState, useEffect } from "react";

import { useLang } from "../../i18n/LanguageContext";

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
    const { lang } = useLang();

    const [message, setMessage] = useState("");

    const [loading, setLoading] = useState(false);

    const [imageIndex, setImageIndex] = useState(0);

    const [accepte, setAccepte] = useState(confidentialiteAcceptee);

    const [connecte, setConnecte] = useState<string | null>(null);


    /* =====================================================
       TRADUCTIONS
    ===================================================== */

    const translations = {
        FR: {
            slogan: "Trouver le bon service ne devrait jamais être compliqué.",
            welcome: "Bon retour parmi nous",
            description: "Connectez-vous à votre espace Connectéo.",
            continueGoogle: "Continuer avec Google",
            continueFacebook: "Continuer avec Facebook",
            googleError: "Impossible de se connecter avec Google.",
            facebookError: "Impossible de se connecter avec Facebook.",
            acceptPrefix: "J'ai lu et j'accepte la",
            privacyLink: "politique de confidentialité",
            acceptAnd: "et les",
            termsLink: "conditions d'utilisation",
            acceptSuffix: "de Connectéo.",
            acceptRequired: "Veuillez d'abord accepter la politique de confidentialité.",
            connectedAs: "Vous êtes connecté avec",
            backHome: "Retour à l'accueil",
            signOutLabel: "Se déconnecter",
            fallbackAccount: "votre compte"
        },

        MG: {
            slogan: "Tsy tokony ho sarotra ny mahita ny tolotra mety.",
            welcome: "Faly miarahaba anao indray",
            description: "Midira ao amin'ny Connectéo.",
            continueGoogle: "Hanohy amin'ny Google",
            continueFacebook: "Hanohy amin'ny Facebook",
            googleError: "Tsy afaka miditra amin'ny alalan'ny Google.",
            facebookError: "Tsy afaka miditra amin'ny alalan'ny Facebook.",
            acceptPrefix: "Namaky sy manaiky ny",
            privacyLink: "politikan'ny fiainana manokana",
            acceptAnd: "sy ny",
            termsLink: "fepetra fampiasana",
            acceptSuffix: "an'ny Connectéo aho.",
            acceptRequired: "Mba ekeo aloha ny politikan'ny fiainana manokana.",
            connectedAs: "Tafiditra amin'ny",
            backHome: "Hiverina any amin'ny fandraisana",
            signOutLabel: "Hiala",
            fallbackAccount: "ny kaontinao"
        },

        EN: {
            slogan: "Finding the right service should never be complicated.",
            welcome: "Welcome back",
            description: "Sign in to your Connectéo account.",
            continueGoogle: "Continue with Google",
            continueFacebook: "Continue with Facebook",
            googleError: "Unable to sign in with Google.",
            facebookError: "Unable to sign in with Facebook.",
            acceptPrefix: "I have read and accept the",
            privacyLink: "privacy policy",
            acceptAnd: "and the",
            termsLink: "terms of use",
            acceptSuffix: "of Connectéo.",
            acceptRequired: "Please accept the privacy policy first.",
            connectedAs: "You are signed in as",
            backHome: "Back to home",
            signOutLabel: "Sign out",
            fallbackAccount: "your account"
        }
    };


    /* =====================================================
       LANGUE ACTUELLE
    ===================================================== */

    const currentLang = translations[lang] || translations.FR;


    /* =====================================================
       SESSION, ERREUR DE RETOUR ET ACCORD
    ===================================================== */

    useEffect(() => {
        const erreur = lireErreurDeConnexion();

        if (erreur) {
            setMessage(erreur);
        }

        supabase.auth.getSession().then(({ data }) => {
            const utilisateur = data.session?.user;

            setConnecte(utilisateur ? utilisateur.email ?? utilisateur.user_metadata?.full_name ?? "" : null);
        });

        const { data: ecoute } = supabase.auth.onAuthStateChange((_evenement, session) => {
            setConnecte(session?.user ? session.user.email ?? "" : null);
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
            setMessage(currentLang.acceptRequired);

            return;
        }

        setMessage("");

        setLoading(true);

        try {
            const { error } = await signInWithGoogle();

            if (error) {
                setMessage(currentLang.googleError);

                setLoading(false);
            }
        }
        catch {
            setMessage(currentLang.googleError);

            setLoading(false);
        }
    }



    /* =====================================================
       CONNEXION FACEBOOK
    ===================================================== */

    async function handleFacebookLogin() {
        if (!accepte) {
            setMessage(currentLang.acceptRequired);

            return;
        }

        setMessage("");

        setLoading(true);

        try {
            const { error } = await signInWithFacebook();

            if (error) {
                setMessage(currentLang.facebookError);

                setLoading(false);
            }
        }
        catch {
            setMessage(currentLang.facebookError);

            setLoading(false);
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
                            alt="Connectéo"
                        />

                        <div className="auth-overlay"></div>

                    </div>


                    {/* TEXTE */}

                    <div className="auth-left-content">

                        <h1>
                            {currentLang.slogan}
                        </h1>

                        <div className="auth-footer-text">

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
                                {currentLang.welcome}
                            </h2>

                            <p>
                                {currentLang.description}
                            </p>

                        </div>



                        {/* DÉJÀ CONNECTÉ */}

                        {connecte !== null && (
                            <div className="auth-connecte">

                                <p>
                                    {currentLang.connectedAs}{" "}
                                    <strong>{connecte || currentLang.fallbackAccount}</strong>.
                                </p>

                                <div className="auth-connecte-actions">

                                    <button
                                        type="button"
                                        className="sso-button"
                                        onClick={() => { window.location.hash = "#pages/Home"; }}
                                    >
                                        {currentLang.backHome}
                                    </button>

                                    <button
                                        type="button"
                                        className="sso-button"
                                        onClick={handleSignOut}
                                        disabled={loading}
                                    >
                                        {currentLang.signOutLabel}
                                    </button>

                                </div>

                            </div>
                        )}


                        {/* BOUTONS DE CONNEXION */}

                        {connecte === null && (
                        <form className="auth-form">


                            {/* ACCORD CONFIDENTIALITÉ ET CONDITIONS */}

                            <label className="auth-consentement">

                                <input
                                    type="checkbox"
                                    checked={accepte}
                                    onChange={(e) => changerAccord(e.target.checked)}
                                />

                                <span>
                                    {currentLang.acceptPrefix}{" "}
                                    <a href="#pages/Confidentialite">{currentLang.privacyLink}</a>
                                    {" "}{currentLang.acceptAnd}{" "}
                                    <a href="#pages/ConditionsUtilisation">{currentLang.termsLink}</a>
                                    {" "}{currentLang.acceptSuffix}
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
                                    {currentLang.continueGoogle}
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
                                    {currentLang.continueFacebook}
                                </span>

                            </button>


                        </form>
                        )}



                        {/* MESSAGE D'ERREUR */}

                        {message && (
                            <div
                                className="auth-message"
                                role="alert"
                            >
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