"""Tests des fournisseurs d'IA (Gemini, puis Groq en secours), des quotas, des replis, des sources web et des images.

Aucun appel réseau : les modèles LangChain et les services web sont simulés.
"""
from __future__ import annotations

import os

os.environ["CONNECTEO_SANS_FICHIER_ENV"] = "1"

import logging
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi.testclient import TestClient
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

import agent_ia
import api
import config
import modele_ia
import recherche
import recherche_images
import recherche_web
from modeles import ReponseChat
from tests.test_chat import Base

CHERCHER_RESULTATS_WEB = recherche_web.chercher_resultats_web          # la vraie fonction, avant toute simulation

RESULTATS_WEB = [
    {"titre": "Andry Rasoanaivo — Université d'Antananarivo", "url": "https://exemple.mg/andry",
     "extrait": "Andry Rasoanaivo est enseignant-chercheur en informatique.", "fournisseur": "duckduckgo"},
    {"titre": "Andry Rasoanaivo (musicien)", "url": "https://exemple.org/musique",
     "extrait": "Un homonyme, musicien malgache.", "fournisseur": "duckduckgo"},
]


class ErreurHTTP(Exception):
    def __init__(self, code: int, attente: str | None = None):
        super().__init__(f"HTTP {code} cle-secrete-ne-doit-pas-sortir")
        self.status_code = code
        self.response = SimpleNamespace(headers={"retry-after": attente} if attente else {})


class FauxModeleAvecOutils(BaseChatModel):
    """Modèle de discussion simulé : renvoie les réponses prévues, une par appel (ou lève l'exception prévue)."""
    reponses: list
    appels: int = 0

    @property
    def _llm_type(self) -> str:
        return "faux-modele"

    def bind_tools(self, outils, **options):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **options):
        reponse = self.reponses[min(self.appels, len(self.reponses) - 1)]
        self.appels += 1

        if isinstance(reponse, Exception):
            raise reponse

        return ChatResult(generations=[ChatGeneration(message=reponse)])


class FauxStructure:
    def __init__(self, comportement):
        self.comportement = comportement

    def invoke(self, messages):
        if isinstance(self.comportement, Exception):
            raise self.comportement

        if callable(self.comportement):
            return self.comportement()

        return self.comportement


class FauxModeleStructure:
    def __init__(self, comportement):
        self.comportement = comportement

    def with_structured_output(self, classe, method, **options):
        return FauxStructure(self.comportement)


class BaseFournisseurs(Base):
    def setUp(self):
        super().setUp()
        config.AGENT_FOURNISSEUR, config.AGENT_API_CLE, config.MODELE_REDACTION = "gemini", "cle-gemini-test", "gemini-2.5-flash"
        config.AGENT_SECOURS_FOURNISSEUR, config.AGENT_SECOURS_CLE = "groq", "cle-groq-test"
        config.AGENT_SECOURS_MODELE = "llama-3.3-70b-versatile"
        config.AGENT_APPELS_PAR_MINUTE, config.AGENT_APPELS_PAR_JOUR = 10, 200

    def modeles(self, **par_fournisseur):
        """Remplace la construction du modèle : un comportement simulé par fournisseur."""
        appels = []

        def construire(fournisseur, max_tokens, temperature, delai):
            appels.append(fournisseur.nom)
            return par_fournisseur[fournisseur.nom]

        return mock.patch.object(agent_ia, "_modele", side_effect=construire), appels


