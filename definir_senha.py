"""Define (ou troca) a senha da área do dono. Rode: python definir_senha.py"""
import json
from getpass import getpass
from pathlib import Path

from seguranca import gerar_hash_senha

ARQUIVO_ADMIN = Path(__file__).parent / "dados" / "admin.json"
TAMANHO_MINIMO = 8


def main():
    senha = getpass("Nova senha da área do dono: ")
    if len(senha) < TAMANHO_MINIMO:
        print(f"A senha precisa ter pelo menos {TAMANHO_MINIMO} caracteres.")
        return
    if getpass("Repita a senha: ") != senha:
        print("As senhas não conferem.")
        return

    ARQUIVO_ADMIN.write_text(json.dumps(gerar_hash_senha(senha), indent=2), encoding="utf-8")
    print(f"Senha salva em {ARQUIVO_ADMIN} (somente o hash, nunca a senha).")


if __name__ == "__main__":
    main()
