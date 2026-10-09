import { useState, useEffect } from "react";
import {
    signInWithGoogle,
    signInWithFacebook
} from "../../services/auth";

import "./Auth.css";



function Auth()
{
    const [message, setMessage] = useState("");

    const [loading, setLoading] = useState(false);

    const [imageIndex, setImageIndex] = useState(0);


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

    useEffect(() =>
    {
        const interval = setInterval(() =>
        {
            setImageIndex((index) =>
            {
                return (index + 1) % images.length;
            });

        }, 10000);


        return () =>
        {
            clearInterval(interval);
        };

    }, []);



    /* =====================================================
       CONNEXION GOOGLE
    ===================================================== */

    async function handleGoogleLogin()
    {
        setMessage("");

        setLoading(true);


        const { error } =
            await signInWithGoogle();


        if (error)
        {
            setLoading(false);

            setMessage(
                "Impossible de se connecter avec Google."
            );
        }
    }

    /* =====================================================
       CONNEXION FACEBOOK
    ===================================================== */
    async function handleFacebookLogin()
    {
        setMessage("");
        setLoading(true);

        const { error } = await signInWithFacebook();

        if (error)
        {
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


                        {/* BOUTONS SSO */}

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
                                    Continuer avec Google
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
                                    Continuer avec Facebook
                                </span>

                            </button>


                        </form>


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