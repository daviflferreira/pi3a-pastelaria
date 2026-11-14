"""Protocolo de mensagens: JSON em UTF-8 precedido por 4 bytes com o tamanho."""
import json
import struct

from config import TAMANHO_MAX_MENSAGEM

_CABECALHO = struct.Struct("!I")

class ErroProtocolo(Exception):
    """Mensagem malformada, grande demais ou conexão interrompida."""

def enviar(sock, mensagem: dict) -> None:
    dados = json.dumps(mensagem, ensure_ascii=False).encode("utf-8")
    if len(dados) > TAMANHO_MAX_MENSAGEM:
        raise ErroProtocolo("Mensagem muito grande!")
    sock.sendall(_CABECALHO.pack(len(dados)) + dados)
    
def _receber_exato(sock, quantidade: int) -> bytes:
    partes = []
    faltam = quantidade
    while faltam > 0:
        bloco = sock.recv(min(faltam, 65536))
        if not bloco:
            raise ErroProtocolo("Conexão encerrada antes do fim da mensagem")
        partes.append(bloco)
        faltam -= len(bloco)
    return b"".join(partes)
    
def receber(sock) -> dict:
    (tamanho,) = _CABECALHO.unpack(_receber_exato(sock, _CABECALHO.size))
    if tamanho > TAMANHO_MAX_MENSAGEM:
        raise ErroProtocolo("Mensagem grande demais")
    try:
        mensagem = json.loads(_receber_exato(sock, tamanho).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ErroProtocolo("JSON inválido") from erro
    if not isinstance(mensagem, dict):
        raise ErroProtocolo("A mensagem deve ser um objeto JSON")
    return mensagem