class TestConfigurationEtRepli(BaseFournisseurs):
    def test_sans_cle_aucun_fournisseur_et_repli_immediat(self):
        config.AGENT_API_CLE = config.AGENT_SECOURS_CLE = ""
        debut = time.monotonic()

        self.assertEqual(agent_ia.fournisseurs_configures(), [])
        self.assertIsNone(agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat))
        self.assertIsNone(agent_ia.completer([{"role": "user", "content": "x"}]))
        self.assertLess(time.monotonic() - debut, 0.5)
        self.assertEqual(agent_ia.etat_public(), {"ia": "desactivee"})

    def test_ordre_principal_puis_secours_et_fournisseur_inconnu_ignore(self):
        self.assertEqual(agent_ia.fournisseurs_configures(), ["gemini", "groq"])
        config.AGENT_FOURNISSEUR = "inconnu"
        self.assertEqual(agent_ia.fournisseurs_configures(), ["groq"])

    def test_429_bascule_sur_groq_et_ecarte_gemini(self):
        remplacement, appels = self.modeles(gemini=FauxModeleStructure(ErreurHTTP(429, "30")),
                                            groq=FauxModeleStructure(ReponseChat(message="Réponse Groq")))

        with remplacement:
            objet, informations = agent_ia.demander_json_detaille([{"role": "user", "content": "x"}], ReponseChat)
            agent_ia.demander_json_detaille([{"role": "user", "content": "x"}], ReponseChat)

        self.assertEqual((objet.message, informations.fournisseur), ("Réponse Groq", "groq"))
        self.assertEqual(appels, ["gemini", "groq", "groq"])          # Gemini écarté après son 429
        etat = agent_ia._etat(agent_ia.lister_les_fournisseurs()[0])
        self.assertGreater(etat.en_panne_jusqua - time.monotonic(), 20)

    def test_tous_limites_renvoie_none_sans_bloquer(self):
        remplacement, _ = self.modeles(gemini=FauxModeleStructure(ErreurHTTP(429)), groq=FauxModeleStructure(ErreurHTTP(429)))
        debut = time.monotonic()

        with remplacement:
            self.assertIsNone(agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat))

        self.assertLess(time.monotonic() - debut, 1)
        self.assertEqual(agent_ia.etat_public()["ia"], "indisponible")

    def test_un_principal_lent_laisse_du_temps_au_secours(self):
        lent = FauxModeleStructure(lambda: time.sleep(9) or ReponseChat(message="trop tard"))
        remplacement, appels = self.modeles(gemini=lent, groq=FauxModeleStructure(ReponseChat(message="Groq à temps")))
        debut = time.monotonic()

        with remplacement:
            objet = agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat, delai_max=12)

        self.assertEqual(objet.message, "Groq à temps")
        self.assertLess(time.monotonic() - debut, 8.5)                  # 60 % de 12 s, puis Groq

    def test_quota_journalier_gemini_ecarte_le_modele_jusqu_au_renouvellement(self):
        erreur = ErreurHTTP(429)
        erreur.args = ("429 RESOURCE_EXHAUSTED ... limit: 20 ... Please retry in 23h32m14.4s.",)
        self.assertAlmostEqual(agent_ia.classer_erreur(erreur)[1], 23 * 3600 + 32 * 60 + 14.4, places=1)

    def test_plusieurs_modeles_par_fournisseur_forment_une_chaine(self):
        config.MODELE_REDACTION = "gemini-3.6-flash, gemini-3.5-flash-lite"
        config.AGENT_SECOURS_MODELE = "openai/gpt-oss-120b,qwen/qwen3.8-27b"
        self.assertEqual([(f.nom, f.modele) for f in agent_ia.lister_les_fournisseurs()],
                         [("gemini", "gemini-3.6-flash"), ("gemini", "gemini-3.5-flash-lite"),
                          ("groq", "openai/gpt-oss-120b"), ("groq", "qwen/qwen3.8-27b")])
        epuise = ErreurHTTP(429)
        epuise.args = ("RESOURCE_EXHAUSTED Please retry in 20h",)
        remplacement, appels = self.modeles(gemini=FauxModeleStructure(epuise), groq=FauxModeleStructure(ReponseChat(message="ok")))

        with remplacement:
            self.assertEqual(agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat).message, "ok")
            agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat)

        self.assertEqual(appels, ["gemini", "gemini", "groq", "groq"])   # les deux Gemini épuisés ne sont plus réessayés

    def test_chaine_de_quatre_fournisseurs_avec_leurs_propres_cles(self):
        config.AGENT_CHAINE = ["gemini", "groq", "cerebras", "openrouter", "mistral"]
        config.CLES_API = {"cerebras": "cle-cerebras", "openrouter": "cle-openrouter"}        # mistral sans clé : ignoré
        config.MODELES_API = {"openrouter": "google/gemma-4-31b-it:free"}            # modèle choisi dans .env
        chaine = [(f.nom, f.modele, f.cle) for f in agent_ia.lister_les_fournisseurs()]

        self.assertEqual([nom for nom, _, _ in chaine], ["gemini", "groq", "cerebras", "cerebras", "openrouter"])
        self.assertIn(("cerebras", "gpt-oss-120b", "cle-cerebras"), chaine)
        self.assertIn(("openrouter", "google/gemma-4-31b-it:free", "cle-openrouter"), chaine)
        self.assertIn(("groq", "llama-3.3-70b-versatile", "cle-groq-test"), chaine)   # anciennes variables du secours

    def test_modeles_compatibles_openai_et_mistral_construits_sans_reseau(self):
        cerebras = agent_ia._modele(agent_ia.Fournisseur("cerebras", "gpt-oss-120b", "cle-c"), 100, 0.3, 8)
        openrouter = agent_ia._modele(agent_ia.Fournisseur("openrouter", "google/gemma-4-31b-it:free", "cle-o"), 100, 0.3, 8)
        mistral = agent_ia._modele(agent_ia.Fournisseur("mistral", "mistral-small-latest", "cle-m"), 100, 0.3, 8)

        self.assertEqual((cerebras.openai_api_base, cerebras.max_retries, cerebras.openai_api_key.get_secret_value()),
                         ("https://api.cerebras.ai/v1", 0, "cle-c"))
        self.assertEqual(openrouter.openai_api_base, "https://openrouter.ai/api/v1")
        self.assertEqual(openrouter.default_headers["X-Title"], "Connecteo")
        self.assertEqual((mistral.max_retries, mistral.mistral_api_key.get_secret_value()), (0, "cle-m"))

    def test_bascule_jusqu_au_quatrieme_fournisseur(self):
        config.AGENT_CHAINE = ["gemini", "groq", "cerebras", "openrouter"]
        config.CLES_API = {"cerebras": "cle-c", "openrouter": "cle-o"}
        config.MODELE_REDACTION, config.AGENT_SECOURS_MODELE = "gemini-3.6-flash", "openai/gpt-oss-120b"
        config.MODELES_API = {"cerebras": "gpt-oss-120b", "openrouter": "google/gemma-4-31b-it:free"}
        remplacement, appels = self.modeles(gemini=FauxModeleStructure(ErreurHTTP(429)), groq=FauxModeleStructure(ErreurHTTP(503)),
                                            cerebras=FauxModeleStructure(ErreurHTTP(429)),
                                            openrouter=FauxModeleStructure(ReponseChat(message="OpenRouter répond")))

        with remplacement:
            objet, informations = agent_ia.demander_json_detaille([{"role": "user", "content": "x"}], ReponseChat)

        self.assertEqual((objet.message, informations.fournisseur), ("OpenRouter répond", "openrouter"))
        self.assertEqual(appels, ["gemini", "groq", "cerebras", "openrouter"])

    def test_un_fournisseur_trop_lent_n_essaie_pas_ses_autres_modeles(self):
        config.MODELE_REDACTION = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
        lent = FauxModeleStructure(lambda: time.sleep(8) or ReponseChat(message="trop tard"))
        remplacement, appels = self.modeles(gemini=lent, groq=FauxModeleStructure(ReponseChat(message="Groq")))

        with remplacement:
            objet = agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat, delai_max=10)

        self.assertEqual(objet.message, "Groq")
        self.assertEqual(appels, ["gemini", "groq"])                    # le second Gemini n'est pas essayé

    def test_gemini_recoit_toujours_un_delai_client_d_au_moins_10_s(self):
        modele = agent_ia._modele(agent_ia.Fournisseur("gemini", "gemini-3.6-flash", "cle-test"), 100, 0.3, 4)
        self.assertEqual(modele.timeout, 10.0)
        self.assertEqual(modele.max_output_tokens, agent_ia.PLANCHER_TOKENS_DE_SORTIE)

    def test_groq_gpt_oss_raisonne_peu(self):
        modele = agent_ia._modele(agent_ia.Fournisseur("groq", "openai/gpt-oss-120b", "cle-test"), 100, 0.3, 4)
        self.assertEqual((modele.reasoning_effort, modele.request_timeout), ("low", 4))

    def test_429_de_mistral_lu_dans_la_reponse_httpx(self):
        erreur = RuntimeError("Error response 429 while fetching https://api.mistral.ai/v1/chat/completions")
        erreur.response = SimpleNamespace(status_code=429, headers={})
        self.assertEqual(agent_ia.classer_erreur(erreur)[0], "limite_du_fournisseur")

    def test_modele_introuvable_et_surcharge_sont_classes(self):
        self.assertEqual(agent_ia.classer_erreur(ErreurHTTP(404))[0], "modele_introuvable")
        self.assertEqual(agent_ia.classer_erreur(ErreurHTTP(503))[0], "fournisseur_surcharge")
        self.assertEqual(agent_ia.classer_erreur(ErreurHTTP(429, "12")), ("limite_du_fournisseur", 12.0))

    def test_cle_refusee_ecarte_le_fournisseur_longtemps(self):
        remplacement, _ = self.modeles(gemini=FauxModeleStructure(ErreurHTTP(401)), groq=FauxModeleStructure(ReponseChat(message="ok")))

        with remplacement:
            agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat)

        etat = agent_ia._etat(agent_ia.lister_les_fournisseurs()[0])
        self.assertGreater(etat.en_panne_jusqua - time.monotonic(), 500)

    def test_delai_depasse_rend_la_main_dans_le_budget(self):
        config.AGENT_SECOURS_FOURNISSEUR = "off"
        lent = FauxModeleStructure(lambda: time.sleep(3) or ReponseChat(message="trop tard"))
        remplacement, _ = self.modeles(gemini=lent)
        debut = time.monotonic()

        with remplacement:
            self.assertIsNone(agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat, delai_max=1.2))

        self.assertLess(time.monotonic() - debut, 2.5)
        self.assertFalse(agent_ia._etat(agent_ia.lister_les_fournisseurs()[0]).est_en_panne())   # notre budget, pas sa faute

    def test_sortie_json_invalide_passe_au_secours_sans_panne(self):
        remplacement, _ = self.modeles(gemini=FauxModeleStructure(OutputParserException("JSON invalide")),
                                       groq=FauxModeleStructure({"message": "Réparé par Groq", "suggestions": []}))

        with remplacement:
            objet = agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat)

        self.assertEqual(objet.message, "Réparé par Groq")
        self.assertFalse(agent_ia._etat(agent_ia.lister_les_fournisseurs()[0]).est_en_panne())

    def test_plafond_par_minute_protege_le_quota(self):
        config.AGENT_SECOURS_FOURNISSEUR = "off"
        config.AGENT_APPELS_PAR_MINUTE = 2
        remplacement, appels = self.modeles(gemini=FauxModeleStructure(ReponseChat(message="ok")))

        with remplacement:
            resultats = [agent_ia.demander_json([{"role": "user", "content": "x"}], ReponseChat) for _ in range(3)]

        self.assertEqual([resultat is not None for resultat in resultats], [True, True, False])
        self.assertEqual(len(appels), 2)

    def test_une_tache_d_arriere_plan_laisse_une_marge_aux_conversations(self):
        etat = agent_ia.EtatFournisseur()
        self.assertTrue(etat.reserver(prioritaire=True, par_minute=2, par_jour=100))
        self.assertFalse(etat.reserver(prioritaire=False, par_minute=2, par_jour=100))
        self.assertTrue(etat.reserver(prioritaire=True, par_minute=2, par_jour=100))

    def test_la_cle_et_les_messages_ne_sont_jamais_journalises(self):
        remplacement, _ = self.modeles(gemini=FauxModeleStructure(ErreurHTTP(429)), groq=FauxModeleStructure(ErreurHTTP(500)))

        with remplacement, self.assertLogs("agent_ia", level=logging.INFO) as journaux:
            agent_ia.demander_json([{"role": "user", "content": "message très privé"}], ReponseChat)

        texte = "\n".join(journaux.output)
        self.assertNotIn("cle-secrete", texte)
        self.assertNotIn("cle-gemini-test", texte)
        self.assertNotIn("message très privé", texte)

    def test_donnees_personnelles_masquees(self):
        texte = agent_ia.proteger_les_donnees_personnelles("Écrivez à rakoto@exemple.mg ou au +261 34 12 345 67, IP 10.0.0.1")
        self.assertNotIn("rakoto@exemple.mg", texte)
        self.assertNotIn("345 67", texte)
        self.assertNotIn("10.0.0.1", texte)


