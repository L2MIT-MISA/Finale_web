"""Tests de l'assistant : python -m unittest discover -s tests -v   (aucun service externe requis)."""
from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import agent_ia
import api
import config
import conversation
import poi_osm
import recherche
import recherche_images
import resultat_json
from modeles import AnalyseTour, Lieu
from tests.fake_llm import FauxServeurIA


def lieu_osm(nom: str, categorie: str = "Restaurant", latitude=-18.91, longitude=47.52) -> Lieu:
    lieu = Lieu(nom=nom, niveau="site", categorie=categorie, description=categorie, adresse="Rue Test, Analakely",
                origine="osm", confiance=0.8, pertinence=0.9)
    lieu.definir_coordonnees(latitude, longitude, "precis")

    return lieu


def lieu_referentiel(nom: str) -> dict:
    return {"nom": nom, "niveau": "commune", "region": "Analamanga", "district": "Antananarivo Renivohitra",
            "description": "", "coordonnees": {"latitude": -18.9, "longitude": 47.5, "precision": "centroide"},
            "origine": "referentiel", "categorie": None, "images": []}


def reponse_pipeline(lieux: list[dict], statut="termine") -> dict:
    return {"id_resultat": "20260101-000000-test-abcd", "statut": statut, "requete": {"intention": "lieu"},
            "reponse": {"source_principale": "referentiel"}, "lieux": lieux, "sources": [], "avertissements": []}


class Base(unittest.TestCase):
    def setUp(self):
        self.dossier = Path(tempfile.mkdtemp())
        self.sauvegarde = {nom: getattr(config, nom) for nom in (
            "DOSSIER_RESULTATS", "AGENT_API_ACTIVE", "AGENT_API_CLE", "AGENT_API_URL", "AGENT_API_MODELE", "AGENT_LOCAL_ACTIF",
            "URL_OLLAMA", "IMAGES_ACTIVES", "POI_ACTIF", "LIMITE_REQUETES_PAR_MINUTE")}
        config.DOSSIER_RESULTATS = self.dossier
        config.IMAGES_ACTIVES = False
        config.AGENT_API_ACTIVE = config.AGENT_LOCAL_ACTIF = False       # par défaut : aucune IA (règles + réponses de secours)
        config.POI_ACTIF = True
        agent_ia.reinitialiser_les_pannes()
        conversation._sessions.clear()
        self.faux = None
        # aucun test n'appelle le vrai web : la recherche complète est simulée (vide) sauf si le test la remplace
        self.pipeline_par_defaut = mock.patch.object(recherche, "lancer_recherche", return_value=reponse_pipeline([]))
        self.pipeline_par_defaut.start()

    def tearDown(self):
        for nom, valeur in self.sauvegarde.items():
            setattr(config, nom, valeur)

        self.pipeline_par_defaut.stop()

        if self.faux:
            self.faux.arreter()

        shutil.rmtree(self.dossier, ignore_errors=True)

    def activer_ia(self, api=True, local=True):
        self.faux = FauxServeurIA()
        config.AGENT_API_URL = config.URL_OLLAMA = self.faux.url
        config.AGENT_API_CLE, config.AGENT_API_MODELE = "cle-test", "modele-test"
        config.AGENT_API_ACTIVE, config.AGENT_LOCAL_ACTIF = api, local

        return self.faux

    def tour(self, message, session=None, **options):
        return conversation.traiter_message(message, session, **options)


class TestAgentIA(Base):
    @unittest.skipUnless(agent_ia.LANGCHAIN_DISPONIBLE, "LangChain n'est pas installé dans cet environnement")
    def test_langchain_ollama_est_le_seul_fournisseur(self):
        from modeles import ReponseChat
        config.AGENT_LOCAL_ACTIF = True

        class Structure:
            def invoke(self, messages):
                return ReponseChat(message="Bonjour", suggestions=[])

        class Modele:
            def with_structured_output(self, classe, method):
                self.classe, self.method = classe, method
                return Structure()

        modele = Modele()
        with mock.patch.object(agent_ia, "_modele", return_value=modele), \
                mock.patch.object(agent_ia, "LANGCHAIN_DISPONIBLE", True):
            resultat = agent_ia.demander_json_detaille([{"role": "user", "content": "u"}], ReponseChat)

        self.assertEqual(resultat[0].message, "Bonjour")
        self.assertEqual(resultat[1].fournisseur, "langchain_ollama")
        self.assertEqual(modele.method, "json_schema")

    def test_tout_en_panne_renvoie_none(self):
        config.AGENT_LOCAL_ACTIF = False
        from modeles import ReponseChat
        self.assertIsNone(agent_ia.demander_json([{"role": "user", "content": "u"}], ReponseChat))
        self.assertIsNone(agent_ia.completer([{"role": "user", "content": "u"}]))

    def test_extraction_du_json_dans_un_texte_bruite(self):
        texte = 'Voici :\n```json\n{"a": "x } y", "b": {"c": 1}}\n``` merci'
        self.assertEqual(json.loads(agent_ia.extraire_objet_json(texte)), {"a": "x } y", "b": {"c": 1}})
        self.assertIsNone(agent_ia.extraire_objet_json("aucun objet"))
        self.assertEqual(agent_ia.nettoyer_texte_du_modele("<think>blabla</think>Salut"), "Salut")


