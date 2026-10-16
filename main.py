from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import asyncio, threading, os
from flask import Flask

API_ID = 32695956
API_HASH = '8d939c8130ea03c01cd9abe6a6e83d7a'
GRUPO = -1003764262854
TOPIC = 733141
CANAL = 'https://t.me/Horny_J'
SESSION = os.environ.get("SESSION_STRING")

app = Flask(__name__)
@app.route('/')
def home(): return "Bot vivo"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000))), daemon=True).start()

# --- PROGRESO EN TELEGRAM, NO EN RENDER ---
async def cargar_desde_telegram(client):
    # Busca en tus Mensajes Guardados el ultimo PROGRESO_BOT:12345
    try:
        async for m in client.iter_messages('me', limit=30):
            if (m.text or "").startswith("PROGRESO_BOT:"):
                try:
                    last = int(m.text.split(":")[1].strip())
                    print(f"RECUPERADO PROGRESO DESDE TELEGRAM: {last}")
                    return last
                except: pass
    except Exception as e:
        print(f"No pude leer progreso de Telegram: {e}")
    print("NO HABIA PROGRESO, EMPIEZO DE 0")
    return 0

async def guardar_en_telegram(client, last_id):
    try:
        # Borra el viejo para no llenarte de mensajes
        async for m in client.iter_messages('me', limit=30):
            if (m.text or "").startswith("PROGRESO_BOT:"):
                await m.delete()
        await client.send_message('me', f"PROGRESO_BOT:{last_id}")
    except Exception as e:
        print(f"No pude guardar progreso: {e}")

async def copiar_con_reintento(client, d, m):
    # No suelta el mensaje hasta que lo copia
    while True:
        try:
            if m.media:
                await client.send_file(d, m.media, caption=m.text, reply_to=TOPIC)
            else:
                await client.send_message(d, m.text, reply_to=TOPIC)
            print(f"Copiado {m.id}")
            return True
        except FloodWaitError as e:
            print(f"TELEGRAM ME FRENO {e.seconds}s en {m.id} - me duermo y sigo en el MISMO")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"Error en {m.id}: {e} - reintento MISMO mensaje en 5s")
            await asyncio.sleep(5)

async def main():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()
    print("CLIENTE CONECTADO OK")

    # 1. Cargo desde Telegram, no desde archivo
    last_id = await cargar_desde_telegram(client)
    print(f"ARRANCO DESDE ID: {last_id}")

    o = await client.get_entity(CANAL)
    d = await client.get_entity(GRUPO)

    while True:
        try:
            async for m in client.iter_messages(o, min_id=last_id, reverse=True):
                # Si no tiene media, solo avanzo en memoria, NO guardo todavia
                if not (m.media or (m.text or "").startswith("https://telegra.ph")):
                    last_id = m.id
                    continue

                # Si tiene media, lo copio hasta que salga
                await copiar_con_reintento(client, d, m)
                last_id = m.id
                # Solo guardo cuando ya copio de verdad, cada 20 para no spamear tus guardados
                if m.id % 20 == 0:
                    await guardar_en_telegram(client, last_id)
                await asyncio.sleep(1)

            # Termino todo, guardo final
            await guardar_en_telegram(client, last_id)
            print("HISTORIAL LISTO - EN VIVO")
            break
        except Exception as e:
            print(f"SE CAYO ITER: {e} - Guardo y reintento en 10s desde {last_id}")
            await guardar_en_telegram(client, last_id)
            await asyncio.sleep(10)

    @client.on(events.NewMessage(chats=CANAL))
    async def h(e):
        if not (e.message.media or (e.message.text or "").startswith("https://telegra.ph")): return
        await copiar_con_reintento(client, d, e.message)
        await guardar_en_telegram(client, e.message.id)

    await client.run_until_disconnected()

asyncio.run(main())
