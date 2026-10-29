"""Faux serveur d'IA pour les tests : parle comme une API OpenAI (/chat/completions) et comme Ollama (/api/chat)."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class FauxServeurIA:
    def __init__(self):
        self.appels: list[dict] = []
        self.gestionnaire = lambda systeme, utilisateur: None     # retourne le texte à renvoyer, ou un entier = code HTTP d'erreur
        faux = self

        class Gestionnaire(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                messages = corps.get("messages", [])
                systeme = next((m["content"] for m in messages if m["role"] == "system"), "")
                utilisateur = messages[-1]["content"] if messages else ""
                chemin = self.path
                faux.appels.append({"chemin": chemin, "corps": corps, "autorisation": self.headers.get("Authorization")})
                resultat = faux.gestionnaire(systeme, utilisateur)

                if isinstance(resultat, int):
                    self.send_response(resultat)
                    self.end_headers()
                    return

                if resultat is None:
                    resultat = "{}"

                if chemin.endswith("/chat/completions"):
                    donnees = {"choices": [{"message": {"role": "assistant", "content": resultat}}]}
                else:
                    donnees = {"message": {"role": "assistant", "content": resultat}}

                octets = json.dumps(donnees).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(octets)))
                self.end_headers()
                self.wfile.write(octets)

        self.serveur = HTTPServer(("127.0.0.1", 0), Gestionnaire)
        self.url = f"http://127.0.0.1:{self.serveur.server_address[1]}"
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def arreter(self):
        self.serveur.shutdown()
        self.serveur.server_close()