class TestAgentAvecOutils(BaseFournisseurs):
    def test_l_agent_cherche_sur_le_web_et_renvoie_ses_sources(self):
        modele = FauxModeleAvecOutils(reponses=[
            AIMessage(content="", tool_calls=[{"name": "rechercher_sur_le_web", "args": {"question": "Andry Rasoanaivo"},
                                               "id": "appel-1", "type": "tool_call"}]),
            AIMessage(content="Andry Rasoanaivo est enseignant-chercheur en informatique [1]."),
        ])
        remplacement, _ = self.modeles(gemini=modele)

        with remplacement, mock.patch.object(recherche_web, "chercher_resultats_web", return_value=RESULTATS_WEB) as web:
            reponse = agent_ia.completer([{"role": "system", "content": "s"}, {"role": "user", "content": "Qui est Andry Rasoanaivo ?"}])

        web.assert_called_once()
        self.assertEqual(reponse.fournisseur, "gemini")
        self.assertIn("enseignant-chercheur", reponse.texte)
        self.assertEqual([source["url"] for source in reponse.sources], [r["url"] for r in RESULTATS_WEB])
        self.assertEqual(modele.appels, 2)

    def test_chaque_appel_du_modele_par_l_agent_consomme_le_quota(self):
        config.AGENT_SECOURS_FOURNISSEUR = "off"
        config.AGENT_APPELS_PAR_MINUTE = 1          # l'agent a besoin de deux appels : le second dépasse le quota
        modele = FauxModeleAvecOutils(reponses=[
            AIMessage(content="", tool_calls=[{"name": "rechercher_sur_le_web", "args": {"question": "x"}, "id": "a", "type": "tool_call"}]),
            AIMessage(content="fin"),
        ])
        remplacement, _ = self.modeles(gemini=modele)

        with remplacement:
            self.assertIsNone(agent_ia.completer([{"role": "user", "content": "x"}]))

        self.assertEqual(modele.appels, 1)

    def test_lire_une_page_refuse_une_adresse_non_trouvee(self):
        outils = {outil.name: outil for outil in agent_ia.construire_outils_web(["https://exemple.mg/andry"])}

        with mock.patch.object(recherche_web, "lire_page_publique", return_value="texte de la page") as lecture:
            refus = outils["lire_une_page"].invoke({"url": "http://127.0.0.1:8000/sante"})
            accord = outils["lire_une_page"].invoke({"url": "https://exemple.mg/andry"})

        self.assertIn("refusée", refus)
        self.assertIn("texte de la page", accord)
        lecture.assert_called_once_with("https://exemple.mg/andry", agent_ia.DELAI_OUTIL_WEB_EN_SECONDES)

    def test_titres_colles_par_le_moteur_sont_separes(self):
        self.assertEqual(recherche_web.nettoyer_titre("Andry RASOANAIVO - Expert AI, Cybersecurity | LinkedInAndry Rasoanaivo - Google Scholar"),
                         "Andry RASOANAIVO - Expert AI, Cybersecurity | LinkedIn")
        self.assertEqual(recherche_web.nettoyer_titre("CTO | Mobile Senior & Fullstack ...Andry RASOANAIVO10+ profils"),
                         "CTO | Mobile Senior & Fullstack ...")
        self.assertEqual(recherche_web.nettoyer_titre("Rasoanaivo Andry Jimmy - Facebook"), "Rasoanaivo Andry Jimmy - Facebook")
        self.assertEqual(recherche_web.nettoyer_titre("Université d'Antananarivo"), "Université d'Antananarivo")

    def test_seuls_les_resultats_pertinents_sont_gardes(self):
        bruts = [{"title": "Marie Lydia Toto Raharimalala", "snippet": "Anjara Rasoanaivo, Femmes parlementaires",
                  "link": "https://fr.wikipedia.org/wiki/Marie_Lydia"},
                 {"title": "Andry RASOANAIVO - Expert AI | LinkedIn", "snippet": "",
                  "link": "https://mg.linkedin.com/in/andry-rasoanaivo"}]

        with mock.patch.dict(recherche_web.FOURNISSEURS, {"wikipedia": lambda q, n: bruts}, clear=True), \
                mock.patch.object(config, "ORDRE_FOURNISSEURS_RECHERCHE", ["wikipedia"]):
            resultats = CHERCHER_RESULTATS_WEB("Andry Rasoanaivo", 5, 2)

        self.assertEqual([resultat["url"] for resultat in resultats], ["https://mg.linkedin.com/in/andry-rasoanaivo"])

    def test_un_moteur_lent_ne_retarde_pas_un_moteur_rapide(self):
        rapide = [{"title": "Andry Rasoanaivo", "snippet": "", "link": "https://exemple.mg/a"}]
        fournisseurs = {"lent": lambda q, n: time.sleep(3) or [], "rapide": lambda q, n: rapide}
        debut = time.monotonic()

        with mock.patch.dict(recherche_web.FOURNISSEURS, fournisseurs, clear=True), \
                mock.patch.object(config, "ORDRE_FOURNISSEURS_RECHERCHE", ["lent", "rapide"]):
            resultats = CHERCHER_RESULTATS_WEB("Andry Rasoanaivo", 5, 1)

        self.assertLess(time.monotonic() - debut, 1.6)
        self.assertEqual(len(resultats), 1)

    def test_tavily_resultats_et_images_sans_cle_ignore(self):
        config.CLE_API_TAVILY = ""
        with self.assertRaises(recherche_web.FournisseurIndisponible):
            recherche_web._recherche_tavily("Andry Rasoanaivo", 5)

        config.CLE_API_TAVILY = "tvly-test"
        reponse = SimpleNamespace(status_code=200, json=lambda: {
            "images": ["https://img.exemple.mg/andry.jpg"],
            "results": [{"title": "Andry Rasoanaivo - MISA", "url": "https://misa.mg/andry", "content": "Directeur de l'UFR MISA"}]})

        try:
            with mock.patch.object(recherche_web.httpx, "post", return_value=reponse) as appel, \
                    mock.patch.dict(recherche_web.FOURNISSEURS, {"tavily": recherche_web._recherche_tavily}, clear=True), \
                    mock.patch.object(config, "ORDRE_FOURNISSEURS_RECHERCHE", ["tavily"]):
                resultats = CHERCHER_RESULTATS_WEB("Andry Rasoanaivo", 5, 3)
        finally:
            config.CLE_API_TAVILY = ""

        self.assertEqual(appel.call_args.kwargs["headers"]["Authorization"], "Bearer tvly-test")
        self.assertEqual(resultats[0]["url"], "https://misa.mg/andry")
        self.assertEqual(resultats[0]["images"], ["https://img.exemple.mg/andry.jpg"])

    def test_arret_des_que_le_moteur_rapide_suffit(self):
        rapide = [{"title": f"Andry Rasoanaivo {i}", "snippet": "", "link": f"https://exemple.mg/{i}"} for i in range(3)]
        fournisseurs = {"tavily": lambda q, n: rapide, "lent": lambda q, n: time.sleep(5) or []}
        debut = time.monotonic()

        with mock.patch.dict(recherche_web.FOURNISSEURS, fournisseurs, clear=True), \
                mock.patch.object(config, "ORDRE_FOURNISSEURS_RECHERCHE", ["tavily", "lent"]):
            resultats = CHERCHER_RESULTATS_WEB("Andry Rasoanaivo", 6, 10)

        self.assertLess(time.monotonic() - debut, 1.5)                  # n'attend pas les 5 s du moteur lent
        self.assertEqual(len(resultats), 3)

    def test_adresses_privees_refusees(self):
        for url in ("http://127.0.0.1/", "http://localhost:8000/", "http://10.0.0.5/", "file:///etc/passwd"):
            self.assertFalse(recherche_web.adresse_publique(url), url)


