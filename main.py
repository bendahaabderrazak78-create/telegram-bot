# main.py - البوت مع نظام تسجيل الدخول
import os
import asyncio
import json
from telethon import TelegramClient, events
from flask import Flask
from threading import Thread

# ==================== خادم ويب ====================
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
        <p class="status">✅ Status: Running with Login System</p>
        <p>Free 24/7 Hosting on Koyeb</p>
    </body>
    </html>
    '''

def run_web():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_web, daemon=True).start()

# ==================== الإعدادات ====================
API_ID = int(os.environ.get('API_ID', '33041609'))
API_HASH = os.environ.get('API_HASH', '5f731c160b3dd9465c4e75005633685e')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8492833920:AAGNDmi41iKOOVqIcsWHmw5XVO-w9oU7ybc')

# ملف لحفظ بيانات المستخدمين
USERS_FILE = 'users_data.json'

# ==================== نظام إدارة المستخدمين ====================
class UserManager:
    def __init__(self):
        self.users_file = USERS_FILE
        self.users = self.load_users()
    
    def load_users(self):
        """تحميل بيانات المستخدمين"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_users(self):
        """حفظ بيانات المستخدمين"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def add_user(self, user_id, phone, session_data=None):
        """إضافة مستخدم جديد"""
        user_id = str(user_id)
        self.users[user_id] = {
            'phone': phone,
            'session': session_data,
            'logged_in': session_data is not None,
            'added_at': str(asyncio.get_event_loop().time())
        }
        self.save_users()
    
    def get_user(self, user_id):
        """الحصول على بيانات مستخدم"""
        return self.users.get(str(user_id))
    
    def is_logged_in(self, user_id):
        """تحقق إذا كان المستخدم مسجل دخول"""
        user = self.get_user(user_id)
        return user and user.get('logged_in', False)

user_manager = UserManager()

# ==================== نظام البوت ====================
async def main():
    print("🚀 بدء تشغيل البوت مع نظام تسجيل الدخول...")
    
    # إنشاء مجلد الجلسات
    os.makedirs('sessions', exist_ok=True)
    
    # تشغيل البوت
    bot = await TelegramClient('sessions/bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    
    # ==================== الأوامر ====================
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        user_id = event.sender_id
        user = user_manager.get_user(user_id)
        
        if user and user.get('logged_in'):
            await event.reply(f'''
👋 **مرحباً بعودتك!**

✅ **حسابك:** {user['phone']}
🔹 **مسجل دخول منذ:** {user.get('added_at', 'غير معروف')}

📋 **الأوامر:**
• /logout - تسجيل الخروج
• /myinfo - معلومات حسابك
• /send - إرسال رسالة
• /status - حالة النظام
            ''')
        else:
            await event.reply('''
👋 **مرحباً بك في نظام تسجيل الدخول!**

🔐 **لتسجيل دخول حسابك الشخصي:**
1. اضغط /login
2. أرسل رقم هاتفك
3. أرسل كود التحقق

📋 **الأوامر:**
• /login - تسجيل دخول جديد
• /help - المساعدة
            ''')
    
    @bot.on(events.NewMessage(pattern='/login'))
    async def login_handler(event):
        user_id = event.sender_id
        
        # إذا كان مسجلاً دخولاً مسبقاً
        if user_manager.is_logged_in(user_id):
            await event.reply('✅ أنت مسجل دخول بالفعل! استخدم /logout أولاً.')
            return
        
        async with bot.conversation(event.chat_id, timeout=300) as conv:
            try:
                # طلب رقم الهاتف
                await conv.send_message("📱 **أرسل رقم هاتفك مع رمز الدولة:**\nمثال: +213552959083")
                phone_msg = await conv.get_response()
                phone = phone_msg.text.strip()
                
                # إنشاء جلسة للمستخدم
                session_file = f'sessions/user_{user_id}'
                user_client = TelegramClient(session_file, API_ID, API_HASH)
                await user_client.connect()
                
                # إرسال كود التحقق
                await conv.send_message(f"⏳ جاري إرسال كود التحقق إلى {phone}...")
                sent_code = await user_client.send_code_request(phone)
                
                # طلب الكود
                await conv.send_message("🔢 **أرسل كود التحقق المكون من 5 أرقام:**")
                code_msg = await conv.get_response()
                code = code_msg.text.strip()
                
                # محاولة تسجيل الدخول
                try:
                    await user_client.sign_in(phone, code)
                    await conv.send_message("✅ **تم تسجيل الدخول بنجاح!**")
                    
                    # حفظ بيانات المستخدم
                    user_manager.add_user(user_id, phone, 'session_active')
                    
                    # الحصول على معلومات الحساب
                    me = await user_client.get_me()
                    await conv.send_message(f'''