class TestComprehension(Base):
    def test_extraction_du_lieu(self):
        cas = {
            "je veux chercher un des restaurant dans la ville d'antananarivo": "Antananarivo",
            "restaurant à Nosy Be svp": "Nosy Be",
            "une pharmacie près de Toamasina": "Toamasina",
            "hôtel à Antsirabe, merci": "Antsirabe",
            "trouve-moi un restaurant": None,
        }

        for texte, attendu in cas.items():
            self.assertEqual(conversation.extraire_le_lieu(texte), attendu, texte)

    def test_regles_sans_ia(self):
        session = conversation.Session(id="s-test1234")
        analyse, sure = conversation._analyser_par_regles("je veux un restaurant à Antananarivo", session)
        self.assertEqual((analyse.action, analyse.categorie, analyse.lieu, sure), ("chercher", "restaurant", "Antananarivo", True))
        analyse, _ = conversation._analyser_par_regles("une agence de voyage à Nosy Be", session)
        self.assertEqual(analyse.categorie, "agence de voyage")
        analyse, sure = conversation._analyser_par_regles("bonjour", session)
        self.assertEqual((analyse.action, sure), ("discuter", True))
        analyse, _ = conversation._analyser_par_regles("je cherche une pharmacie", session)
        self.assertEqual(analyse.action, "preciser")
        analyse, _ = conversation._analyser_par_regles("Voir sur la carte", session)
        self.assertEqual(analyse.action, "carte")

    def test_une_personne_ne_devient_jamais_un_lieu(self):
        session = conversation.Session(id="s-personne1")
        for question in ("Connais-tu Andry Rasoanaivo ?", "Qui est Andry Rasoanaivo ?",
                         "Non, je parle d'une personne, pas d'un lieu"):
            analyse, sure = conversation._analyser_par_regles(question, session)
            self.assertEqual((analyse.action, sure), ("discuter", True), question)

    def test_les_lieux_a_isalo_utilisent_les_sites_touristiques_osm(self):
        session = conversation.Session(id="s-isalo123")
        analyse, sure = conversation._analyser_par_regles("Je veux trouver des lieux à Isalo", session)
        self.assertEqual((analyse.action, analyse.categorie, analyse.lieu, sure),
                         ("chercher", "site touristique", "Isalo", True))

    def test_besoins_et_produits_compris_sans_ia(self):
        session = conversation.Session(id="s-test5678")
        analyse, sure = conversation._analyser_par_regles("j'ai faim", session)
        self.assertEqual((analyse.action, analyse.categorie, sure), ("preciser", "restaurant", True))
        analyse, sure = conversation._analyser_par_regles("j'ai faim, un endroit à Toamasina ?", session)
        self.assertEqual((analyse.action, analyse.categorie, analyse.lieu, sure), ("chercher", "restaurant", "Toamasina", True))
        analyse, sure = conversation._analyser_par_regles("ou se trouve le cultivateur de cacao", session)
        self.assertEqual((analyse.action, analyse.type_recherche, sure), ("chercher", "theme", True))

    def test_les_null_ecrits_en_texte_par_le_modele_sont_des_absences(self):
        analyse = AnalyseTour.model_validate({"action": "chercher", "type_recherche": "null", "categorie": "null",
                                              "lieu": "None", "requete": "j'ai faim"})
        self.assertEqual((analyse.type_recherche, analyse.categorie, analyse.lieu), (None, None, None))

    def test_une_conversation_passe_avant_une_tache_d_arriere_plan(self):
        creneau = agent_ia._CreneauLocal()
        self.assertTrue(creneau.prendre(True, 1))
        ordre = []

        def arriere_plan():
            if creneau.prendre(False, 5):
                ordre.append("arriere_plan")
                creneau.rendre()

        def conversation_():
            if creneau.prendre(True, 5):
                ordre.append("conversation")
                time.sleep(0.1)
                creneau.rendre()

        fils = [threading.Thread(target=arriere_plan)]
        fils[0].start()
        time.sleep(0.1)
        fils.append(threading.Thread(target=conversation_))
        fils[1].start()
        time.sleep(0.1)
        creneau.rendre()

        for fil in fils:
            fil.join()

        self.assertEqual(ordre, ["conversation", "arriere_plan"])
        self.assertTrue(creneau.prendre(True, 1))
        self.assertFalse(creneau.prendre(True, 0.2))      # occupé au-delà du budget : renoncement, pas d'attente infinie

    def test_detection_urgence_sans_faux_positifs(self):
        self.assertTrue(conversation.detecter_urgence("C'est une URGENCE !"))
        self.assertTrue(conversation.detecter_urgence("j'ai besoin de secours"))
        self.assertFalse(conversation.detecter_urgence("restaurant à Antananarivo"))
        self.assertFalse(conversation.detecter_urgence("une pharmacie pas chère"))


