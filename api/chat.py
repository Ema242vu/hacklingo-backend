import os
import json
import requests
import urllib.request
from http.server import BaseHTTPRequestHandler

URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Verificar token de Firebase
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self._responder({"respuesta": "No autorizado"}, 401)
                return

            token = auth_header.replace('Bearer ', '')
            firebase_key = os.environ.get('FIREBASE_API_KEY', '')

            # Verificar con Firebase REST API
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={firebase_key}"
            data = json.dumps({"idToken": token}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    user_data = json.loads(resp.read().decode())
                    if not user_data.get('users'):
                        self._responder({"respuesta": "Token inválido"}, 401)
                        return
            except Exception as e:
                self._responder({"respuesta": f"Token inválido: {str(e)[:50]}"}, 401)
                return

            # Procesar mensaje
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body) if body else {}
            mensaje = data.get('mensaje', '')
            personalidad = data.get('personalidad', 'Eres una waifu hacker. Responde en español, máximo 3 líneas.')

            api_key = os.environ.get('GROQ_API_KEY', '')
            if not mensaje or not api_key:
                self._responder({"respuesta": "Falta mensaje o API Key"})
                return

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "openai/gpt-oss-20b",
                "messages": [
                    {"role": "system", "content": personalidad},
                    {"role": "user", "content": mensaje}
                ],
                "temperature": 0.8,
                "max_tokens": 200
            }
            r = requests.post(URL_GROQ, headers=headers, json=payload, timeout=20)
            if r.status_code == 200:
                respuesta = r.json()['choices'][0]['message']['content']
            else:
                respuesta = f"Error {r.status_code}"
            self._responder({"respuesta": respuesta})
        except Exception as e:
            self._responder({"respuesta": f"Error: {str(e)[:80]}"})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def _responder(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
