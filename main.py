# main.py - البوت الرئيسي
import os
import asyncio
import json
from telethon import TelegramClient, events
from flask import Flask
from threading import Thread

# ==================== خادم ويب لإبقاء البوت نشطاً ====================
app = Flask('')

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Bot</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; }
            .status { color: green; font-size: 24px; }
        </style>
    </head>
    <body>
        <h1>🤖 Telegram Bot</h1>
        <p class="status">✅ Status: Running on Koyeb</p>
        <p>Free 24/7 Hosting</p>
    </body>
    </html>
    '''

# تشغيل خادم الويب في الخلفية
def run_web():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_web, daemon=True).start()

# ==================== الإعدادات ====================
API_ID = 33041609  # ضع API_ID الخاص بك هنا
API_HASH = '5f731c160b3dd9465c4e75005633685e'  # ضع API_HASH هنا
BOT_TOKEN = '8492833920:AAGNDmi41iKOOVqIcsWHmw5XVO-w9oU7ybc'  # ضع توكن البوت هنا

# ==================== البوت الرئيسي ====================
async def main():
    print("🚀 بدء تشغيل البوت على Koyeb...")
    print("="*50)
    
    # 1. إنشاء مجلد للجلسات
    os.makedirs('sessions', exist_ok=True)
    
    try:
        # 2. تسجيل دخول حسابك الشخصي
        print("🔐 محاولة تسجيل دخول حسابك...")
        user_client = TelegramClient('sessions/user', API_ID, API_HASH)
        await user_client.connect()
        
        if not await user_client.is_user_authorized():
            print("⚠️ حسابك غير مسجل دخول")
            print("📱 ستحتاج لتسجيل الدخول أول مرة فقط")
            # يمكنك إضافة كود تسجيل الدخول هنا لاحقاً
        
        # 3. تشغيل بوت التليجرام
        print("🤖 تشغيل بوت التليجرام...")
        bot = await TelegramClient('sessions/bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
        
        # 4. إضافة الأوامر
        @bot.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            await event.reply('''
👋 **مرحباً بك!**

✅ البوت يعمل على Koyeb مجاناً 24/7

🔹 **الأوامر المتاحة:**
• /start - عرض هذه الرسالة
• /send - إرسال رسالة (قريباً)
• /status - حالة البوت
• /me - معلومات حسابك

⚡ **المطور:** Abderrazak
            ''')
        
        @bot.on(events.NewMessage(pattern='/status'))
        async def status_handler(event):
            await event.reply('✅ **الحالة:** البوت يعمل بنجاح!')
        
        @bot.on(events.NewMessage(pattern='/me'))
        async def me_handler(event):
            try:
                me = await user_client.get_me()
                await event.reply(f'''
👤 **معلومات حسابك:**

🏷️ **الاسم:** {me.first_name}
📞 **الهاتف:** {me.phone}
🆔 **ID:** {me.id}
                ''')
            except:
                await event.reply('❌ حسابك الشخصي غير متصل')
        
        # 5. عرض معلومات البوت
        bot_info = await bot.get_me()
        print(f"✅ البوت يعمل: @{bot_info.username}")
        print(f"🔗 رابط البوت: https://t.me/{bot_info.username}")
        
        print("\n" + "="*50)
        print("🎉 **جاهز للاستخدام!**")
        print("1. اذهب إلى Telegram")
        print(f"2. ابحث عن @{bot_info.username}")
        print("3. اكتب /start")
        print("="*50)
        
        # 6. إبقاء البوت يعمل للأبد
        await bot.run_until_disconnected()
        
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        import traceback
        traceback.print_exc()

# ==================== تشغيل البوت ====================
if __name__ == '__main__':
    asyncio.run(main())