class TestQuestionDeConnaissance(BaseFournisseurs):
    def test_requete_web_extraite_de_la_question(self):
        import conversation

        self.assertEqual(conversation.requete_web_du_message("Connais-tu Andry Rasoanaivo ?"), "Andry Rasoanaivo")
        self.assertEqual(conversation.requete_web_du_message("Qui est Andry Rasoanaivo"), "Andry Rasoanaivo")
        self.assertEqual(conversation.requete_web_du_message("Bonjour , connais tu Mr Andry Rasoanaivo"), "Andry Rasoanaivo")
        self.assertEqual(conversation.requete_web_du_message("Salut ! Qui est Monsieur Marc Ravalomanana ?"), "Marc Ravalomanana")
        self.assertEqual(conversation.requete_web_du_message("Bonjour, parle-moi du Dr Rakoto"), "Rakoto")
        self.assertEqual(conversation.requete_web_du_message("je veux trouver des informations sur Andry Rasoanaivo"), "Andry Rasoanaivo")
        self.assertEqual(conversation.requete_web_du_message("des infos sur Mr Andry Rasoanaivo svp"), "Andry Rasoanaivo svp")
        self.assertEqual(conversation.requete_web_du_message("c'est qui le président actuel de Madagascar ?"),
                         "le président actuel de Madagascar")
        self.assertTrue(recherche_web.resultat_pertinent("le président actuel de Madagascar",
                                                         "Liste des présidents de Madagascar — wikipedia"))
        self.assertTrue(conversation.merite_une_recherche_web("connais tu Andry Rasoanaivo"))
        self.assertFalse(conversation.merite_une_recherche_web("écris-moi un poème sur la mer"))
        self.assertFalse(conversation.merite_une_recherche_web("merci beaucoup"))

    def test_ville_sans_preposition(self):
        import conversation

        session = conversation.Session(id="s-sans-prep1")
        analyse, sure = conversation._analyser_par_regles("chercher alors des restaurants Antananarivo", session)
        self.assertEqual((analyse.action, analyse.categorie, analyse.lieu, sure), ("chercher", "restaurant", "Antananarivo", True))
        analyse, sure = conversation._analyser_par_regles("restaurants antananarivo pas cher", session)
        self.assertEqual((analyse.action, sure), ("preciser", False))         # minuscules : l'IA tranche
        analyse, sure = conversation._analyser_par_regles("je cherche une pharmacie", session)
        self.assertEqual((analyse.action, sure), ("preciser", True))          # rien d'autre : on demande la ville

    def test_sans_ia_les_resultats_web_sont_montres_comme_un_moteur(self):
        config.AGENT_FOURNISSEUR = config.AGENT_SECOURS_FOURNISSEUR = "off"

        with mock.patch.object(recherche_web, "chercher_resultats_web", return_value=RESULTATS_WEB) as web:
            resultat = self.tour("connais tu Andry Rasoanaivo")

        web.assert_called_once()
        self.assertEqual(web.call_args.args[0], "Andry Rasoanaivo")
        self.assertIn("Andry Rasoanaivo — Université d'Antananarivo", resultat["message"])
        self.assertNotIn("http", resultat["message"])
        self.assertEqual([source["origine"] for source in resultat["sources"]], ["web", "web"])
        self.assertEqual(resultat["sources"][0]["url"], "https://exemple.mg/andry")

    def test_photos_de_la_reponse_ajoutees_sans_attendre_l_ia(self):
        photo = {"url": "https://upload.wikimedia.org/marc.jpg", "legende": "Wikipédia — Marc Ravalomanana",
                 "page": "https://fr.wikipedia.org/wiki/Marc_Ravalomanana"}
        reponse = agent_ia.ReponseAgent("Marc Ravalomanana est un homme d'État malgache [1].", "groq", "gpt-oss", 900, [])

        with mock.patch.object(recherche_web, "chercher_resultats_web", return_value=[dict(r) for r in RESULTATS_WEB]), \
                mock.patch.object(recherche_images, "images_pour_une_reponse", return_value=[photo]) as photos, \
                mock.patch.object(agent_ia, "completer", return_value=reponse) as completer:
            resultat = self.tour("Qui est Marc Ravalomanana ?")

        photos.assert_called_once()
        self.assertEqual(photos.call_args.args[0], "Marc Ravalomanana")
        self.assertEqual(completer.call_args.kwargs["outils"], [])            # résultats déjà fournis : un seul appel
        self.assertEqual(resultat["images"], [photo])

    def test_pas_de_photo_d_une_autre_personne(self):
        reponse = SimpleNamespace(status_code=200, json=lambda: {"query": {"pages": {
            "1": {"title": "Président de la république de Madagascar", "thumbnail": {"source": "https://upload.wikimedia.org/sceau.png"}}}}})
        resultats = [{"url": "https://fr.wikipedia.org/wiki/Andry_Rajoelina"},
                     {"url": "https://fr.wikipedia.org/wiki/Président_de_la_république_de_Madagascar"}]

        with mock.patch.object(recherche_images.httpx, "get", return_value=reponse) as appel:
            images = recherche_images._images_des_pages_wikipedia("le président actuel de Madagascar", resultats, 2)

        self.assertEqual(appel.call_args.kwargs["params"]["titles"], "Président de la république de Madagascar")
        self.assertEqual([image["url"] for image in images], ["https://upload.wikimedia.org/sceau.png"])

    def test_images_du_web_seulement_pour_un_nom_propre(self):
        config.IMAGES_ACTIVES = True

        with mock.patch.object(recherche_images, "_images_des_pages_wikipedia", return_value=[]), \
                mock.patch.object(recherche_images, "_images_du_web", return_value=[{"url": "https://x.org/a.jpg"}]) as web:
            self.assertEqual(recherche_images.images_pour_une_reponse("le président actuel de Madagascar", [], delai=3), [])
            self.assertEqual(len(recherche_images.images_pour_une_reponse("Marc Ravalomanana", [], delai=3)), 1)

        web.assert_called_once()

    def test_la_premiere_page_est_lue_et_la_date_du_jour_donnee(self):
        reponse = agent_ia.ReponseAgent("Michaël Randrianirina, depuis le 14 octobre 2025 [1].", "gemini", "gemini-3.6-flash", 900, [])

        with mock.patch.object(recherche_web, "chercher_resultats_web", return_value=[dict(r) for r in RESULTATS_WEB]), \
                mock.patch.object(recherche_web, "lire_page_publique", return_value="Titulaire actuel : Michaël Randrianirina") as lecture, \
                mock.patch.object(agent_ia, "completer", return_value=reponse) as completer:
            self.tour("c'est qui le président actuel de Madagascar ?")

        lecture.assert_called_once_with("https://exemple.mg/andry", 3, 2500)
        messages = completer.call_args.args[0]
        self.assertIn("DATE DU JOUR :", messages[0]["content"])
        self.assertIn("Contenu de la page [1] : Titulaire actuel : Michaël Randrianirina", messages[-1]["content"])

    def test_avec_ia_reponse_redigee_sources_citees_d_abord(self):
        reponse = agent_ia.ReponseAgent("Il existe deux personnes de ce nom : un musicien [2] et un enseignant [1]. "
                                        "Voir https://exemple.mg", "gemini", "gemini-2.5-flash", 900, [])

        with mock.patch.object(recherche_web, "chercher_resultats_web", return_value=RESULTATS_WEB), \
                mock.patch.object(agent_ia, "completer", return_value=reponse) as completer:
            resultat = self.tour("Qui est Andry Rasoanaivo ?")

        envoye = completer.call_args.args[0][-1]["content"]
        self.assertIn("RÉSULTATS WEB", envoye)
        self.assertIn("[1] Andry Rasoanaivo — Université d'Antananarivo", envoye)
        self.assertNotIn("http", resultat["message"])                     # adresses et [n] retirés du texte
        self.assertNotIn("[1]", resultat["message"])
        self.assertEqual(resultat["sources"][0]["url"], "https://exemple.org/musique")   # [2] cité en premier
        self.assertEqual(resultat["meta"]["fournisseur_ia"], "gemini")

    def test_web_muet_l_agent_repond_avec_ses_connaissances_sans_outil(self):
        reponse = agent_ia.ReponseAgent("Andry Rasoanaivo n'est pas une personnalité très connue.", "groq", "gpt-oss", 900, [])

        with mock.patch.object(agent_ia, "completer", return_value=reponse) as completer:
            resultat = self.tour("Bonjour , connais tu Mr Andry Rasoanaivo")

        self.assertEqual(completer.call_args.kwargs["outils"], [])
        self.assertIn("réponds avec tes connaissances", completer.call_args.args[0][-1]["content"])
        self.assertEqual(resultat["images"], [])                               # images désactivées dans les tests
        self.assertEqual(resultat["message"], "Andry Rasoanaivo n'est pas une personnalité très connue.")

    def test_sans_ia_ni_resultat_web_le_message_est_honnete(self):
        config.AGENT_FOURNISSEUR = config.AGENT_SECOURS_FOURNISSEUR = "off"
        resultat = self.tour("Connais-tu Andry Rasoanaivo ?")

        self.assertIn("aucune information fiable sur « Andry Rasoanaivo »", resultat["message"])
        self.assertEqual(resultat["sources"], [])

    def test_un_nom_propre_introuvable_comme_lieu_donne_une_reponse_web(self):
        config.AGENT_FOURNISSEUR = config.AGENT_SECOURS_FOURNISSEUR = "off"

        with mock.patch.object(recherche_web, "chercher_resultats_web", return_value=RESULTATS_WEB):
            resultat = self.tour("Rasoanaivo Andry")

        self.assertIn("Voici ce que j'ai trouvé sur le web", resultat["message"])
        self.assertEqual(resultat["meta"]["action"], "discuter_apres_recherche_vide")