class TestConversation(Base):
    def simuler_recherche(self, etablissements=None, pipeline=None):
        return (mock.patch.object(poi_osm, "chercher_etablissements", return_value=(etablissements or [], "Antananarivo")),
                mock.patch.object(recherche, "lancer_recherche", return_value=pipeline or reponse_pipeline([])))

    def test_salutation_sans_ia_est_une_discussion_qui_garde_les_resultats(self):
        resultat = self.tour("Bonjour")
        self.assertEqual(resultat["statut"], "termine")
        self.assertEqual(resultat["lieux"], [])
        self.assertTrue(resultat["garder_resultats"])
        self.assertFalse(resultat["ouvrir_carte"])
        self.assertIn("assistant Connectéo", resultat["message"])
        self.assertTrue(resultat["suggestions"])

    def test_restaurant_donne_des_noms_exacts_et_ne_redirige_pas_vers_la_carte(self):
        restaurants = [lieu_osm("Restaurant Kanana"), lieu_osm("Chez Sucett's"), lieu_osm("Le Jasmin")]
        poi, pipeline = self.simuler_recherche(restaurants)

        with poi as poi_mock, pipeline as pipeline_mock:
            resultat = self.tour("je veux chercher un restaurant dans la ville d'Antananarivo")

        poi_mock.assert_called_once_with("restaurant", "Antananarivo")
        pipeline_mock.assert_not_called()                       # 3 établissements suffisent : pas besoin du web
        self.assertEqual([lieu["nom"] for lieu in resultat["lieux"]], ["Restaurant Kanana", "Chez Sucett's", "Le Jasmin"])
        self.assertFalse(resultat["ouvrir_carte"])
        self.assertFalse(resultat["garder_resultats"])
        self.assertIn("Restaurant Kanana", resultat["message"])
        self.assertIn("Voir sur la carte", resultat["suggestions"])
        self.assertIn("images", resultat["lieux"][0])
        self.assertIsNotNone(resultat["carte"])
        self.assertEqual(resultat["lieux"][0]["origine"], "osm")

    def test_peu_d_etablissements_le_web_complete_sans_doublon(self):
        web = {**lieu_referentiel("Restaurant Kanana"), "niveau": "site", "origine": "google"}
        web2 = {**lieu_referentiel("La Varangue"), "niveau": "site", "origine": "google"}
        poi, pipeline = self.simuler_recherche([lieu_osm("Restaurant Kanana")], reponse_pipeline([web, web2]))

        with poi, pipeline as pipeline_mock:
            resultat = self.tour("restaurant à Antananarivo")

        pipeline_mock.assert_called_once()
        self.assertEqual([lieu["nom"] for lieu in resultat["lieux"]], ["Restaurant Kanana", "La Varangue"])

    def test_etablissement_les_zones_administratives_ne_sont_pas_des_resultats(self):
        poi, pipeline = self.simuler_recherche([lieu_osm("Chalet des Roses")],
                                               reponse_pipeline([lieu_referentiel("ANTANANARIVO I"), lieu_referentiel("ANTANANARIVO II")]))

        with poi, pipeline:
            resultat = self.tour("un restaurant à Antananarivo")

        noms = [lieu["nom"] for lieu in resultat["lieux"]]
        self.assertEqual(noms, ["Chalet des Roses"])

    def test_zones_administratives_gardees_pour_une_recherche_de_lieu_avec_leur_localisation(self):
        poi, pipeline = self.simuler_recherche([], reponse_pipeline([lieu_referentiel("ANTANANARIVO I")]))

        with poi, pipeline:
            resultat = self.tour("Antananarivo")

        self.assertEqual(resultat["lieux"][0]["nom"], "ANTANANARIVO I")
        self.assertIn("district Antananarivo Renivohitra", resultat["lieux"][0]["adresse"])

    def test_precision_puis_reponse_de_ville(self):
        poi, pipeline = self.simuler_recherche([lieu_osm("Pharmacie Edness", "Pharmacie")])

        with poi as poi_mock, pipeline:
            premier = self.tour("je cherche une pharmacie")
            self.assertEqual(premier["lieux"], [])
            self.assertIn("Dans quelle ville", premier["message"])
            self.assertTrue(premier["garder_resultats"])
            second = self.tour("Toamasina", premier["session_id"])

        poi_mock.assert_called_once_with("pharmacie", "Toamasina")
        self.assertEqual(second["lieux"][0]["nom"], "Pharmacie Edness")
        self.assertEqual(second["session_id"], premier["session_id"])

    def test_suite_de_conversation_garde_la_ville(self):
        poi, pipeline = self.simuler_recherche([lieu_osm("Hôtel Colbert", "Hôtel")])

        with poi as poi_mock, pipeline:
            premier = self.tour("restaurant à Antananarivo")
            self.tour("et un hôtel ?", premier["session_id"])

        self.assertEqual(poi_mock.call_args_list[-1].args, ("hotel", "Antananarivo"))

    def test_la_carte_n_est_montree_que_sur_demande(self):
        poi, pipeline = self.simuler_recherche([lieu_osm("Restaurant Kanana")])

        with poi, pipeline:
            premier = self.tour("restaurant à Antananarivo")
            carte = self.tour("montre-moi sur la carte", premier["session_id"])

        self.assertTrue(carte["ouvrir_carte"])
        self.assertEqual(carte["lieux"][0]["nom"], "Restaurant Kanana")

    def test_carte_sans_resultat_precedent(self):
        resultat = self.tour("voir sur la carte")
        self.assertFalse(resultat["ouvrir_carte"])
        self.assertEqual(resultat["lieux"], [])
        self.assertIn("Dites-moi ce que vous cherchez", resultat["message"])

    def test_urgence_repond_tout_de_suite_avec_les_contacts(self):
        resultat = self.tour("c'est une urgence")
        self.assertEqual(resultat["statut"], "urgence")
        self.assertTrue(resultat["urgence"]["contacts"])
        self.assertIn("117", resultat["message"])

    def test_un_message_renvoye_avec_le_meme_requete_id_n_est_traite_qu_une_fois(self):
        poi, pipeline = self.simuler_recherche([lieu_osm("Restaurant Kanana")])

        with poi as poi_mock, pipeline:
            premier = self.tour("restaurant à Antananarivo", requete_id="req-123456")
            second = self.tour("restaurant à Antananarivo", premier["session_id"], requete_id="req-123456")

        self.assertEqual(premier["id_resultat"], second["id_resultat"])
        self.assertEqual(poi_mock.call_count, 1)
        self.assertEqual(len(conversation.lire_historique(premier["session_id"])), 2)

    def test_openstreetmap_en_panne_bascule_sur_le_web_et_previent(self):
        pipeline = reponse_pipeline([{**lieu_referentiel("Hôtel du Lac"), "niveau": "site", "origine": "google"}])

        with mock.patch.object(poi_osm, "chercher_etablissements", side_effect=poi_osm.PoiIndisponible("Overpass indisponible")), \
                mock.patch.object(recherche, "lancer_recherche", return_value=pipeline):
            resultat = self.tour("hôtel à Antsirabe")

        self.assertEqual(resultat["lieux"][0]["nom"], "Hôtel du Lac")
        self.assertTrue(any("OpenStreetMap" in a for a in resultat["avertissements"]))

    def test_aucun_resultat_est_dit_honnetement(self):
        poi, pipeline = self.simuler_recherche([])

        with poi, pipeline:
            resultat = self.tour("agence de voyage à Antananarivo")

        self.assertEqual(resultat["lieux"], [])
        self.assertIn("aucun résultat", resultat["message"])

    def test_erreur_interne_donne_un_message_poli_et_un_resultat_ecrit(self):
        with mock.patch.object(conversation, "analyser", side_effect=RuntimeError("boom")):
            resultat = self.tour("restaurant à Antananarivo")

        self.assertEqual(resultat["statut"], "erreur")
        self.assertIn("problème technique", resultat["message"])
        self.assertIsNotNone(resultat_json.lire_resultat(resultat["id_resultat"]))

    def test_message_vide_refuse(self):
        with self.assertRaises(ValueError):
            conversation.traiter_message("   \n ")

    def test_les_messages_trop_longs_sont_coupes_et_les_caracteres_de_controle_retires(self):
        self.assertEqual(len(conversation.nettoyer_message("a" * 5000)), config.CHAT_TAILLE_MAX_MESSAGE)
        self.assertEqual(conversation.nettoyer_message("a\x00b\x07 c"), "a b c")

    def test_attente_depassee_renvoie_en_cours_puis_le_resultat_est_lisible(self):
        def lent(*args, **kwargs):
            import time
            time.sleep(0.6)
            return ([lieu_osm("Restaurant Kanana")], "Antananarivo")

        with mock.patch.object(poi_osm, "chercher_etablissements", side_effect=lent), \
                mock.patch.object(recherche, "lancer_recherche", return_value=reponse_pipeline([])):
            provisoire = self.tour("restaurant à Antananarivo", attente_max=0.05)
            self.assertEqual(provisoire["statut"], "en_cours")
            final = conversation._attendre_le_resultat(provisoire["id_resultat"], 5)

        self.assertEqual(final["statut"], "termine")
        self.assertEqual(final["lieux"][0]["nom"], "Restaurant Kanana")


