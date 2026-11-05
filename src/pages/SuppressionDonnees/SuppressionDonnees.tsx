import "./SuppressionDonnees.css";

export default function SuppressionDonnees() {
  return (
    <main className="page-legale">
      <div className="page-legale__contenu">

        <h1>Suppression des données personnelles</h1>

        <p className="page-legale__date">
          Dernière mise à jour : novembre 2026
        </p>

        <section>
          <h2>1. Votre droit à la suppression</h2>
          <p>
            Chez Connectéo, nous respectons votre vie privée.
            Vous pouvez demander la suppression de votre compte
            et des données personnelles qui y sont associées.
          </p>
        </section>

        <section>
          <h2>2. Comment demander la suppression ?</h2>
          <p>
            Pour demander la suppression de vos données, veuillez
            suivre les étapes suivantes :
          </p>

          <ol>
            <li>Envoyez un e-mail à notre équipe Connectéo.</li>
            <li>
              Indiquez que vous souhaitez supprimer votre compte
              et vos données personnelles.
            </li>
            <li>
              Précisez l'adresse e-mail associée à votre compte
              afin que nous puissions identifier votre demande.
            </li>
            <li>
              Notre équipe vous répondra pour vous informer du
              traitement de votre demande.
            </li>
          </ol>
        </section>

        <section>
          <h2>3. Adresse de contact</h2>
          <p>
            Vous pouvez envoyer votre demande à l'adresse suivante :
          </p>

          <p className="suppression-email">
            <a href="#">connecteo.contact@gmail.com</a>
          </p>

          <p>
            Objet du message : Demande de suppression de mes données
          </p>
        </section>

        <section>
          <h2>4. Traitement de votre demande</h2>
          <p>
            Après vérification de votre demande, notre équipe
            procédera à la suppression des données concernées,
            sous réserve des obligations légales éventuelles
            de conservation.
          </p>
          <p>
            Nous vous informerons lorsque votre demande aura été
            traitée.
          </p>
        </section>

        <section>
          <h2>5. Suppression des données liées à Facebook</h2>
          <p>
            Si vous avez utilisé Facebook pour vous connecter
            à Connectéo, vous pouvez également nous contacter
            pour demander la suppression des données associées
            à cette connexion.
          </p>
        </section>

        <section>
          <h2>6. Besoin d'aide ?</h2>
          <p>
            Pour toute question concernant la suppression de
            vos données, contactez notre équipe Connectéo.
          </p>
        </section>

      </div>
    </main>
  );
}