📊 **معلومات حسابك:**

👤 **الاسم:** {me.first_name} {me.last_name or ""}
📞 **الهاتف:** {me.phone}
🆔 **ID:** {me.id}
                    ''')
                    
                except Exception as e:
                    if "two step" in str(e).lower():
                        await conv.send_message("🔐 **هذا الحساب يحتاج كلمة مرور ثنائية:**")
                        password_msg = await conv.get_response()
                        await user_client.sign_in(password=password_msg.text)
                        await conv.send_message("✅ **تم التسجيل مع التحقق الثنائي!**")
                        user_manager.add_user(user_id, phone, 'session_active')
                    else:
                        await conv.send_message(f"❌ **فشل تسجيل الدخول:** {str(e)}")
                
                await user_client.disconnect()
                
            except asyncio.TimeoutError:
                await event.reply("⏰ انتهت المهلة، حاول /login مرة أخرى")
            except Exception as e:
                await event.reply(f"❌ **حدث خطأ:** {str(e)}")
    
    @bot.on(events.NewMessage(pattern='/logout'))
    async def logout_handler(event):
        user_id = event.sender_id
        
        if user_manager.is_logged_in(user_id):
            # حذف ملف الجلسة
            session_file = f'sessions/user_{user_id}.session'
            if os.path.exists(session_file):
                os.remove(session_file)
            
            # تحديث بيانات المستخدم
            user = user_manager.get_user(user_id)
            if user:
                user['logged_in'] = False
                user_manager.save_users()
            
            await event.reply("✅ **تم تسجيل الخروج بنجاح!**")
        else:
            await event.reply("❌ **أنت غير مسجل دخول!**")
    
    @bot.on(events.NewMessage(pattern='/myinfo'))
    async def myinfo_handler(event):
        user_id = event.sender_id
        user = user_manager.get_user(user_id)
        
        if user and user.get('logged_in'):
            await event.reply(f'''
📊 **معلومات حسابك:**

📞 **الهاتف:** {user['phone']}
🔐 **الحالة:** ✅ مسجل دخول
📅 **تم الإضافة:** {user.get('added_at', 'غير معروف')}
👥 **المستخدمين المسجلين:** {len(user_manager.users)}
            ''')
        else:
            await event.reply("❌ **أنت غير مسجل دخول! استخدم /login أولاً.**")
    
    @bot.on(events.NewMessage(pattern='/send'))
    async def send_handler(event):
        user_id = event.sender_id
        
        if not user_manager.is_logged_in(user_id):
            await event.reply("❌ **يجب تسجيل الدخول أولاً! استخدم /login**")
            return
        
        await event.reply("📨 **ميزة الإرسال قريباً...**\n(سيتم إضافتها في التحديث القادم)")
    
    @bot.on(events.NewMessage(pattern='/status'))
    async def status_handler(event):
        await event.reply(f'''
📊 **حالة النظام:**

✅ **البوت:** نشط
👥 **المستخدمون:** {len(user_manager.users)} مسجلين
🔐 **المسجلون دخولاً:** {sum(1 for u in user_manager.users.values() if u.get('logged_in'))}
⚡ **المطور:** Abderrazak
        ''')
    
    @bot.on(events.NewMessage(pattern='/help'))
    async def help_handler(event):
        await event.reply('''
📚 **قائمة الأوامر:**

🔐 **التسجيل:**
• /login - تسجيل دخول حسابك
• /logout - تسجيل الخروج
• /myinfo - معلومات حسابك

🔧 **عامة:**
• /start - بدء البوت
• /status - حالة النظام
• /help - هذه المساعدة

📨 **الإرسال:**
• /send - إرسال رسالة (قريباً)
        ''')
    
    # ==================== بدء التشغيل ====================
    bot_info = await bot.get_me()
    print(f"✅ البوت يعمل: @{bot_info.username}")
    print(f"🔗 رابط البوت: https://t.me/{bot_info.username}")
    print(f"👥 المستخدمون المسجلون: {len(user_manager.users)}")
    
    print("\n" + "="*50)
    print("🎉 **نظام تسجيل الدخول جاهز!**")
    print("="*50)
    
    # إبقاء البوت يعمل
    await bot.run_until_disconnected()

# ==================== التشغيل الرئيسي ====================
if __name__ == '__main__':
    asyncio.run(main())