class TestConversationAvecIA(Base):
    def scenario(self, systeme, utilisateur):
        if "module de compréhension" in systeme:
            return json.dumps({"action": "chercher", "type_recherche": "etablissement", "categorie": "hôtel",
                               "lieu": "Nosy Be", "requete": "hôtel Nosy Be"})

        return json.dumps({"message": "J'ai trouvé deux adresses à Nosy Be, dont Nosy Be Hôtel. Souhaitez-vous des précisions ?",
                           "suggestions": ["Le plus proche de la plage ?", "Voir sur la carte", "Un restaurant ?", "quatrième"]})

    def test_comprehension_et_redaction_par_l_api(self):
        faux = self.activer_ia()
        faux.gestionnaire = self.scenario
        poi = mock.patch.object(poi_osm, "chercher_etablissements",
                                return_value=([lieu_osm("Nosy Be Hôtel", "Hôtel"), lieu_osm("Ravintsara", "Hôtel"),
                                               lieu_osm("Gerard et Francine", "Hôtel")], "Nosy Be"))

        with poi as poi_mock:
            resultat = self.tour("Je voudrais dormir près de la plage quelque part du côté de Nosy Be")

        poi_mock.assert_called_once_with("hotel", "Nosy Be")
        self.assertEqual(resultat["meta"]["fournisseur_ia"], "api")
        self.assertEqual(resultat["meta"]["comprehension"], "ia")
        self.assertIn("Nosy Be Hôtel", resultat["message"])
        self.assertEqual(len(resultat["suggestions"]), 3)         # coupées à 3
        bloc = faux.appels[-1]["corps"]["messages"][-1]["content"]
        self.assertIn("[1] Nosy Be Hôtel", bloc)                  # l'IA ne reçoit que les résultats réels
        self.assertIn("RÉSULTATS", bloc)

    def test_ia_indisponible_les_reponses_de_secours_prennent_le_relais(self):
        faux = self.activer_ia()
        faux.gestionnaire = lambda s, u: 503

        with mock.patch.object(poi_osm, "chercher_etablissements", return_value=([lieu_osm("Restaurant Kanana")], "Antananarivo")):
            resultat = self.tour("restaurant à Antananarivo")

        self.assertEqual(resultat["statut"], "termine")
        self.assertEqual(resultat["meta"]["fournisseur_ia"], "aucun")
        self.assertIn("Restaurant Kanana", resultat["message"])

    def test_message_de_l_ia_avec_un_lien_est_refuse(self):
        faux = self.activer_ia()
        faux.gestionnaire = lambda s, u: json.dumps({"message": "Allez sur http://exemple.com", "suggestions": []})

        with mock.patch.object(poi_osm, "chercher_etablissements", return_value=([lieu_osm("Restaurant Kanana")], "Antananarivo")):
            resultat = self.tour("restaurant à Antananarivo")

        self.assertNotIn("http", resultat["message"])


