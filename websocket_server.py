import asyncio
import websockets
import json
from reportlab.pdfgen import canvas

class Aluno:
    def __init__(self, nome, nota1, nota2):
        self.nome = nome
        self.nota1 = nota1
        self.nota2 = nota2
        self.media = (nota1 + nota2) / 2
        self.situacao = "Aprovado" if self.media >= 7 else "Reprovado"

alunos = set()
connected_clients = set()

async def enviar_lista_alunos():
    global alunos
    lista_alunos = [
        {
            "posicao": i + 1,
            "nome": aluno.nome,
            "nota1": aluno.nota1,
            "nota2": aluno.nota2,
            "media": aluno.media,
            "situacao": aluno.situacao
        } for i, aluno in enumerate(sorted(alunos, key=lambda x: x.media, reverse=True))
    ]

    # Envia a lista de alunos para todos os clientes conectados
    await asyncio.gather(
        *[client.send(json.dumps({"action": "lista_alunos", "alunos": lista_alunos})) for client in connected_clients]
    )

async def gerar_relatorio():
    global alunos

    # Crie um documento PDF usando a biblioteca reportlab
    pdf_filename = "relatorio_alunos.pdf"
    c = canvas.Canvas(pdf_filename)
    c.drawString(100, 800, "Relatório de Alunos")

    # Adicione os dados dos alunos ao PDF
    y = 780
    for i, aluno in enumerate(sorted(alunos, key=lambda x: x.media, reverse=True), start=1):
        c.drawString(100, y, f"POS: {i}")
        c.drawString(150, y, f"Nome: {aluno.nome}")
        c.drawString(150, y - 15, f"Nota 1: {aluno.nota1}")
        c.drawString(150, y - 30, f"Nota 2: {aluno.nota2}")
        c.drawString(150, y - 45, f"Média: {aluno.media}")
        c.drawString(150, y - 60, f"Situação: {aluno.situacao}")
        y -= 80

    # Salve o documento PDF
    c.save()

    # Envie o nome do arquivo para os clientes baixarem
    await asyncio.gather(
        *[client.send(json.dumps({"action": "baixar_relatorio", "filename": pdf_filename})) for client in connected_clients]
    )

async def processar_mensagem(websocket, message):
    global alunos, connected_clients

    try:
        data = json.loads(message)
        action = data.get("action")

        if action == "registrar_aluno":
            nome = data["nome"]
            nota1 = float(data["nota1"])
            nota2 = float(data["nota2"])

            aluno = Aluno(nome, nota1, nota2)
            alunos.add(aluno)

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

async def registrar_aluno(websocket, path):
    global connected_clients
    connected_clients.add(websocket)

    try:
        # Enviar lista de alunos quando o cliente se conectar
        await enviar_lista_alunos()

        async for message in websocket:
            await processar_mensagem(websocket, message)
    except websockets.exceptions.ConnectionClosedOK:
        pass
    finally:
        connected_clients.remove(websocket)

start_server = websockets.serve(registrar_aluno, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
