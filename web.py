"""Interface web: serve as páginas e repassa as consultas ao servidor (via cliente.py, com TLS)."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from cliente import consultar
from config import WEB_HOST, WEB_PORTA
from protocolo import ErroProtocolo

PASTA_STATIC = (Path(__file__).parent / "static").resolve()
TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}
ACOES_PERMITIDAS = {
    "listar", "buscar", "detalhar", "loja", "status",
    "login", "logout", "admin_listar", "salvar_item", "remover_item", "disponibilidade", "atualizar_loja",
}
ROTAS = {"/": "/index.html", "/admin": "/admin.html"}
TAMANHO_MAX_CORPO = 10_000


class Manipulador(BaseHTTPRequestHandler):
    def do_GET(self):
        caminho = urlsplit(self.path).path
        caminho = ROTAS.get(caminho, caminho)

        arquivo = (PASTA_STATIC / caminho.lstrip("/")).resolve()
        if arquivo.parent != PASTA_STATIC or arquivo.suffix not in TIPOS or not arquivo.is_file():
            self.responder(404, "Página não encontrada".encode("utf-8"), "text/plain; charset=utf-8")
            return
        self.responder(200, arquivo.read_bytes(), TIPOS[arquivo.suffix])

    def do_POST(self):
        if urlsplit(self.path).path != "/api":
            self.responder_json(404, {"ok": False, "erro": "Rota não encontrada"})
            return

        try:
            tamanho = int(self.headers.get("Content-Length", 0))
        except ValueError:
            tamanho = 0
        if not 0 < tamanho <= TAMANHO_MAX_CORPO:
            self.responder_json(400, {"ok": False, "erro": "Requisição inválida"})
            return

        try:
            pedido = json.loads(self.rfile.read(tamanho))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.responder_json(400, {"ok": False, "erro": "JSON inválido"})
            return

        if not isinstance(pedido, dict) or pedido.get("acao") not in ACOES_PERMITIDAS:
            self.responder_json(400, {"ok": False, "erro": "Ação não permitida"})
            return

        try:
            self.responder_json(200, consultar(pedido))
        except (OSError, ErroProtocolo) as erro:
            print(f"Falha ao falar com o servidor de consultas: {erro}")
            self.responder_json(503, {"ok": False, "erro": "Servidor de consultas indisponível"})

    def responder_json(self, status, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.responder(status, corpo, "application/json; charset=utf-8")

    def responder(self, status, corpo, tipo):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, formato, *args):
        print(f"[web] {self.address_string()} {formato % args}")


def main():
    with ThreadingHTTPServer((WEB_HOST, WEB_PORTA), Manipulador) as servidor_web:
        print(f"Interface web em http://{WEB_HOST}:{WEB_PORTA} (Ctrl+C pra parar)")
        try:
            servidor_web.serve_forever()
        except KeyboardInterrupt:
            print("\nInterface web encerrada")


if __name__ == "__main__":
    main()