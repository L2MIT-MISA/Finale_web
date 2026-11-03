import { VERSION_CONFIDENTIALITE } from "../../services/auth";
import "./Confidentialite.css";

// Adresse à laquelle exercer ses droits (accès, rectification, suppression) : à renseigner par l'équipe.
const CONTACT_CONFIDENTIALITE = "";

function dateLisible(iso: string) {
  const [annee, mois, jour] = iso.split("-");
  return `${jour}/${mois}/${annee}`;
}

function Confidentialite() {
  return (
    <main className="conf-page">
      <article className="conf-article">
        <h1>Politique de confidentialité</h1>
        <p className="conf-date">Dernière mise à jour : {dateLisible(VERSION_CONFIDENTIALITE)}</p>

        <p>
          Cette page explique quelles données Connectéo utilise, pourquoi, avec qui elles sont partagées et combien de
          temps elles sont conservées. En vous connectant, vous acceptez ce fonctionnement.
        </p>

        <h2>1. Connexion avec Google ou Facebook</h2>
        <p>
          La connexion passe par Google ou Facebook, puis par notre service d'authentification Supabase. Nous recevons
          seulement ce que ces services transmettent pour ouvrir votre compte : votre identifiant, votre adresse e-mail,
          votre nom et votre photo de profil. Nous ne recevons jamais votre mot de passe.
        </p>
        <p>
          Ces informations servent à vous identifier et à afficher votre compte. La session est gardée dans votre
          navigateur jusqu'à la déconnexion.
        </p>

        <h2>2. Assistant et recherche</h2>
        <p>
          Vos messages à l'assistant sont envoyés à notre serveur pour être compris et recevoir une réponse. Pour
          rédiger cette réponse, ils peuvent être transmis à des services d'intelligence artificielle : Google
          (Gemini), Groq et OpenRouter. Avant l'envoi, les adresses e-mail, les numéros de téléphone ou de carte et
          les adresses IP écrits dans vos messages sont masqués automatiquement.
        </p>
        <p>
          Avec l'offre gratuite de Google Gemini, Google peut utiliser les contenus reçus pour améliorer ses produits.
          N'écrivez donc pas d'informations personnelles ou sensibles dans l'assistant.
        </p>
        <p>
          Pour répondre aux questions générales, la question est aussi envoyée à des moteurs de recherche (Tavily,
          DuckDuckGo, Wikipédia), et des pages web publiques sont lues. Pour trouver des lieux, le nom du lieu ou de la
          ville est envoyé aux services OpenStreetMap (Nominatim, Overpass, Photon). Chacun de ces services applique
          ses propres conditions d'utilisation.
        </p>

        <h2>3. Carte, itinéraire et position</h2>
        <p>
          La carte est affichée par Google Maps : Google reçoit les informations techniques nécessaires à son
          affichage, comme votre adresse IP. Votre position n'est utilisée que si vous la demandez pour un itinéraire,
          avec l'accord de votre navigateur. Elle est alors envoyée au service de calcul d'itinéraire
          routing.openstreetmap.de, et les adresses saisies au service nominatim.openstreetmap.org. Nous ne
          conservons pas votre position.
        </p>
        <p>
          Les photos des lieux et des réponses sont chargées directement depuis leurs sites d'origine (par exemple
          Wikimedia, des sites d'établissements ou des sites d'actualité), qui reçoivent alors votre adresse IP.
        </p>

        <h2>4. Durée de conservation</h2>
        <ul>
          <li>L'historique de la discussion est gardé dans la mémoire du serveur et effacé après 2 heures sans nouveau message, ou au redémarrage du service.</li>
          <li>Chaque réponse, avec le message qui l'a demandée, est enregistrée sur le serveur et supprimée automatiquement après 7 jours.</li>
          <li>Votre adresse IP est gardée en mémoire pour limiter le nombre de messages par minute, sans être enregistrée sur disque à cette fin. Comme pour tout site web, les journaux techniques du serveur enregistrent l'adresse IP et l'heure des requêtes.</li>
          <li>Votre compte est conservé jusqu'à ce que vous demandiez sa suppression.</li>
        </ul>

        <h2>5. Données gardées dans votre navigateur</h2>
        <p>
          Le site enregistre dans votre navigateur votre langue, votre session de connexion, votre accord à cette
          politique, l'identifiant de votre discussion et votre dernière recherche. Vous pouvez les effacer à tout
          moment depuis les réglages de votre navigateur.
        </p>

        <h2>6. Ce que nous ne faisons pas</h2>
        <p>
          Connectéo ne vend pas vos données, n'affiche pas de publicité et ne publie jamais vos messages.
        </p>

        <h2>7. Vos droits</h2>
        <p>
          Vous pouvez demander l'accès à vos données, leur correction ou leur suppression, y compris celle de votre
          compte, en écrivant à :{" "}
          {CONTACT_CONFIDENTIALITE ? (
            <a href={`mailto:${CONTACT_CONFIDENTIALITE}`}>{CONTACT_CONFIDENTIALITE}</a>
          ) : (
            <strong>adresse de contact à compléter par l'équipe Connectéo</strong>
          )}
          .
        </p>

        <p className="conf-retour">
          <a href="#pages/Auth">Retour à la connexion</a>
          {" · "}
          <a href="#pages/Home">Retour à l'accueil</a>
        </p>
      </article>
    </main>
  );
}

export default Confidentialite;