class TestSanteEtLimites(BaseFournisseurs):
    def setUp(self):
        super().setUp()
        self.client = TestClient(api.app)
        api._appels_recents.clear()

    def test_sante_publique_sans_detail_sensible(self):
        etats = [{"service": "PostgreSQL", "ok": False, "message": "postgresql://utilisateur:motdepasse@hote", "consequence_si_absent": "x"}]

        with mock.patch("diagnostic.diagnostiquer_services", return_value=etats), mock.patch("diagnostic._cache_sante", None):
            corps = self.client.get("/sante").json()

        self.assertEqual(corps, [{"service": "PostgreSQL", "ok": False}])
        rapide = self.client.get("/sante/rapide").json()
        self.assertTrue(rapide["ok"])
        self.assertNotIn("modele", str(rapide))
        self.assertNotIn("cle", str(rapide))

    def test_preciser_et_sante_sont_limites(self):
        config.LIMITE_REQUETES_PAR_MINUTE = 2

        with mock.patch("diagnostic.etat_public_des_services", return_value=[]):
            codes = [self.client.get("/sante").status_code for _ in range(2)]
            codes.append(self.client.post("/recherche/preciser", json={"id_resultat": "x", "id_option": "lieu"}).status_code)

        self.assertEqual(codes, [200, 200, 429])


