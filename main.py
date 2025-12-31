import os
import asyncio
from telethon import TelegramClient, events, Button, errors
from telethon.sessions import StringSession

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_ID = int(os.getenv("API_ID", 33041609))
API_HASH = os.getenv("API_HASH", "5f731c160b3dd9465c4e75005633685e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8492833920:AAGNDmi41iKOOVqIcsWHmw5XVO-w9oU7ybc")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "1234")

# Récupération de la session si elle existe déjà dans Koyeb
SAVED_SESSION = os.getenv("STRING_SESSION")

# ==========================================
# 🔌 INITIALISATION
# ==========================================
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Initialisation intelligente du client utilisateur
if SAVED_SESSION:
    user_client = TelegramClient(StringSession(SAVED_SESSION), API_ID, API_HASH)
else:
    # Session vide en mémoire (pour permettre le login via le bot)
    user_client = TelegramClient(StringSession(), API_ID, API_HASH)

# Variables globales
active_tasks = {}
allowed_users = set()

# ==========================================
# 🛠️ MENU ET UTILITAIRES
# ==========================================
def get_main_menu():
    return [
        [Button.inline("🔑 Connexion", data=b'login'), Button.inline("🚪 Déconnexion", data=b'logout')],
        [Button.inline("🚀 Lancer Auto", data=b'auto'), Button.inline("🛑 Tout Arrêter", data=b'stop')],
        [Button.inline("📊 VOIR STATUT", data=b'status')]
    ]

# ==========================================
# 🤖 COMMANDE START (Sécurité)
# ==========================================
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    chat_id = event.chat_id
    allowed_users.discard(chat_id) # Verrouillage
    
    async with bot.conversation(chat_id) as conv:
        await conv.send_message("🔒 **SÉCURITÉ**\nEntrez le mot de passe :")
        try:
            resp = await conv.get_response()
            if resp.text.strip() == BOT_PASSWORD:
                allowed_users.add(chat_id)
                await conv.send_message("🔓 **Accès Autorisé !**", buttons=get_main_menu())
            else:
                await conv.send_message("❌ Mot de passe incorrect.")
        except:
            await conv.send_message("❌ Temps écoulé.")

# ==========================================
# 🖱️ GESTION DES BOUTONS
# ==========================================
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    chat_id = event.chat_id
    if chat_id not in allowed_users:
        await event.answer("⛔ Fais /start d'abord", alert=True)
        return

    data = event.data

    # --- 📊 STATUT ---
    if data == b'status':
        is_connected = False
        try:
            if not user_client.is_connected(): await user_client.connect()
            is_connected = await user_client.is_user_authorized()
        except: pass
        
        is_running = chat_id in active_tasks
        msg = f"📊 **STATUT**\n👤 Compte : {'✅ Connecté' if is_connected else '❌ Déconnecté'}\n🔄 Auto : {'RUNNING 🏃' if is_running else 'STOPPED 💤'}"
        await event.edit(msg, buttons=get_main_menu())

    # --- 🔑 LOGIN (CONNEXION) ---
    elif data == b'login':
        await event.answer()
        # 1. Vérifier si déjà connecté
        if not user_client.is_connected(): await user_client.connect()
        if await user_client.is_user_authorized():
            await event.respond("✅ Déjà connecté !", buttons=get_main_menu())
            return

        # 2. Procédure de connexion
        async with bot.conversation(chat_id) as conv:
            try:
                await conv.send_message("📱 **Entrez votre numéro** (ex: `+21355...`) :")
                phone = (await conv.get_response()).text.strip().replace(" ", "")

                await conv.send_message("⏳ Envoi du code...")
                try:
                    await user_client.send_code_request(phone)
                except Exception as e:
                    await conv.send_message(f"❌ Erreur : {e}", buttons=get_main_menu())
                    return

                await conv.send_message("📩 **Entrez le code reçu** sur Telegram :")
                code = (await conv.get_response()).text.strip()

                try:
                    await user_client.sign_in(phone, code)
                except errors.SessionPasswordNeededError:
                    await conv.send_message("🔐 **Mot de passe 2FA** requis :")
                    pwd = (await conv.get_response()).text
                    await user_client.sign_in(password=pwd)
                except Exception as e:
                    await conv.send_message(f"❌ Erreur Login : {e}", buttons=get_main_menu())
                    return

                # 3. SAUVEGARDE POUR KOYEB
                # On récupère la StringSession générée
                session_string = user_client.session.save()
                
                await conv.send_message(
                    f"🎉 **Connecté !**\n\n"
                    f"⚠️ **IMPORTANT POUR KOYEB** ⚠️\n"
                    f"Cette connexion est temporaire. Pour qu'elle reste après un redémarrage, "
                    f"copiez le code ci-dessous et ajoutez-le dans les variables Koyeb sous le nom `STRING_SESSION` :\n\n"
                    f"`{session_string}`",
                    buttons=get_main_menu()
                )

            except asyncio.TimeoutError:
                await conv.send_message("❌ Trop lent.", buttons=get_main_menu())

    # --- 🚪 LOGOUT (DÉCONNEXION) ---
    elif data == b'logout':
        if not user_client.is_connected(): await user_client.connect()
        if await user_client.is_user_authorized():
            await user_client.log_out()
            await user_client.disconnect()
            await event.edit("👋 **Déconnecté avec succès.**", buttons=get_main_menu())
        else:
            await event.answer("Déjà déconnecté.", alert=True)

    # --- 🚀 AUTO ---
    elif data == b'auto':
        await event.answer()
        if chat_id in active_tasks:
            await event.respond("⚠️ Déjà en cours !", buttons=get_main_menu())
            return

        try:
            if not user_client.is_connected(): await user_client.connect()
            if not await user_client.is_user_authorized():
                await event.respond("❌ **Non connecté !** Utilisez le bouton Connexion.", buttons=get_main_menu())
                return
        except:
             await event.respond("❌ Erreur de connexion client.", buttons=get_main_menu())
             return

        async with bot.conversation(chat_id) as conv:
            await conv.send_message("🔗 **Liste des Groupes** (séparés par espace) :")
            resp = await conv.get_response()
            targets = resp.text.split()
            if not targets:
                await conv.send_message("❌ Liste vide.", buttons=get_main_menu())
                return

            await conv.send_message("📝 **Message** :")
            msg = (await conv.get_response()).text

            await conv.send_message("⏱️ **Pause** (secondes) :")
            try:
                interval = int((await conv.get_response()).text)
            except:
                await conv.send_message("❌ Chiffre requis.", buttons=get_main_menu())
                return

            task = bot.loop.create_task(send_loop(targets, msg, interval, chat_id))
            active_tasks[chat_id] = task
            await conv.send_message(f"🚀 **Lancement sur {len(targets)} groupes !**", buttons=get_main_menu())

    # --- 🛑 STOP ---
    elif data == b'stop':
        if chat_id in active_tasks:
            active_tasks[chat_id].cancel()
            del active_tasks[chat_id]
            await event.edit("🛑 **Arrêté.**", buttons=get_main_menu())
        else:
            await event.answer("Rien à arrêter.", alert=True)

# ==========================================
# 🔄 BOUCLE D'ENVOI
# ==========================================
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
    except asyncio.CancelledError:
        pass
    except Exception as e:
        if chat_id in active_tasks: del active_tasks[chat_id]

# ==========================================
# 🚀 MAIN
# ==========================================
async def main():
    print("🤖 Bot Cloud Ready (Login/Logout) en ligne...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
