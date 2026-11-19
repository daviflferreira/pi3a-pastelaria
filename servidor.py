import socket
from admin import ACOES_ADMIN, mascarar
from config import CERT_ARQUIVO, CHAVE_ARQUIVO, HOST, PORTA
from protocolo import enviar, receber, ErroProtocolo
import json
from pathlib import Path
import ssl
import unicodedata
from datetime import datetime, timedelta

PASTA_DADOS = Path(__file__).parent / "dados"
CAMPOS_PUBLICOS = ("id", "nome", "categoria", "descricao", "ingredientes", "preco", "disponivel")
DIAS = ("segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo")
NOMES_DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")

def carregar(nome_arquivo):
    with open(PASTA_DADOS / nome_arquivo, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def publico(item):
    return {campo: item[campo] for campo in CAMPOS_PUBLICOS if campo in item}

def normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower().strip()


def calcular_status(funcionamento, agora):
    hoje = DIAS[agora.weekday()]
    hora = agora.strftime("%H:%M")
    horario_hoje = funcionamento.get(hoje)

    if horario_hoje and horario_hoje["abre"] <= hora < horario_hoje["fecha"]:
        return {"aberto": True, "mensagem": f"Aberto agora · fecha às {horario_hoje['fecha']}"}

    if horario_hoje and hora < horario_hoje["abre"]:
        return {"aberto": False, "mensagem": f"Fechado · abre hoje às {horario_hoje['abre']}"}

    for dias_a_frente in range(1, 8):
        dia = agora + timedelta(days=dias_a_frente)
        horario = funcionamento.get(DIAS[dia.weekday()])
        if horario:
            quando = "amanhã" if dias_a_frente == 1 else NOMES_DIAS[dia.weekday()]
            return {"aberto": False, "mensagem": f"Fechado · abre {quando} às {horario['abre']}"}

    return {"aberto": False, "mensagem": "Fechado"}


def acao_status(pedido):
    funcionamento = carregar("loja.json")["funcionamento"]
    return {"ok": True, "dados": calcular_status(funcionamento, datetime.now())}

def acao_listar(pedido):
    itens = carregar("cardapio.json")["itens"]
    return {"ok": True, "dados": [publico(item) for item in itens]}


def acao_loja(pedido):
    return {"ok": True, "dados": carregar("loja.json")}


def acao_buscar(pedido):
    termo = normalizar(pedido.get("termo", ""))
    if not termo:
        return {"ok": False, "erro": "Informe o que buscar"}

    itens = carregar("cardapio.json")["itens"]
    achados = []
    for item in itens:
        no_nome = termo in normalizar(item["nome"])
        nos_ingredientes = any(termo in normalizar(ingrediente) for ingrediente in item["ingredientes"])
        if no_nome or nos_ingredientes:
            achados.append(publico(item))

    return {"ok": True, "dados": achados}


def acao_detalhar(pedido):
    id_item = pedido.get("id")
    if not isinstance(id_item, int) or isinstance(id_item, bool):
        return {"ok": False, "erro": "Informe o número do item"}

    for item in carregar("cardapio.json")["itens"]:
        if item["id"] == id_item:
            return {"ok": True, "dados": publico(item)}

    return {"ok": False, "erro": "Item não encontrado"}


ACOES = {
    "listar": acao_listar,
    "buscar": acao_buscar,
    "detalhar": acao_detalhar,
    "loja": acao_loja,
    "status": acao_status,
    **ACOES_ADMIN,
}


def processar(pedido):
    funcao = ACOES.get(pedido.get("acao"))
    if funcao is None:
        return {"ok": False, "erro": f"Ação desconhecida: {pedido.get('acao')!r}"}
    return funcao(pedido)

def criar_contexto_tls():
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    contexto.load_cert_chain(CERT_ARQUIVO, CHAVE_ARQUIVO)
    return contexto


def main():
    contexto = criar_contexto_tls()
    with socket.create_server((HOST, PORTA)) as servidor:
        print(f"Servidor (TLS) ouvindo em {HOST}:{PORTA} (Ctrl+C pra parar)")
        try:
            while True:
                conexao, endereco = servidor.accept()
                origem = f"{endereco[0]}:{endereco[1]}"
                try:
                    with contexto.wrap_socket(conexao, server_side=True) as conexao_tls:
                        pedido = receber(conexao_tls)
                        print(f"{origem} [{conexao_tls.version()}] pediu: {mascarar(pedido)}")
                        enviar(conexao_tls, processar(pedido))
                except ssl.SSLError as erro:
                    print(f"{origem} falha no TLS: {erro.reason}")
                except ErroProtocolo as erro:
                    print(f"{origem} mensagem inválida: {erro}")
                except OSError as erro:
                    print(f"{origem} erro de conexão: {erro}")
        except KeyboardInterrupt:
            print("\nServidor encerrado")
            
if __name__ == "__main__":
    main()