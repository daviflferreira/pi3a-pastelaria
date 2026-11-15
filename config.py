"""Configs compartilhadas entre o cliente e o server"""

from pathlib import Path

BASE_DIR = Path(__file__).parent

HOST = "127.0.0.1"
PORTA = 5050
TAMANHO_MAX_MENSAGEM = 1_000_000

NOME_SERVIDOR_TLS = "localhost"
CERT_ARQUIVO = BASE_DIR / "certs" / "servidor.crt"
CHAVE_ARQUIVO = BASE_DIR / "certs" / "servidor.key"