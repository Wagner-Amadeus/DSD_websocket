import asyncio                          # Suportar programação assíncrona.
import websockets                       # Implementar WebSocket no servidor.
import json                             # Tratar com codificação e decodificação de objetos JSON.
from reportlab.pdfgen import canvas     # Criar documentos PDF.

# Definição da classe Aluno
class Aluno:
    def __init__(self, nome, nota1, nota2):
        self.nome = nome
        self.nota1 = nota1
        self.nota2 = nota2
        self.media = (nota1 + nota2) / 2
        self.situacao = "Aprovado" if self.media >= 7 else "Reprovado"


alunos = set()                          # Conjunto para armazenar instâncias da classe Aluno. 
connected_clients = set()               # Conjunto para armazenar clientes conectados ao servidor WebSocket.

# Declaração de função assíncrona
async def enviar_lista_alunos():
    global alunos
    # Compreensão de lista para criar uma lista de dicionários de alunos
    lista_alunos = [
        {
            "posicao": i + 1,
            "nome": aluno.nome,
            "nota1": aluno.nota1,
            "nota2": aluno.nota2,
            "media": aluno.media,
            "situacao": aluno.situacao
        } for i, aluno in enumerate(sorted(alunos, key=lambda x: x.media, reverse=True))
    ]   # Ordenada a lista com base na média dos alunos em ordem decrescente.

    # Envia a lista de alunos para todos os clientes conectados de forma assíncrona.
    # Cada cliente recebe uma mensagem JSON contendo a ação ("lista_alunos") e a lista de alunos.
    await asyncio.gather(
        *[client.send(json.dumps({"action": "lista_alunos", "alunos": lista_alunos})) for client in connected_clients]
    )

# Função assíncrona para criar um relatório em PDF contendo informações sobre os alunos.
async def gerar_relatorio():
    global alunos

    # Cria um documento PDF usando a biblioteca reportlab
    pdf_filename = "relatorio_alunos.pdf"
    c = canvas.Canvas(pdf_filename)
    c.drawString(100, 800, "RELATÓRIO DE ALUNOS")

    # Adiciona os dados dos alunos ao PDF
    y = 780
    for i, aluno in enumerate(sorted(alunos, key=lambda x: x.media, reverse=True), start=1):
        c.drawString(100, y, f"POS: {i}")
        c.drawString(150, y, f"Nome: {aluno.nome}")
        c.drawString(150, y - 15, f"Nota 1: {aluno.nota1}")
        c.drawString(150, y - 30, f"Nota 2: {aluno.nota2}")
        c.drawString(150, y - 45, f"Média: {aluno.media}")
        c.drawString(150, y - 60, f"Situação: {aluno.situacao}")
        y -= 80

    # Salva o documento PDF
    c.save()

    # Envia o nome do arquivo para os clientes baixarem
    await asyncio.gather(
        *[client.send(json.dumps({"action": "baixar_relatorio", "filename": pdf_filename})) for client in connected_clients]
    )

# Função assíncrona para processar as mensagens recebidas dos clientes WebSocket.
async def processar_mensagem(websocket, message):
    global alunos, connected_clients

    try:
        # Converte a string JSON recebida em um objeto Python usando json.loads.
        data = json.loads(message)

        # Obtém o valor associado à chave "action" no objeto JSON.
        action = data.get("action")

        if action == "registrar_aluno":
            nome = data["nome"]
            nota1 = float(data["nota1"])
            nota2 = float(data["nota2"])

            aluno = Aluno(nome, nota1, nota2)
            alunos.add(aluno)

            # Criação de um dicionário contendo informações do aluno para enviar de volta ao cliente que registrou o aluno.
            response = {
                "nome": aluno.nome,
                "nota1": aluno.nota1,
                "nota2": aluno.nota2,
                "media": aluno.media,
                "situacao": aluno.situacao
            }

            # Broadcast para todos os clientes conectados
            await asyncio.gather(
                *[client.send(json.dumps(response)) for client in connected_clients]
            )

            # Enviar a lista atualizada para todos os clientes
            await enviar_lista_alunos()

        elif action == "remover_aluno":
            nome_aluno_remover = data["nome"]
            # Atualiza o conjunto de alunos, removendo o aluno com o nome fornecido.
            alunos = {aluno for aluno in alunos if aluno.nome != nome_aluno_remover}

            # Broadcast para todos os clientes conectados para atualizar a lista
            await asyncio.gather(
                *[client.send(json.dumps({"action": "remover_aluno", "nome": nome_aluno_remover})) for client in connected_clients]
            )

        elif action == "conectar_cliente":
            # Enviar lista de alunos para cliente recém-conectado
            await enviar_lista_alunos()

        elif action == "gerar_relatorio":
            # Gerar o relatório em PDF
            await gerar_relatorio()

    except websockets.exceptions.ConnectionClosedOK:
        pass

# Função assíncrona chamada quando um novo cliente WebSocket se conecta ao servidor. 
async def registrar_aluno(websocket, path):
    global connected_clients
    # Adiciona o objeto WebSocket do cliente recém-conectado ao conjunto connected_clients.
    connected_clients.add(websocket)

    try:
        # Chama a função assíncrona enviar_lista_alunos() para enviar a lista de alunos atualizada para o cliente recém-conectado.
        await enviar_lista_alunos()
        
        # Loop assíncrono para receber mensagens do cliente WebSocket.
        async for message in websocket:
            # Chama a função assíncrona processar_mensagem para processar a mensagem recebida do cliente.
            await processar_mensagem(websocket, message)
    except websockets.exceptions.ConnectionClosedOK:
        pass
    finally:
        # Remove o objeto WebSocket do conjunto connected_clients quando a conexão é fechada,
        # garantindo que não seja mais considerado como um cliente conectado.
        connected_clients.remove(websocket)

# Cria um servidor WebSocket usando a biblioteca websockets
# registrar_aluno é a função que será chamada para lidar com as conexões de clientes.
# "localhost" especifica que o servidor será acessível apenas localmente.
# 8765 é a porta em que o servidor estará escutando.
start_server = websockets.serve(registrar_aluno, "localhost", 8765)

# Executa o servidor até que ele seja concluído (ou seja, até que seja fechado ou ocorra um erro).
asyncio.get_event_loop().run_until_complete(start_server)

# Permite que o servidor WebSocket continue a aceitar conexões e processar eventos indefinidamente.
asyncio.get_event_loop().run_forever()