class TestVecteurs(BaseFournisseurs):
    def test_vecteurs_desactives_sans_erreur_ni_avertissement(self):
        config.VECTEURS_FOURNISSEUR = "off"
        avertissements = []

        with self.assertRaises(modele_ia.VecteursDesactives):
            modele_ia.calculer_vecteurs(["x"])

        with mock.patch("base_donnees.chercher_fragments", return_value=[]) as fragments:
            recherche.chercher_connaissances(recherche.analyser_requete("cacao"), avertissements)

        self.assertIsNone(fragments.call_args.args[0])                      # recherche par mots-clés seulement
        self.assertEqual(avertissements, [])

    def test_vecteurs_gemini_768_normalises_avec_la_bonne_cle(self):
        config.VECTEURS_FOURNISSEUR, config.MODELE_VECTEURS = "gemini", "gemini-embedding-001"
        modele_ia._quota_vecteurs = None

        class FauxEmbeddings:
            def __init__(self, **options):
                FauxEmbeddings.options = options

            def embed_query(self, texte):
                return [3.0, 4.0] + [0.0] * (config.DIMENSION_VECTEUR - 2)

        with mock.patch("langchain_google_genai.GoogleGenerativeAIEmbeddings", FauxEmbeddings):
            vecteur = modele_ia.calculer_vecteurs(["cacao"], "requete", 2)[0]

        self.assertEqual(len(vecteur), 768)
        self.assertAlmostEqual(vecteur[0], 0.6)
        self.assertAlmostEqual(vecteur[1], 0.8)
        self.assertEqual(FauxEmbeddings.options["api_key"], "cle-gemini-test")
        self.assertEqual(FauxEmbeddings.options["output_dimensionality"], 768)


