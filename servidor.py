import socket
from config import HOST, PORTA
from protocolo import enviar, receber, ErroProtocolo

def main():
    with socket.create_server((HOST, PORTA)) as servidor:
        print(f"Servidor ouvindo em {HOST}:{PORTA} (Ctrl+C pra parar)")
        try:
            while True:
                conexao, endereco = servidor.accept()
                with conexao:
                    try:
                        pedido = receber(conexao)
                        print(f"{endereco[0]}:{endereco[1]} pediu: {pedido}")
                        enviar(conexao, {"ok": True, "eco": pedido})
                    except ErroProtocolo as erro:
                        print(f"{endereco[0]}:{endereco[1]} mensagem inválida: {erro}")
                    
        except KeyboardInterrupt:
            print("\nServidor Encerrado")
            
if __name__ == "__main__":
    main()