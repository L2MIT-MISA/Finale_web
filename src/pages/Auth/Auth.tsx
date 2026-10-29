import { useState, useEffect } from "react";

import { useLang } from "../../i18n/LanguageContext";

import {
    signInWithGoogle,
    signInWithFacebook
} from "../../services/auth";

import "./Auth.css";


function Auth() {
    const { lang } = useLang();

    const [message, setMessage] = useState("");

    const [loading, setLoading] = useState(false);

    const [imageIndex, setImageIndex] = useState(0);


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
            facebookError: "Impossible de se connecter avec Facebook."
        },

        MG: {
            slogan: "Tsy tokony ho sarotra ny mahita ny tolotra mety.",
            welcome: "Faly miarahaba anao indray",
            description: "Midira ao amin'ny Connectéo.",
            continueGoogle: "Hanohy amin'ny Google",
            continueFacebook: "Hanohy amin'ny Facebook",
            googleError: "Tsy afaka miditra amin'ny alalan'ny Google.",
            facebookError: "Tsy afaka miditra amin'ny alalan'ny Facebook."
        },

        EN: {
            slogan: "Finding the right service should never be complicated.",
            welcome: "Welcome back",
            description: "Sign in to your Connectéo account.",
            continueGoogle: "Continue with Google",
            continueFacebook: "Continue with Facebook",
            googleError: "Unable to sign in with Google.",
            facebookError: "Unable to sign in with Facebook."
        }
    };


    /* =====================================================
       LANGUE ACTUELLE
    ===================================================== */

    const currentLang = translations[lang] || translations.FR;


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



                        {/* BOUTONS DE CONNEXION */}

                        <form className="auth-form">


                            {/* GOOGLE */}

                            <button
                                type="button"
                                className="sso-button"
                                onClick={handleGoogleLogin}
                                disabled={loading}
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
                                disabled={loading}
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