class TestImagesGalerie(Base):
    def setUp(self):
        super().setUp()
        config.IMAGES_ACTIVES = True
        recherche_images._cache.clear()
        self.sauvegarde_images = (config.IMAGES_GOOGLE_PLACES_CLE, config.IMAGES_MAPILLARY_JETON, config.IMAGES_COMMONS)

    def tearDown(self):
        config.IMAGES_GOOGLE_PLACES_CLE, config.IMAGES_MAPILLARY_JETON, config.IMAGES_COMMONS = self.sauvegarde_images
        super().tearDown()

    def test_commons_autour_d_un_site_avec_credit(self):
        reponse = SimpleNamespace(status_code=200, json=lambda: {"query": {"pages": {
            "1": {"index": 1, "title": "File:Isalo canyon.jpg", "imageinfo": [{
                "thumburl": "https://upload.wikimedia.org/isalo.jpg",
                "extmetadata": {"Artist": {"value": "<a href='x'>Rakoto</a>"}, "LicenseShortName": {"value": "CC BY-SA 4.0"}}}]},
            "2": {"index": 2, "title": "File:Carte.svg", "imageinfo": [{"thumburl": "https://upload.wikimedia.org/carte.png"}]}}}})
        lieu = {"nom": "Parc national de l'Isalo", "niveau": "site", "origine": "osm", "categorie": "Site touristique",
                "coordonnees": {"latitude": -22.55, "longitude": 45.37}, "images": []}

        with mock.patch.object(recherche_images.httpx, "get", return_value=reponse) as appel:
            images = recherche_images._images_commons(lieu, 2)

        self.assertEqual(appel.call_args.kwargs["params"]["ggsradius"], 2000)
        self.assertEqual(images, [{"url": "https://upload.wikimedia.org/isalo.jpg",
                                   "legende": "Photo : Rakoto, CC BY-SA 4.0 — Wikimedia Commons"}])

    def test_commons_surcharge_ne_casse_rien(self):
        reponse = SimpleNamespace(status_code=200, json=lambda: {"error": {"code": "cirrussearch-too-busy-error"}})
        lieu = {"nom": "Antsirabe", "niveau": "commune", "origine": "referentiel", "coordonnees": {"latitude": -19.87, "longitude": 47.03}}

        with mock.patch.object(recherche_images.httpx, "get", return_value=reponse):
            self.assertEqual(recherche_images._images_commons(lieu, 2), [])

    def test_galerie_plusieurs_images_et_google_jamais_en_cache(self):
        config.IMAGES_PAR_LIEU = 3
        lieu = {"nom": "Restaurant Kanana", "origine": "osm", "images": ["https://osm.org/a.jpg"],
                "coordonnees": {"latitude": -18.9, "longitude": 47.5}}
        trouvees = [{"url": "https://g.com/1.jpg", "legende": "Photo : Rabe — Google Maps", "google": True},
                    {"url": "https://commons.org/2.jpg", "legende": "Photo : Wikimedia Commons"}]

        with mock.patch.object(recherche_images, "_chercher_pour_un_lieu", return_value=trouvees):
            recherche_images.enrichir_avec_images([lieu], delai_max=2)

        self.assertEqual(lieu["images"], ["https://osm.org/a.jpg", "https://g.com/1.jpg", "https://commons.org/2.jpg"])
        self.assertEqual(lieu["images_details"][1]["legende"], "Photo : Rabe — Google Maps")
        en_cache = recherche_images._lire_le_cache(recherche_images._cle(lieu))
        self.assertEqual([image["url"] for image in en_cache], ["https://commons.org/2.jpg"])


if __name__ == "__main__":
    unittest.main()