class TestImages(Base):
    def test_url_valides(self):
        self.assertEqual(recherche_images.url_image_valide("http://exemple.com/a.jpg"), "https://exemple.com/a.jpg")
        self.assertIsNone(recherche_images.url_image_valide("javascript:alert(1)"))
        self.assertIsNone(recherche_images.url_image_valide("data:image/png;base64,AAAA"))
        self.assertIsNone(recherche_images.url_image_valide("https://exemple.com/a b.jpg"))
        self.assertIsNone(recherche_images.url_image_valide(None))

    def test_une_image_doit_correspondre_au_nom(self):
        self.assertTrue(recherche_images.texte_correspond_au_nom("Restaurant Kanana", "Kanana - Antananarivo | Tripadvisor"))
        self.assertFalse(recherche_images.texte_correspond_au_nom("Restaurant Kanana", "Les 10 meilleurs restaurants à Antananarivo"))
        self.assertFalse(recherche_images.texte_correspond_au_nom("Restaurant", "Restaurant"))      # aucun mot distinctif

    def test_les_lieux_gardent_leurs_images_valides_et_l_echec_ne_bloque_pas(self):
        config.IMAGES_ACTIVES = True
        lieux = [{"nom": "A", "images": ["http://x.org/1.jpg", "javascript:1"]}, {"nom": "B", "images": []}]

        with mock.patch.object(recherche_images, "_chercher_pour_un_lieu", side_effect=RuntimeError("réseau")):
            recherche_images.enrichir_avec_images(lieux, delai_max=2)

        self.assertEqual(lieux[0]["images"], ["https://x.org/1.jpg"])
        self.assertEqual(lieux[0]["image"], "https://x.org/1.jpg")
        self.assertEqual(lieux[1]["images"], [])
        self.assertIsNone(lieux[1]["image"])


