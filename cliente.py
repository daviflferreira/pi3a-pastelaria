import socket
import ssl

from config import CERT_ARQUIVO, HOST, NOME_SERVIDOR_TLS, PORTA
from protocolo import ErroProtocolo, enviar, receber


def criar_contexto_tls():
    contexto = ssl.create_default_context(cafile=CERT_ARQUIVO)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    return contexto


_CONTEXTO = None


def consultar(pedido):
    """Envia um pedido ao servidor por TLS e devolve a resposta (dict)."""
    global _CONTEXTO
    if _CONTEXTO is None:
        _CONTEXTO = criar_contexto_tls()
    with socket.create_connection((HOST, PORTA), timeout=5) as conexao:
        with _CONTEXTO.wrap_socket(conexao, server_hostname=NOME_SERVIDOR_TLS) as conexao_tls:
            enviar(conexao_tls, pedido)
            return receber(conexao_tls)


def montar_pedido(texto):
    partes = texto.split(maxsplit=1)
    acao = partes[0].lower() if partes else ""
    argumento = partes[1] if len(partes) > 1 else ""

    pedido = {"acao": acao}
    if acao == "buscar":
        pedido["termo"] = argumento
    elif acao == "detalhar" and argumento.isdigit():
        pedido["id"] = int(argumento)
    return pedido


def main():
    while True:
        texto = input("Mensagem (ou 'sair'): ").strip()
        if texto.lower() == "sair":
            print("Encerrando o cliente.")
            break

        try:
            resposta = consultar(montar_pedido(texto))
            print(f"Servidor respondeu: {resposta}")
        except ConnectionRefusedError:
            print("Não foi possível conectar: o servidor provavelmente tá offline!")
        except TimeoutError:
            print("O servidor demorou pra responder.")
        except ssl.SSLCertVerificationError as erro:
            print(f"Certificado do servidor não confiável: {erro.verify_message}")
        except ErroProtocolo as erro:
            print(f"Resposta inválida do servidor: {erro}")


if __name__ == "__main__":
    main()