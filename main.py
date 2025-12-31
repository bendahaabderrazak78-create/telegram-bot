import asyncio
from telethon import TelegramClient, events, errors, Button

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_ID = 33041609
API_HASH = '5f731c160b3dd9465c4e75005633685e'
BOT_TOKEN = '8492833920:AAGNDmi41iKOOVqIcsWHmw5XVO-w9oU7ybc'

SESSION_NAME = 'my_user_session'
BOT_PASSWORD = "1234"  # 🔐 TON MOT DE PASSE

# ==========================================
# 🔌 INITIALISATION
# ==========================================
bot = TelegramClient('bot_interface', API_ID, API_HASH)
user_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Variables globales
active_tasks = {}   # {chat_id: task}
task_info = {}      # {chat_id: {'targets': [], 'count': 0}}
allowed_users = set()

# ==========================================
# 🛠️ UTILITAIRES (Menu & Sécurité)
# ==========================================

def get_main_menu():
    """Génère les boutons du menu principal."""
    return [
        [Button.inline("🔑 Connexion (Login)", data=b'login'), Button.inline("🚪 Déconnexion", data=b'logout')],
        [Button.inline("🚀 Lancer Auto", data=b'auto'), Button.inline("🛑 Tout Arrêter", data=b'stop')],
        [Button.inline("📊 VOIR STATUT", data=b'status')]
    ]

async def check_access(event):
    """Vérifie si l'utilisateur est autorisé."""
    chat_id = event.chat_id
    if chat_id not in allowed_users:
        await event.respond("⛔ **Accès Refusé.**\nClique sur /start et entre le mot de passe.")
        return False
    return True

# ==========================================
# 🤖 1. DÉMARRAGE & MOT DE PASSE (/START)
# ==========================================
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    chat_id = event.chat_id
    
    # Verrouillage immédiat
    allowed_users.discard(chat_id)

    async with bot.conversation(chat_id) as conv:
        # 1. Demande mot de passe
        await conv.send_message("🔒 **BOT SÉCURISÉ**\nEntrez le mot de passe :")
        try:
            resp = await conv.get_response()
            if resp.text.strip() == BOT_PASSWORD:
                allowed_users.add(chat_id)
                await conv.send_message("🔓 **Accès Autorisé !**", buttons=get_main_menu())
            else:
                await conv.send_message("❌ **Mot de passe faux.**")
        except:
            await conv.send_message("❌ Temps écoulé.")

