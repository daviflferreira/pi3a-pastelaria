import socket
from config import HOST, PORTA
from protocolo import ErroProtocolo, enviar, receber

def main():
    while True:
        texto = input("Mensagem (ou 'sair'): ").strip()
        if texto.lower() == "sair":
            print("Encerrando a conexão")
            break
        
        partes = texto.split(maxsplit=1)
        acao = partes[0].lower() if partes else ""
        argumento = partes[1] if len(partes) > 1 else ""

        pedido = {"acao": acao}
        if acao == "buscar":
            pedido["termo"] = argumento
        elif acao == "detalhar" and argumento.isdigit():
            pedido["id"] = int(argumento)
        try:
            with socket.create_connection((HOST, PORTA), timeout=5) as conexao:
                enviar(conexao, pedido)
                resposta = receber(conexao)
                print(f"Servidor respondeu: {resposta}")
        except ConnectionRefusedError:
            print("Não foi possível conectar: o servidor provavelmente tá offline!")
        except TimeoutError:
            print("O servidor demorou pra responder.")
        except ErroProtocolo as erro:
            print(f"Resposta inválida do servidor: {erro}")
        
        
if __name__ == "__main__":
    main()