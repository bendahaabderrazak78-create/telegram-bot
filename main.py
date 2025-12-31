import os
import asyncio
import threading
import logging
from flask import Flask
from telethon import TelegramClient, events, Button, errors
from telethon.sessions import StringSession

# ==========================================
# 📝 LOGGING (POUR VOIR LES ERREURS)
# ==========================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 🌐 SERVEUR WEB (KEEP ALIVE KOYEB)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot en ligne ! (Status: 200 OK)"

def run_web_server():
    # Koyeb utilise souvent le port 8080 par défaut
    port = int(os.environ.get("PORT", 8080))
    print(f"🌍 Serveur Web démarré sur le port {port}")
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ Erreur Web Server: {e}")

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_ID = int(os.getenv("API_ID", 33041609))
API_HASH = os.getenv("API_HASH", "5f731c160b3dd9465c4e75005633685e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8492833920:AAGNDmi41iKOOVqIcsWHmw5XVO-w9oU7ybc")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "1234")
SAVED_SESSION = os.getenv("STRING_SESSION")

# ==========================================
# 🔌 INITIALISATION CLIENTS
# ==========================================
print("🔄 Initialisation des clients Telegram...")
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_client = None
if SAVED_SESSION:
    try:
        user_client = TelegramClient(StringSession(SAVED_SESSION), API_ID, API_HASH)
        print("✅ StringSession détectée.")
    except Exception as e:
        print(f"⚠️ Erreur StringSession (Session ignorée) : {e}")
        user_client = TelegramClient(StringSession(), API_ID, API_HASH)
else:
    print("⚠️ Aucune StringSession trouvée. Mode temporaire.")
    user_client = TelegramClient(StringSession(), API_ID, API_HASH)

active_tasks = {}
allowed_users = set()

