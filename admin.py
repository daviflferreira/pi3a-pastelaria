"""Área restrita do dono: login, consulta completa e edição do cardápio e da loja."""
import json
import os
import re
import tempfile
import threading
from functools import wraps
from pathlib import Path

from seguranca import LimitadorLogin, Sessoes, verificar_senha

PASTA_DADOS = Path(__file__).parent / "dados"
DIAS = ("segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo")
FORMATO_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
CAMPOS_SENSIVEIS = ("senha", "token")

sessoes = Sessoes()
limitador = LimitadorLogin()
_trava_gravacao = threading.Lock()


# ---------- leitura e gravação segura dos arquivos ----------

def carregar(nome_arquivo):
    with open(PASTA_DADOS / nome_arquivo, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def gravar(nome_arquivo, dados):
    """Grava num arquivo temporário e depois troca de lugar: se algo falhar no meio,
    o arquivo original continua intacto."""
    destino = PASTA_DADOS / nome_arquivo
    descritor, caminho_temp = tempfile.mkstemp(dir=PASTA_DADOS, suffix=".tmp")
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        os.replace(caminho_temp, destino)
    except BaseException:
        os.unlink(caminho_temp)
        raise


def mascarar(pedido):
    """Cópia do pedido sem senha/token, para poder imprimir no log."""
    return {chave: ("***" if chave in CAMPOS_SENSIVEIS else valor) for chave, valor in pedido.items()}


# ---------- autenticação ----------

def exige_login(funcao):
    """Decorador: só executa a ação se o pedido trouxer um token de sessão válido."""
    @wraps(funcao)
    def protegida(pedido):
        if not sessoes.valida(pedido.get("token")):
            return {"ok": False, "erro": "Sessão inválida ou expirada. Faça login novamente.", "login": True}
        return funcao(pedido)
    return protegida


def acao_login(pedido):
    if limitador.bloqueado():
        return {"ok": False, "erro": "Muitas tentativas erradas. Aguarde alguns minutos."}

    try:
        registro = carregar("admin.json")
    except FileNotFoundError:
        return {"ok": False, "erro": "Senha ainda não definida. Rode: python definir_senha.py"}

    senha = pedido.get("senha")
    if not isinstance(senha, str) or not verificar_senha(senha, registro):
        limitador.registrar_falha()
        return {"ok": False, "erro": "Senha incorreta"}

    limitador.registrar_sucesso()
    return {"ok": True, "dados": {"token": sessoes.criar()}}


def acao_logout(pedido):
    sessoes.encerrar(pedido.get("token"))
    return {"ok": True, "dados": None}


# ---------- validação ----------

def _texto(valor, campo, maximo, obrigatorio=False):
    if valor is None and not obrigatorio:
        return ""
    if not isinstance(valor, str):
        raise ValueError(f"'{campo}' deve ser texto")
    valor = valor.strip()
    if obrigatorio and not valor:
        raise ValueError(f"'{campo}' é obrigatório")
    if len(valor) > maximo:
        raise ValueError(f"'{campo}' pode ter no máximo {maximo} caracteres")
    return valor


def _numero(valor, campo, minimo=0, maximo=10_000, opcional=False):
    if valor is None and opcional:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"'{campo}' deve ser um número")
    if not minimo <= valor <= maximo:
        raise ValueError(f"'{campo}' deve estar entre {minimo} e {maximo}")
    return round(float(valor), 2)


def validar_item(dados):
    if not isinstance(dados, dict):
        raise ValueError("Item inválido")

    ingredientes = dados.get("ingredientes", [])
    if not isinstance(ingredientes, list) or len(ingredientes) > 30:
        raise ValueError("'ingredientes' deve ser uma lista com até 30 itens")
    ingredientes = [_texto(i, "ingrediente", 40, obrigatorio=True).lower() for i in ingredientes]

    disponivel = dados.get("disponivel", True)
    if not isinstance(disponivel, bool):
        raise ValueError("'disponivel' deve ser verdadeiro ou falso")

    fornecedor = _texto(dados.get("fornecedor"), "fornecedor", 80)
    return {
        "nome": _texto(dados.get("nome"), "nome", 80, obrigatorio=True),
        "categoria": _texto(dados.get("categoria"), "categoria", 60, obrigatorio=True),
        "descricao": _texto(dados.get("descricao"), "descricao", 300),
        "ingredientes": ingredientes,
        "preco": _numero(dados.get("preco"), "preco", maximo=1000),
        "disponivel": disponivel,
        "custo": _numero(dados.get("custo"), "custo", maximo=1000, opcional=True),
        "fornecedor": fornecedor or None,
    }