class TestAPI(Base):
    def setUp(self):
        super().setUp()
        self.client = TestClient(api.app)
        api._appels_recents.clear()

    def test_chat_puis_historique_puis_suppression(self):
        with mock.patch.object(poi_osm, "chercher_etablissements", return_value=([lieu_osm("Restaurant Kanana")], "Antananarivo")):
            reponse = self.client.post("/chat", json={"message": "restaurant à Antananarivo", "requete_id": "req-abcdef"})

        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertEqual(corps["statut"], "termine")
        self.assertEqual(self.client.get(f"/resultats/{corps['id_resultat']}").json()["message"], corps["message"])
        historique = self.client.get(f"/chat/{corps['session_id']}/historique").json()
        self.assertEqual([m["role"] for m in historique["messages"]], ["user", "assistant"])
        self.assertTrue(self.client.delete(f"/chat/{corps['session_id']}").json()["supprimee"])
        self.assertEqual(self.client.get(f"/chat/{corps['session_id']}/historique").status_code, 404)

    def test_messages_invalides(self):
        self.assertEqual(self.client.post("/chat", json={"message": ""}).status_code, 422)
        self.assertEqual(self.client.post("/chat", json={"message": "   "}).status_code, 400)
        self.assertEqual(self.client.post("/chat", json={}).status_code, 422)

    def test_limite_de_debit(self):
        config.LIMITE_REQUETES_PAR_MINUTE = 3
        codes = [self.client.post("/chat", json={"message": "bonjour"}).status_code for _ in range(5)]
        self.assertEqual(codes, [200, 200, 200, 429, 429])

    def test_cors_et_sante_rapide(self):
        reponse = self.client.options("/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                                                        "Access-Control-Request-Headers": "content-type"})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.headers["access-control-allow-origin"], "*")
        self.assertTrue(self.client.get("/sante/rapide").json()["ok"])

    def test_la_page_de_test_est_servie(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Assistant Connectéo", reponse.text)


if __name__ == "__main__":
    unittest.main()
