import socket

HOST = "127.0.0.1"
PORTA = 5050

def main():
    with socket.create_server((HOST, PORTA)) as servidor:
        print(f"Servidor ouvindo em {HOST}:{PORTA} *Ctrl+C pra parar)")
        try:
            while True:
                conexao, endereco = servidor.accept()
                with conexao:
                    dados = conexao.recv(1024)
                    texto = dados.decode("utf-8")
                    print(f"{endereco[0]}:{endereco[1]} enviou: {texto}")
                    resposta = f"olá, recebi: {texto}"
                    conexao.sendall(resposta.encode("utf-8"))
                    
        except KeyboardInterrupt:
            print("\nServidor Encerrado")
            
if __name__ == "__main__":
    main()