import "./Confidentialite.css";

export default function Confidentialite() {
  return (
    <main className="page-legale">
      <div className="page-legale__contenu">

        <h1>Politique de confidentialité</h1>

        <p className="page-legale__date">
          Dernière mise à jour : novembre 2026
        </p>

        <section>
          <h2>1. Introduction</h2>
          <p>
            Bienvenue sur Connectéo. Nous accordons une grande importance
            à la protection de vos données personnelles et au respect de
            votre vie privée.
          </p>
          <p>
            Cette politique explique comment vos informations peuvent être
            collectées, utilisées et protégées lorsque vous utilisez notre
            plateforme.
          </p>
        </section>

        <section>
          <h2>2. Données collectées</h2>
          <p>
            Selon les fonctionnalités que vous utilisez, Connectéo peut
            collecter certaines informations, notamment :
          </p>
          <ul>
            <li>Votre nom et votre prénom ;</li>
            <li>Votre adresse e-mail ;</li>
            <li>Les informations nécessaires à votre connexion ;</li>
            <li>Les informations que vous choisissez de communiquer sur la plateforme.</li>
          </ul>
        </section>

        <section>
          <h2>3. Utilisation des données</h2>
          <p>
            Les informations collectées peuvent être utilisées pour :
          </p>
          <ul>
            <li>Créer et gérer votre compte utilisateur ;</li>
            <li>Vous permettre d'accéder aux fonctionnalités de Connectéo ;</li>
            <li>Améliorer le fonctionnement de notre plateforme ;</li>
            <li>Répondre à vos demandes et questions.</li>
          </ul>
        </section>

        <section>
          <h2>4. Protection des données</h2>
          <p>
            Nous prenons des mesures raisonnables pour protéger les
            informations des utilisateurs contre les accès non autorisés,
            la perte ou la divulgation.
          </p>
        </section>

        <section>
          <h2>5. Partage des données</h2>
          <p>
            Les données personnelles ne doivent être partagées qu'avec
            les services nécessaires au fonctionnement de Connectéo,
            conformément aux fonctionnalités réellement utilisées et
            aux obligations applicables.
          </p>
        </section>

        <section>
          <h2>6. Vos droits</h2>
          <p>
            Vous pouvez demander des informations sur vos données
            personnelles, leur rectification ou leur suppression en
            contactant l'équipe Connectéo.
          </p>
        </section>

        <section>
          <h2>7. Contact</h2>
          <p>
            Pour toute question concernant cette politique, contactez
            notre équipe à l'adresse suivante :
          </p>
          <p>
            <strong>Adresse e-mail :</strong> <a href="#">connecteo.contact@gmail.com</a> 
          </p>
        </section>

      </div>
    </main>
  );
}