# ==========================================
# 🛠️ FONCTIONS BOT
# ==========================================
def get_main_menu():
    return [
        [Button.inline("🔑 Connexion", data=b'login'), Button.inline("🚪 Déconnexion", data=b'logout')],
        [Button.inline("🚀 Lancer Auto", data=b'auto'), Button.inline("🛑 Tout Arrêter", data=b'stop')],
        [Button.inline("📊 VOIR STATUT", data=b'status')]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    chat_id = event.chat_id
    allowed_users.discard(chat_id)
    async with bot.conversation(chat_id) as conv:
        await conv.send_message("🔒 **SÉCURITÉ**\nEntrez le mot de passe :")
        try:
            resp = await conv.get_response()
            if resp.text.strip() == BOT_PASSWORD:
                allowed_users.add(chat_id)
                await conv.send_message("🔓 **Accès Autorisé !**", buttons=get_main_menu())
            else:
                await conv.send_message("❌ Faux.")
        except:
            await conv.send_message("❌ Temps écoulé.")

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    chat_id = event.chat_id
    if chat_id not in allowed_users:
        await event.answer("⛔ Fais /start d'abord", alert=True)
        return
    data = event.data

    # --- STATUS ---
    if data == b'status':
        is_connected = False
        try:
            if not user_client.is_connected(): await user_client.connect()
            is_connected = await user_client.is_user_authorized()
        except: pass
        is_running = chat_id in active_tasks
        msg = f"📊 **STATUT**\n👤 Compte : {'✅ Connecté' if is_connected else '❌ Déconnecté'}\n🔄 Auto : {'RUNNING 🏃' if is_running else 'STOPPED 💤'}"
        await event.edit(msg, buttons=get_main_menu())

    # --- LOGIN ---
    elif data == b'login':
        await event.answer()
        try:
            if not user_client.is_connected(): await user_client.connect()
        except Exception as e:
            await event.respond(f"❌ Erreur connexion client: {e}", buttons=get_main_menu())
            return

        if await user_client.is_user_authorized():
            await event.respond("✅ Déjà connecté !", buttons=get_main_menu())
            return

        async with bot.conversation(chat_id) as conv:
            try:
                await conv.send_message("📱 **Numéro** (ex: `+21355...`) :")
                phone = (await conv.get_response()).text.strip().replace(" ", "")
                await conv.send_message("⏳ Envoi code...")
                try: await user_client.send_code_request(phone)
                except Exception as e: 
                    await conv.send_message(f"❌ Erreur : {e}", buttons=get_main_menu())
                    return
                
                await conv.send_message("📩 **Code Telegram** :")
                code = (await conv.get_response()).text.strip()
                try:
                    await user_client.sign_in(phone, code)
                except errors.SessionPasswordNeededError:
                    await conv.send_message("🔐 **Pass 2FA** :")
                    pwd = (await conv.get_response()).text
                    await user_client.sign_in(password=pwd)
                except Exception as e:
                    await conv.send_message(f"❌ Erreur : {e}", buttons=get_main_menu())
                    return

                session_string = user_client.session.save()
                await conv.send_message(
                    f"🎉 **Connecté !**\n⚠️ **COPIE CE CODE DANS KOYEB (VAR: STRING_SESSION)** :\n\n`{session_string}`",
                    buttons=get_main_menu()
                )
            except asyncio.TimeoutError:
                await conv.send_message("❌ Trop lent.", buttons=get_main_menu())

    # --- LOGOUT ---
    elif data == b'logout':
        if not user_client.is_connected(): await user_client.connect()
        if await user_client.is_user_authorized():
            await user_client.log_out()
            await user_client.disconnect()
            await event.edit("👋 **Déconnecté.**", buttons=get_main_menu())
        else:
            await event.answer("Déjà fait.", alert=True)

    # --- AUTO ---
    elif data == b'auto':
        await event.answer()
        if chat_id in active_tasks:
            await event.respond("⚠️ Déjà en cours !", buttons=get_main_menu())
            return
        
        try:
            if not user_client.is_connected(): await user_client.connect()
            if not await user_client.is_user_authorized():
                await event.respond("❌ Non connecté !", buttons=get_main_menu())
                return
        except: return

        async with bot.conversation(chat_id) as conv:
            await conv.send_message("🔗 **Groupes** (séparés par espace) :")
            resp = await conv.get_response()
            targets = resp.text.split()
            if not targets:
                await conv.send_message("❌ Vide.", buttons=get_main_menu())
                return
            
            await conv.send_message("📝 **Message** :")
            msg = (await conv.get_response()).text
            
            await conv.send_message("⏱️ **Pause** (sec) :")
            try: interval = int((await conv.get_response()).text)
            except: 
                await conv.send_message("❌ Chiffre svp.", buttons=get_main_menu())
                return

            task = bot.loop.create_task(send_loop(targets, msg, interval, chat_id))
            active_tasks[chat_id] = task
            await conv.send_message("🚀 **C'est parti !**", buttons=get_main_menu())

    # --- STOP ---
    elif data == b'stop':
        if chat_id in active_tasks:
            active_tasks[chat_id].cancel()
            del active_tasks[chat_id]
            await event.edit("🛑 **Arrêté.**", buttons=get_main_menu())
        else:
            await event.answer("Rien à arrêter.", alert=True)

async def send_loop(targets, message, interval, chat_id):
    try:
        while True:
            for group in targets:
                try:
                    await user_client.send_message(group, message)
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"Erreur {group}: {e}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError: pass
    except Exception as e:
        if chat_id in active_tasks: del active_tasks[chat_id]

# ==========================================
# 🚀 MAIN (DÉMARRAGE ROBUSTE)
# ==========================================
if __name__ == '__main__':
    print("🚀 Démarrage du script...")
    
    # 1. Lancer le serveur Web (Thread)
    try:
        server_thread = threading.Thread(target=run_web_server)
        server_thread.daemon = True
        server_thread.start()
        print("✅ Thread Web Server lancé.")
    except Exception as e:
        print(f"❌ Echec lancement Web Server: {e}")

    # 2. Lancer la boucle principale Telegram
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.run_until_disconnected())
    except KeyboardInterrupt:
        print("🛑 Arrêt manuel.")
    except Exception as e:
        print(f"❌ CRASH DU BOT : {e}")
