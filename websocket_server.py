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

async def registrar_aluno(websocket, path):
    global alunos, connected_clients
    connected_clients.add(websocket)

    try:
        async for message in websocket:
            data = json.loads(message)
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
    except websockets.exceptions.ConnectionClosedOK:
        pass
    finally:
        connected_clients.remove(websocket)

start_server = websockets.serve(registrar_aluno, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
