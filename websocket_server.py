import asyncio
import websockets
import json

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
            "nome": aluno.nome,
            "nota1": aluno.nota1,
            "nota2": aluno.nota2,
            "media": aluno.media,
            "situacao": aluno.situacao
        } for aluno in alunos
    ]

    # Envia a lista de alunos para todos os clientes conectados
    await asyncio.gather(
        *[client.send(json.dumps({"action": "lista_alunos", "alunos": lista_alunos})) for client in connected_clients]
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
                "action": "registrar_aluno",
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

            # Após registrar um novo aluno, envie a lista atualizada para todos os clientes
            await enviar_lista_alunos()

        elif action == "remover_aluno":
            nome_aluno_remover = data["nome"]
            alunos = {aluno for aluno in alunos if aluno.nome != nome_aluno_remover}

            # Broadcast para todos os clientes conectados para atualizar a lista
            await asyncio.gather(
                *[client.send(json.dumps({"action": "remover_aluno", "nome": nome_aluno_remover})) for client in connected_clients]
            )

            # Após remover um aluno, envie a lista atualizada para todos os clientes
            await enviar_lista_alunos()

        elif action == "conectar_cliente":
            # Enviar lista de alunos para cliente recém-conectado
            await enviar_lista_alunos()

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