def validar_funcionamento(dados):
    if not isinstance(dados, dict) or set(dados) != set(DIAS):
        raise ValueError("Informe o horário de todos os dias da semana")
    resultado = {}
    for dia in DIAS:
        horario = dados[dia]
        if horario is None:
            resultado[dia] = None
            continue
        abre, fecha = horario.get("abre"), horario.get("fecha")
        if not (isinstance(abre, str) and FORMATO_HORA.match(abre) and isinstance(fecha, str) and FORMATO_HORA.match(fecha)):
            raise ValueError(f"Horário de {dia} deve estar no formato HH:MM")
        if abre >= fecha:
            raise ValueError(f"Em {dia}, o horário de abrir deve ser antes do de fechar")
        resultado[dia] = {"abre": abre, "fecha": fecha}
    return resultado


def _id_valido(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


# ---------- ações restritas ----------

@exige_login
def acao_admin_listar(pedido):
    return {"ok": True, "dados": carregar("cardapio.json")["itens"]}


@exige_login
def acao_salvar_item(pedido):
    try:
        novo = validar_item(pedido.get("item"))
    except ValueError as erro:
        return {"ok": False, "erro": str(erro)}

    id_item = (pedido.get("item") or {}).get("id")
    with _trava_gravacao:
        cardapio = carregar("cardapio.json")
        itens = cardapio["itens"]
        if id_item is None:
            novo = {"id": max((item["id"] for item in itens), default=0) + 1, **novo}
            itens.append(novo)
        else:
            posicao = next((i for i, item in enumerate(itens) if item["id"] == id_item), None)
            if not _id_valido(id_item) or posicao is None:
                return {"ok": False, "erro": "Item não encontrado"}
            novo = {"id": id_item, **novo}
            itens[posicao] = novo
        gravar("cardapio.json", cardapio)

    return {"ok": True, "dados": novo}


@exige_login
def acao_remover_item(pedido):
    id_item = pedido.get("id")
    if not _id_valido(id_item):
        return {"ok": False, "erro": "Informe o número do item"}
    with _trava_gravacao:
        cardapio = carregar("cardapio.json")
        restantes = [item for item in cardapio["itens"] if item["id"] != id_item]
        if len(restantes) == len(cardapio["itens"]):
            return {"ok": False, "erro": "Item não encontrado"}
        cardapio["itens"] = restantes
        gravar("cardapio.json", cardapio)
    return {"ok": True, "dados": None}


@exige_login
def acao_disponibilidade(pedido):
    id_item, disponivel = pedido.get("id"), pedido.get("disponivel")
    if not _id_valido(id_item) or not isinstance(disponivel, bool):
        return {"ok": False, "erro": "Informe o item e se está disponível (true/false)"}
    with _trava_gravacao:
        cardapio = carregar("cardapio.json")
        for item in cardapio["itens"]:
            if item["id"] == id_item:
                item["disponivel"] = disponivel
                gravar("cardapio.json", cardapio)
                return {"ok": True, "dados": item}
    return {"ok": False, "erro": "Item não encontrado"}


@exige_login
def acao_atualizar_loja(pedido):
    dados = pedido.get("loja")
    if not isinstance(dados, dict):
        return {"ok": False, "erro": "Dados da loja inválidos"}
    try:
        pagamentos = dados.get("pagamentos", [])
        if not isinstance(pagamentos, list) or len(pagamentos) > 10:
            raise ValueError("'pagamentos' deve ser uma lista com até 10 itens")
        loja = {
            "nome": _texto(dados.get("nome"), "nome", 80, obrigatorio=True),
            "endereco": _texto(dados.get("endereco"), "endereco", 150),
            "telefone": _texto(dados.get("telefone"), "telefone", 30),
            "instagram": _texto(dados.get("instagram"), "instagram", 40),
            "funcionamento": validar_funcionamento(dados.get("funcionamento")),
            "pagamentos": [_texto(p, "pagamento", 30, obrigatorio=True) for p in pagamentos],
        }
    except ValueError as erro:
        return {"ok": False, "erro": str(erro)}

    with _trava_gravacao:
        gravar("loja.json", loja)
    return {"ok": True, "dados": loja}


ACOES_ADMIN = {
    "login": acao_login,
    "logout": acao_logout,
    "admin_listar": acao_admin_listar,
    "salvar_item": acao_salvar_item,
    "remover_item": acao_remover_item,
    "disponibilidade": acao_disponibilidade,
    "atualizar_loja": acao_atualizar_loja,
}