# ==========================================
# 🖱️ GESTION DES BOUTONS (CALLBACKS)
# ==========================================
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    chat_id = event.chat_id
    
    # Vérification sécurité
    if chat_id not in allowed_users:
        await event.answer("⛔ Non autorisé. Fais /start", alert=True)
        return

    data = event.data

    # --- 📊 BOUTON STATUS ---
    if data == b'status':
        # Vérif User Client
        is_connected = False
        try:
            if not user_client.is_connected(): await user_client.connect()
            is_connected = await user_client.is_user_authorized()
        except: pass

        # Vérif Tâche
        is_running = chat_id in active_tasks
        info = task_info.get(chat_id, {})
        nb_groups = len(info.get('targets', []))
        
        status_msg = (
            f"📊 **ÉTAT DU SYSTÈME**\n\n"
            f"👤 **Compte User :** {'✅ Connecté' if is_connected else '❌ Déconnecté'}\n"
            f"🔄 **Diffusion :** {'RUNNING 🏃' if is_running else 'STOPPED 💤'}\n"
        )
        if is_running:
            status_msg += f"🎯 **Cibles :** {nb_groups} groupes\n"

        await event.answer("Statut mis à jour !", alert=False)
        await event.edit(status_msg, buttons=get_main_menu())

    # --- 🔑 BOUTON LOGIN ---
    elif data == b'login':
        await event.answer()
        # Refresh connection
        if user_client.is_connected(): await user_client.disconnect()
        await user_client.connect()

        if await user_client.is_user_authorized():
            await event.respond("✅ **Déjà connecté !**", buttons=get_main_menu())
            return

        # On lance la conversation
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
                    await conv.send_message(f"❌ Erreur connexion : {e}", buttons=get_main_menu())
                    return
                
                me = await user_client.get_me()
                await conv.send_message(f"🎉 **Succès !** Connecté en tant que {me.first_name}", buttons=get_main_menu())

            except asyncio.TimeoutError:
                await conv.send_message("❌ Trop lent.", buttons=get_main_menu())

    # --- 🚪 BOUTON LOGOUT ---
    elif data == b'logout':
        if not user_client.is_connected(): await user_client.connect()
        
        if not await user_client.is_user_authorized():
            await event.answer("⚠️ Déjà déconnecté", alert=True)
            return

        # Stop task si existe
        if chat_id in active_tasks:
            active_tasks[chat_id].cancel()
            del active_tasks[chat_id]

        await user_client.log_out()
        await user_client.disconnect()
        await event.edit("👋 **Déconnecté avec succès.**", buttons=get_main_menu())

    # --- 🚀 BOUTON AUTO ---
    elif data == b'auto':
        await event.answer()
        
        if chat_id in active_tasks:
            await event.respond("⚠️ **Une diffusion est déjà en cours !**\nUtilisez STOP d'abord.", buttons=get_main_menu())
            return

        if not user_client.is_connected(): await user_client.connect()
        if not await user_client.is_user_authorized():
            await event.respond("❌ **Vous n'êtes pas connecté.**\nCliquez sur 'Connexion' d'abord.", buttons=get_main_menu())
            return

        async with bot.conversation(chat_id) as conv:
            try:
                await conv.send_message("🔗 **Envoyez la liste des groupes** (séparés par espace ou ligne) :")
                resp = await conv.get_response()
                targets = [t.strip() for t in resp.text.replace("\n", " ").split(" ") if t.strip()]

                if not targets:
                    await conv.send_message("❌ Liste vide.", buttons=get_main_menu())
                    return

                await conv.send_message("📝 **Envoyez le MESSAGE** à diffuser :")
                msg = (await conv.get_response()).text

                await conv.send_message("⏱️ **Temps d'attente** (en secondes) entre chaque cycle :")
                resp_t = await conv.get_response()
                if not resp_t.text.isdigit():
                    await conv.send_message("❌ Erreur: Chiffre requis.", buttons=get_main_menu())
                    return
                interval = int(resp_t.text)

                await conv.send_message(f"🚀 **Lancement sur {len(targets)} groupes !**", buttons=get_main_menu())
                
                # Sauvegarde info et lancement
                task_info[chat_id] = {'targets': targets}
                task = bot.loop.create_task(send_loop(targets, msg, interval, chat_id))
                active_tasks[chat_id] = task

            except Exception as e:
                await conv.send_message(f"❌ Erreur : {e}", buttons=get_main_menu())

    # --- 🛑 BOUTON STOP ---
    elif data == b'stop':
        if chat_id in active_tasks:
            active_tasks[chat_id].cancel()
            del active_tasks[chat_id]
            if chat_id in task_info: del task_info[chat_id]
            await event.answer("Arrêt effectué !", alert=True)
            await event.edit("🛑 **Diffusion ARRÊTÉE.**", buttons=get_main_menu())
        else:
            await event.answer("Aucune tâche en cours.", alert=True)

# ==========================================
# 🔄 BOUCLE D'ENVOI (Back-end)
# ==========================================
async def send_loop(targets, message, interval, chat_id):
    try:
        while True:
            for group in targets:
                try:
                    await user_client.send_message(group, message)
                    await asyncio.sleep(3) # Anti-flood pause
                except Exception as e:
                    print(f"Erreur envoi {group}: {e}")
            
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        if chat_id in active_tasks: del active_tasks[chat_id]
        try: await bot.send_message(chat_id, f"❌ Erreur critique boucle : {e}")
        except: pass

# ==========================================
# 🏁 MAIN
# ==========================================
async def main():
    print(f"🔐 Bot à Boutons en ligne... (Pass: {BOT_PASSWORD})")
    await bot.start(bot_token=BOT_TOKEN)
    try: await user_client.connect()
    except: pass
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
