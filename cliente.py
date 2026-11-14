import socket

HOST = "127.0.0.1"
PORTA = 5050

def main():
    while True:
        texto = input("Mensagem (ou 'sair'): ").strip()
        if texto.lower() == "sair":
            print("Fechando o server.")
            break
        if not texto:
            continue
        
        try:
            with socket.create_connection((HOST, PORTA), timeout=5) as conexao:
                conexao.sendall(texto.encode("utf-8"))
                resposta = conexao.recv(1024).decode("utf-8")
                print(f"Servidor respondeu: {resposta}")
        except ConnectionRefusedError:
            print("Não foi possivel conectar: o servidor provavelmente ta offline!")
        except TimeoutError:
            print("O servidor demorou pra responder.")
        
        
if __name__ == "__main__":
    main()