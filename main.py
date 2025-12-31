import os
import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# Le code cherche d'abord dans Koyeb (os.getenv). 
# S'il ne trouve pas, il utilise tes valeurs par défaut ci-dessous.

API_ID = int(os.getenv("API_ID", 33041609))
API_HASH = os.getenv("API_HASH", "5f731c160b3dd9465c4e75005633685e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8492833920:AAGNDmi41iKOOVqIcsWHmw5XVO-w9oU7ybc")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "1234")

# ⚠️ IMPORTANT : Sur Koyeb, cette variable doit être définie dans les Settings.
# Sinon, le bot ne pourra pas se connecter à ton compte perso.
STRING_SESSION = os.getenv("STRING_SESSION") 

# ==========================================
# 🔌 INITIALISATION
# ==========================================

# 1. Connexion au Bot (Interface)
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# 2. Connexion au Compte Utilisateur (Celui qui envoie)
if STRING_SESSION:
    # Mode Cloud (Koyeb/GitHub)
    user_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
else:
    # Mode Local (Test sur PC sans StringSession) - Moins fiable sur Koyeb
    print("⚠️ ATTENTION : Pas de STRING_SESSION détectée. Le bot risque de demander le code à chaque redémarrage.")
    user_client = TelegramClient('user_session', API_ID, API_HASH)

# Variables de gestion
active_tasks = {}
allowed_users = set()

# ==========================================
# 🛠️ FONCTIONS UTILITAIRES
# ==========================================
def get_main_menu():
    """Boutons du menu principal"""
    return [
        [Button.inline("🚀 Lancer Auto", data=b'auto'), Button.inline("🛑 Tout Arrêter", data=b'stop')],
        [Button.inline("📊 VOIR STATUT", data=b'status')]
    ]

# ==========================================
# 🤖 COMMANDES (START & MENU)
# ==========================================
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    chat_id = event.chat_id
    # On verrouille l'utilisateur pour forcer le mot de passe
    allowed_users.discard(chat_id)
    
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
# 🖱️ GESTION DES CLICS (CALLBACKS)
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
            # On tente de connecter le client user s'il ne l'est pas
            if not user_client.is_connected():
                await user_client.connect()
            is_connected = await user_client.is_user_authorized()
        except: pass

        is_running = chat_id in active_tasks
        
        msg = (
            f"📊 **ÉTAT DU BOT**\n\n"
            f"👤 Compte Perso : {'✅ Connecté' if is_connected else '❌ Déconnecté (Ajoute STRING_SESSION)'}\n"
            f"🔄 Diffusion : {'EN COURS 🏃' if is_running else 'ARRÊTÉE 💤'}"
        )
        await event.edit(msg, buttons=get_main_menu())

    # --- 🚀 AUTO ---
    elif data == b'auto':
        await event.answer()
        
        if chat_id in active_tasks:
            await event.respond("⚠️ Déjà en cours !", buttons=get_main_menu())
            return

        # Vérification connexion
        try:
            await user_client.connect()
            if not await user_client.is_user_authorized():
                await event.respond("❌ **Erreur Compte !**\nLe compte utilisateur n'est pas connecté.\nAjoute la variable `STRING_SESSION` dans Koyeb.", buttons=get_main_menu())
                return
        except Exception as e:
            await event.respond(f"❌ Erreur technique : {e}")
            return

        async with bot.conversation(chat_id) as conv:
            await conv.send_message("🔗 **Liste des Groupes** (séparés par espace ou saut de ligne) :")
            resp = await conv.get_response()
            targets = resp.text.split()

            if not targets:
                await conv.send_message("❌ Liste vide.", buttons=get_main_menu())
                return

            await conv.send_message("📝 **Message** à envoyer :")
            msg_text = (await conv.get_response()).text

            await conv.send_message("⏱️ **Pause** entre les cycles (en secondes) :")
            try:
                interval = int((await conv.get_response()).text)
            except:
                await conv.send_message("❌ Il faut un nombre.", buttons=get_main_menu())
                return

            await conv.send_message(f"🚀 **Lancement sur {len(targets)} groupes !**", buttons=get_main_menu())
            
            # Lancement tâche de fond
            task = bot.loop.create_task(send_loop(targets, msg_text, interval, chat_id))
            active_tasks[chat_id] = task

    # --- 🛑 STOP ---
    elif data == b'stop':
        if chat_id in active_tasks:
            active_tasks[chat_id].cancel()
            del active_tasks[chat_id]
            await event.answer("Arrêt confirmé !", alert=True)
            await event.edit("🛑 **Diffusion stoppée.**", buttons=get_main_menu())
        else:
            await event.answer("Rien ne tourne actuellement.", alert=True)

# ==========================================
# 🔄 LA BOUCLE D'ENVOI
# ==========================================
async def send_loop(targets, message, interval, chat_id):
    try:
        while True:
            for group in targets:
                try:
                    await user_client.send_message(group, message)
                    # Pause de sécurité (3s) entre chaque envoi pour éviter le flood
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"Erreur envoi {group}: {e}")
            
            # Pause avant le prochain cycle complet
            await asyncio.sleep(interval)
            
    except asyncio.CancelledError:
        pass # Arrêt propre
    except Exception as e:
        if chat_id in active_tasks: del active_tasks[chat_id]
        print(f"Erreur critique: {e}")

# ==========================================
# 🚀 MAIN
# ==========================================
async def main():
    print("🤖 Bot démarré...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
