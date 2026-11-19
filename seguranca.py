"""Recursos de segurança da área restrita (o TLS fica no servidor/cliente).

- Senha guardada como hash PBKDF2-SHA256 com salt (nunca em texto puro).
- Sessões com token aleatório e prazo de validade.
- Bloqueio temporário após várias senhas erradas.
Tudo com a biblioteca padrão: hashlib, hmac, secrets.
"""
import hashlib
import hmac
import os
import secrets
import threading
import time

ITERACOES_PBKDF2 = 600_000
SESSAO_DURACAO_SEG = 2 * 60 * 60   # 2 horas
LOGIN_MAX_TENTATIVAS = 5
LOGIN_BLOQUEIO_SEG = 5 * 60        # 5 minutos


def gerar_hash_senha(senha):
    salt = os.urandom(16)
    resumo = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, ITERACOES_PBKDF2)
    return {
        "algoritmo": "pbkdf2_sha256",
        "iteracoes": ITERACOES_PBKDF2,
        "salt": salt.hex(),
        "hash": resumo.hex(),
    }


def verificar_senha(senha, registro):
    resumo = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), bytes.fromhex(registro["salt"]), int(registro["iteracoes"])
    )
    return hmac.compare_digest(resumo.hex(), registro["hash"])


class Sessoes:
    def __init__(self, duracao=SESSAO_DURACAO_SEG):
        self._duracao = duracao
        self._tokens = {}
        self._lock = threading.Lock()

    def criar(self):
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = time.monotonic() + self._duracao
        return token

    def valida(self, token):
        if not isinstance(token, str):
            return False
        with self._lock:
            expira = self._tokens.get(token)
            if expira is None:
                return False
            if time.monotonic() > expira:
                del self._tokens[token]
                return False
            return True

    def encerrar(self, token):
        with self._lock:
            self._tokens.pop(token, None)


class LimitadorLogin:
    def __init__(self, maximo=LOGIN_MAX_TENTATIVAS, bloqueio=LOGIN_BLOQUEIO_SEG):
        self._maximo = maximo
        self._bloqueio = bloqueio
        self._falhas = 0
        self._ultima_falha = 0.0
        self._lock = threading.Lock()

    def bloqueado(self):
        with self._lock:
            if self._falhas < self._maximo:
                return False
            if time.monotonic() - self._ultima_falha < self._bloqueio:
                return True
            self._falhas = 0
            return False

    def registrar_falha(self):
        with self._lock:
            self._falhas += 1
            self._ultima_falha = time.monotonic()

    def registrar_sucesso(self):
        with self._lock:
            self._falhas = 0
