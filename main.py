from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler, ApplicationHandlerStop
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat
from telegram.error import Conflict
from config import (
    COMPROBANTE1_CONFIG,
    COMPROBANTE4_CONFIG,
    COMPROBANTE_MOVIMIENTO_CONFIG,
    COMPROBANTE_MOVIMIENTO2_CONFIG,
    COMPROBANTE_QR_CONFIG,
    COMPROBANTE_NUEVO_CONFIG,
    COMPROBANTE_ANULADO_CONFIG,  # 
    COMPROBANTE_MOVIMIENTO3_CONFIG,
    MVKEY_CONFIG,  # 
    COMPROBANTE_AHORROS_CONFIG,  # 
    COMPROBANTE_AHORROS2_CONFIG,  # Configuración para corriente
    COMPROBANTE_DAVIPLATA_CONFIG,  # Configuración para daviplata
    COMPROBANTE_BC_NQ_T_CONFIG,  # Configuración para BC a NQ y T
    COMPROBANTE_BC_QR_CONFIG,  # Configuración para BC QR
    COMPROBANTE_NEQUI_BC_CONFIG,  # Configuración para Nequi a BC
    COMPROBANTE_NEQUI_AHORROS_CONFIG,  # Configuración para Nequi Ahorros
    MOVIMIENTO_BC_AHORROS_CONFIG,  # Movimientos Bancolombia
    MOVIMIENTO_BC_CORRIENTE_CONFIG,
    MOVIMIENTO_BC_NEQUI_CONFIG,
    MOVIMIENTO_BC_QR_CONFIG
)
from utils import generar_comprobante, generar_comprobante_nuevo, generar_comprobante_anulado, enmascarar_nombre, generar_comprobante_ahorros, generar_comprobante_daviplata, generar_comprobante_bc_nq_t, generar_comprobante_bc_qr, generar_comprobante_nequi_bc, generar_comprobante_nequi_ahorros, generar_movimiento_bancolombia
from auth_system import AuthSystem
import os
import logging
from datetime import datetime, timedelta
import pytz
import json

os.makedirs("logs", exist_ok=True)

class QuietHttpLogsFilter(logging.Filter):
    def filter(self, record):
        if record.name.startswith(("httpx", "httpcore")) and record.levelno < logging.WARNING:
            return False
        return True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/errors.log", encoding="utf-8"),
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
for handler in logging.getLogger().handlers:
    handler.addFilter(QuietHttpLogsFilter())

def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.strip()
                if not clean or clean.startswith("#") or "=" not in clean:
                    continue
                key, value = clean.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except Exception as e:
        logging.warning(f"No se pudo cargar .env: {e}")

load_env_file()

# Configuration - copia Curry
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Falta configurar BOT_TOKEN en las variables de entorno.")
ADMIN_ID = 6801143985  # Owner principal Curry
OWNER_IDS = [
    ADMIN_ID,
    7422843477,
    8268082701,
]
OWNER_NAMES = {
    ADMIN_ID: "Owner principal",
    7422843477: "Owner",
    8268082701: "Owner",
}
SUPERVISOR_ADMIN_IDS = []
SUPERVISOR_NAMES = {}
ADDITIONAL_ADMIN_IDS = [7422843477]
ALLOWED_GROUP = int(os.getenv("CURRY_GROUP_ID", "0") or "0")
GROUP_INVITE_URL = os.getenv("CURRY_GROUP_INVITE_URL", "https://t.me/Curry_comprobantebot")
REQUIRED_CHANNEL_ID = ALLOWED_GROUP
CHANNEL_INVITE_URL = GROUP_INVITE_URL

# Contactos que verán los usuarios sin VIP.
# Si el vendedor tiene username, ponlo sin @ en "username".
# Si no tiene username, deja username en None y cambia telegram_id.
CONTACT_SELLERS = [
    {"name": "Soporte Curry 1", "telegram_id": 6801143985, "username": None},
    {"name": "Soporte Curry 2", "telegram_id": 7422843477, "username": None},
    {"name": "Soporte Curry 3", "telegram_id": 8268082701, "username": None},
]

BOT_ACCESS_TEXT = (
    "🔐 **Acceso VIP requerido**\n\n"
    "Tu ID aun no tiene una membresia activa en el sistema.\n"
    "El acceso se activa manualmente por un vendedor y queda con fecha de vencimiento.\n\n"
    "✨ **Que incluye el VIP:**\n"
    "• Generador de comprobantes\n"
    "• Acceso privado por ID\n"
    "• Soporte directo\n\n"
    "💎 **Elige una opcion o contacta a un vendedor:**"
)

RULES_TEXT = (
    "📌 **Reglas de uso**\n\n"
    "━━━━━━━━━━━━━━\n"
    "✅ Usa el bot solo dentro de tu acceso autorizado.\n"
    "🚫 Prohibido usar el servicio para engaños, suplantación, ventas ilegales o abuso.\n"
    "👑 Los owners pueden auditar actividad, banear usuarios y retirar accesos.\n"
    "🧾 Tu acceso VIP tiene fecha de inicio y vencimiento.\n\n"
    "El mal uso causa baneo permanente."
)

GROUP_RULES_BASE_TEXT = (
    "📌 **Reglas y uso del grupo**\n\n"
    "━━━━━━━━━━━━━━\n"
    "✅ Usa el bot solo para generar tus comprobantes dentro del grupo autorizado.\n"
    "🚫 No uses el servicio para engaños, suplantación, ventas ilegales o abuso.\n"
    "⏰ Si el grupo tiene horario, el bot solo funciona dentro de esa franja.\n"
    "⛔ Si el grupo está en OFF, el bot no procesa comandos ni botones.\n\n"
    "🧭 **Cómo se usa**\n"
    "1. Toca una opción del panel: Nequi, Daviplata, QR, Bre B, etc.\n"
    "2. Responde los datos que el bot va pidiendo.\n"
    "3. Usa **❌ Cancelar** si quieres cortar una acción pendiente.\n\n"
    "📋 **Comando principal**\n"
    "🤖 `/comprobante` - Abrir panel"
)

def group_rules_text(can_manage_group: bool = False):
    return GROUP_RULES_BASE_TEXT


def group_comandos_disponibles_text(can_manage_group: bool = False):
    return (
        "📋 **Comandos del grupo**\n\n"
        "━━━━━━━━━━━━━━\n"
        "🤖 `/comprobante` - Abrir panel\n"
        "📌 `/reglas` - Ver reglas\n"
        "❌ `/cancelar` - Cancelar acción"
    )

def comandos_disponibles_text(user_id=None):
    text = (
        "📋 **Comandos disponibles**\n\n"
        "━━━━━━━━━━━━━━\n"
        "🤖 `/start` - Iniciar\n"
        "🧾 `/comprobante` - Abrir generador\n"
        "📌 `/reglas` - Ver reglas\n"
        "💬 `/soporte` - Contactar soporte\n"
        "❌ `/cancelar` - Cancelar una acción pendiente"
    )

    if user_id is not None and auth_system.is_admin(user_id):
        text += (
            "\n\n🛠️ **Comandos admin**\n"
            "🛠️ `/panel` - Panel administrador\n"
            "👥 `/grupos` - Grupos por ID\n"
            "💎 `/agregar` - Agregar VIP\n"
            "📊 `/stats` - Ver estadísticas"
        )

    if user_id is not None and is_owner(user_id):
        text += (
            "\n\n👑 **Comandos owner**\n"
            "🧩 `/owner` - Panel privado\n"
            "💾 `/backup` - Descargar backup\n"
            "📢 `/broadcast mensaje` - Avisar a usuarios VIP"
        )

    return text

BOT_VIP_PRICES = [
    ("$7 DIAS", "$10.000"),
    ("$1 MES", "$25.000"),
    ("$2 MESES", "$45.000"),
    ("$3 MESES", "$70.000"),
    ("PERMANENTE", "$80.000"),
]

NEQUI_IPHONE_PRICE = "$45.000"

NEQUI_APP_PRICES = [
    ("$3.500.000", "$48.000", "🤑"),
    ("$5.000.000", "$68.000", "🦾"),
    ("$10.000.000", "$78.000", "🤑"),
]

BANCOLOMBIA_APP_PRICES = [
    ("$3.500.000", "$50.000"),
    ("$5.000.000", "$60.000"),
    ("$10.000.000", "$75.000"),
]

DAVIPLATA_PRICE = "$40.000"
PRICES_FILE = "prices_data.json"
SETTINGS_FILE = "bot_settings.json"

DEFAULT_PRICE_DATA = {
    "bot": BOT_VIP_PRICES,
    "nequi_iphone": NEQUI_IPHONE_PRICE,
    "nequi_app": NEQUI_APP_PRICES,
    "bancolombia_app": BANCOLOMBIA_APP_PRICES,
    "daviplata": DAVIPLATA_PRICE,
}

def load_json_file(path, default):
    if not os.path.exists(path):
        return default.copy() if isinstance(default, dict) else default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(default, dict):
            merged = default.copy()
            merged.update(data)
            return merged
        return data
    except Exception as e:
        logging.warning(f"No se pudo cargar {path}: {e}")
        return default.copy() if isinstance(default, dict) else default

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

PRICE_DATA = load_json_file(PRICES_FILE, DEFAULT_PRICE_DATA)
BOT_SETTINGS = load_json_file(SETTINGS_FILE, {"maintenance": False})

def format_bot_prices():
    return "\n".join(f"💎 **{md_escape(name)}** ⮕ **{md_escape(price)}**" for name, price in PRICE_DATA["bot"])

def format_app_prices():
    nequi_lines = "\n".join(
        f"✅ **{md_escape(amount)}** ⮕ **{md_escape(price)}** {md_escape(emoji)}"
        for amount, price, emoji in PRICE_DATA["nequi_app"]
    )
    bancolombia_lines = "\n".join(
        f"💎 **{md_escape(amount)}** ⮕ **{md_escape(price)}**"
        for amount, price in PRICE_DATA["bancolombia_app"]
    )
    return (
        "🔹 **Nequi iPhone**\n"
        f"💰 Valor: **{md_escape(PRICE_DATA['nequi_iphone'])}**\n\n"
        "🔹 **App NEQUI**\n"
        f"{nequi_lines}\n\n"
        "🏦 **TARIFAS BANCOLOMBIA**\n"
        f"{bancolombia_lines}\n\n"
        "⚡️ **Daviplata**\n"
        f"🙂‍↕️ **{md_escape(PRICE_DATA['daviplata'])}**"
    )

def normalize_price(value: str) -> str:
    clean = value.strip()
    if not clean.startswith("$"):
        clean = f"${clean}"
    return clean

def md_escape(value) -> str:
    text = str(value if value is not None else "")
    for char in ("\\", "_", "*", "[", "]", "`"):
        text = text.replace(char, f"\\{char}")
    return text

ASK_NAME = "👤 Nombre\nUsa solo letras y espacios."
ASK_BUSINESS = "🏪 Nombre del negocio\nUsa texto corto y claro."
ASK_DESCRIPTION = "📝 Descripcion\nEscribe una descripcion corta."
ASK_PHONE = "📱 Numero\nDebe tener 10 digitos y empezar por 3."
ASK_SENDER_PHONE = "📱 Numero de quien envia\nDebe tener 10 digitos y empezar por 3."
ASK_VALUE = "💰 Valor\nSolo numeros, minimo 1000."
ASK_ACCOUNT_11 = "🏦 Numero de cuenta\nDebe tener 11 digitos."
ASK_LAST4_SEND = "🔢 Ultimos 4 digitos de quien envia\nSolo 4 numeros."
ASK_LAST4_RECEIVE = "🔢 Ultimos 4 digitos de quien recibe\nSolo 4 numeros."
ASK_KEY = "🔑 Llave\nIngresa la llave o identificador."
ASK_BANK = "🏦 Banco\nIngresa el nombre del banco."
ASK_REF = "🔢 Referencia\nFormato: M12345678."
ASK_DATE = "📅 Fecha\nEjemplo: 06/12/2025 - 02:30 PM."

ERR_PHONE = "❌ Numero invalido\nDebe tener 10 digitos y empezar por 3."
ERR_VALUE_NUM = "❌ Valor invalido\nUsa solo numeros."
ERR_VALUE_MIN = "❌ Valor invalido\nEl minimo es 1000."
ERR_ACCOUNT_11 = "❌ Cuenta invalida\nDebe tener 11 digitos."
ERR_LAST4 = "❌ Dato invalido\nDeben ser exactamente 4 numeros."
ERR_NAME = "❌ Nombre invalido\nUsa solo letras y espacios."
ERR_REF = "❌ Referencia invalida\nFormato: M12345678."

NAME_FIRST_TYPES = {
    "comprobante1",
    "movimiento",
    "movimiento2",
    "comprobante_nuevo",
    "comprobante_anulado",
    "comprobante_corriente",
    "comprobante_daviplata",
    "comprobante_ahorros",
    "comprobante_nequi_bc",
    "comprobante_nequi_ahorros",
}

def is_valid_name_text(value: str) -> bool:
    clean = value.strip()
    if len(clean) < 2:
        return False
    return all(ch.isalpha() or ch.isspace() for ch in clean)

def is_valid_reference(value: str) -> bool:
    clean = value.strip().upper()
    return len(clean) == 9 and clean.startswith("M") and clean[1:].isdigit()

def seller_url(seller):
    username = seller.get("username")
    if username:
        return f"https://t.me/{username.replace('@', '')}"
    return None

def seller_button(seller):
    url = seller_url(seller)
    if url:
        return InlineKeyboardButton(f"💬 {seller['name']}", url=url)
    return InlineKeyboardButton(f"💬 {seller['name']}", callback_data="request_access")

def sellers_keyboard(include_prices=True):
    keyboard = []
    if include_prices:
        keyboard.append([
            InlineKeyboardButton("🤖 Planes Bot VIP", callback_data="prices_bot_vip"),
            InlineKeyboardButton("📲 App Nequi VIP", callback_data="prices_nequi_app"),
        ])
    for seller in CONTACT_SELLERS:
        keyboard.append([seller_button(seller)])
    keyboard.append([InlineKeyboardButton("📣 Canal oficial", url=GROUP_INVITE_URL)])
    return InlineKeyboardMarkup(keyboard)

def user_home_keyboard():
    seller_buttons = [
        seller_button(seller)
        for seller in CONTACT_SELLERS
    ]
    keyboard = [
        [
            InlineKeyboardButton("✅ Mi estado", callback_data="show_status"),
            InlineKeyboardButton("📌 Reglas", callback_data="show_rules"),
        ],
        [
            InlineKeyboardButton("💎 Solicitar acceso", callback_data="request_access"),
            InlineKeyboardButton("🧭 Menú", callback_data="show_menu"),
        ],
    ]
    for i in range(0, len(seller_buttons), 2):
        keyboard.append(seller_buttons[i:i + 2])
    return InlineKeyboardMarkup(keyboard)

def optional_group_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Entrar al canal oficial", url=CHANNEL_INVITE_URL)],
        [InlineKeyboardButton("✅ Ya estoy en el canal", callback_data="check_channel")]
    ])

def vip_duration_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏱️ 1 hora", callback_data="vip_time_1 hora"),
            InlineKeyboardButton("⏱️ 6 horas", callback_data="vip_time_6 horas"),
        ],
        [
            InlineKeyboardButton("📅 1 día", callback_data="vip_time_1 dia"),
            InlineKeyboardButton("📅 7 días", callback_data="vip_time_7 dias"),
        ],
        [
            InlineKeyboardButton("💎 1 mes", callback_data="vip_time_1 mes"),
            InlineKeyboardButton("💎 2 meses", callback_data="vip_time_2 meses"),
        ],
        [
            InlineKeyboardButton("👑 Permanente", callback_data="vip_time_permanente"),
        ],
        [
            InlineKeyboardButton("❌ Cancelar", callback_data="vip_time_cancelar"),
        ],
    ])

def vip_manage_keyboard(target_user_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔁 +1 hora", callback_data=f"vip_manage_renew_1h_{target_user_id}"),
            InlineKeyboardButton("🔁 +7 días", callback_data=f"vip_manage_renew_7d_{target_user_id}"),
        ],
        [
            InlineKeyboardButton("🔁 +1 mes", callback_data=f"vip_manage_renew_1m_{target_user_id}"),
            InlineKeyboardButton("👑 Permanente", callback_data=f"vip_manage_renew_perm_{target_user_id}"),
        ],
        [
            InlineKeyboardButton("➖ Quitar VIP", callback_data=f"vip_manage_confirmremove_{target_user_id}"),
            InlineKeyboardButton("🚫 Banear", callback_data=f"vip_manage_confirmban_{target_user_id}"),
        ],
        [
            InlineKeyboardButton("📜 Historial", callback_data=f"vip_manage_history_{target_user_id}"),
        ],
    ])

def confirm_action_keyboard(action: str, target_user_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f"vip_manage_{action}_{target_user_id}"),
            InlineKeyboardButton("❌ Cancelar", callback_data=f"vip_manage_cancel_{target_user_id}"),
        ]
    ])

def users_page_keyboard(mode: str, offset: int, total: int, page_size: int = 10):
    buttons = []
    row = []
    if offset > 0:
        row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"users_page_{mode}_{max(0, offset - page_size)}"))
    if offset + page_size < total:
        row.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"users_page_{mode}_{offset + page_size}"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons) if buttons else None

VIP_DURATION_TEXT = (
    "⏳ **Duración del VIP**\n\n"
    "Elige un tiempo rápido o escribe una duración manual.\n\n"
    "━━━━━━━━━━━━━━\n"
    "⏱️ **Horas:** `1 hora`, `6 horas`, `12 horas`\n"
    "📅 **Días:** `1 dia`, `7 dias`, `15 dias`\n"
    "💎 **Meses:** `1 mes`, `2 meses`, `3 meses`\n"
    "👑 **Sin vencimiento:** `permanente`\n\n"
    "La duración mínima es **1 hora**."
)

def main_menu_keyboard(group_mode: bool = False):
    base_keyboard = [
        [KeyboardButton("🟣 Nequi"), KeyboardButton("🔴 Daviplata")],
        [KeyboardButton("🔳 Nequi QR"), KeyboardButton("⚡ Bre B"), KeyboardButton("🚫 Anulado")],
        [KeyboardButton("🏦 Ahorros"), KeyboardButton("💼 Corriente")],
        [KeyboardButton("↔️ BC a NQ"), KeyboardButton("🔲 BC QR")],
        [KeyboardButton("🏛️ Nequi Corriente"), KeyboardButton("💰 Nequi Ahorros")],
        [KeyboardButton("📅 Fecha manual"), KeyboardButton("🔢 Referencia manual")],
    ]
    if group_mode:
        keyboard = base_keyboard + [
            [KeyboardButton("📋 Comandos"), KeyboardButton("📌 Reglas")],
            [KeyboardButton("❌ Cancelar")]
        ]
    else:
        keyboard = base_keyboard + [
            [KeyboardButton("📋 Comandos"), KeyboardButton("✅ Mi estado")],
            [KeyboardButton("💰 Precios"), KeyboardButton("📌 Reglas")],
            [KeyboardButton("❌ Cancelar")]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def send_vip_required_message(update):
    if is_group_chat(update):
        await send_group_unavailable_message(update)
        return

    user_id = update.effective_user.id
    await update.message.reply_text(
        "👋 **Bienvenido**\n\n"
        "Tu acceso todavía no está activo.\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🆔 **Tu ID:** `{user_id}`\n"
        "💎 Estado: **Sin VIP activo**\n\n"
        "Envíale tu ID a un vendedor para activar el acceso. También puedes ver planes, revisar reglas o pedir soporte desde los botones.",
        parse_mode='Markdown',
        reply_markup=user_home_keyboard()
    )

async def send_group_invite_message(update):
    await update.message.reply_text(
        "📣 **Canal requerido**\n\n"
        "Para ver planes y precios necesitas estar en el canal oficial.\n\n"
        "1. Toca **Entrar al canal oficial**\n"
        "2. Unete al canal\n"
        "3. Vuelve aqui y toca **Ya estoy en el canal**",
        parse_mode='Markdown',
        reply_markup=optional_group_keyboard()
    )

async def is_member_of_required_channel(bot, user_id):
    if auth_system.is_admin(user_id):
        return True
    if not REQUIRED_CHANNEL_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user_id)
        logging.info(f"[CANAL] Usuario {user_id} - Estado: {member.status}")
        return member.status in ['member', 'administrator', 'creator', 'restricted']
    except Exception as e:
        logging.warning(f"[CANAL] No se pudo verificar usuario {user_id}: {e}")
        return False

async def require_channel_for_plans(update_or_query, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if hasattr(update_or_query, "callback_query") and update_or_query.callback_query is not None:
        user_id = update_or_query.callback_query.from_user.id
        message = update_or_query.callback_query.message
    else:
        user_id = update_or_query.effective_user.id
        message = update_or_query.message

    if await is_member_of_required_channel(context.bot, user_id):
        return True

    await message.reply_text(
        "🔒 **Primero debes unirte al canal**\n\n"
        "Los planes y precios se muestran solo a miembros del canal oficial.",
        parse_mode='Markdown',
        reply_markup=optional_group_keyboard()
    )
    return False

async def send_main_menu(update):
    user_id = update.effective_user.id
    in_group = is_group_chat(update)
    if in_group:
        await update.message.reply_text(
            "🤖 **Panel del grupo**\n\n"
            "━━━━━━━━━━━━━━\n"
            f"⏰ {md_escape(group_schedule_text(update.effective_chat.id))}\n\n"
            "Selecciona una opción del menú.\n"
            "Usa **❌ Cancelar** para cortar una acción pendiente.\n\n"
            "📌 Revisa **Reglas** para ver cómo se usa y los comandos principales.",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard(group_mode=True)
        )
        return

    expires = auth_system.get_user_expiration(user_id)
    if auth_system.is_authorized(user_id):
        expires_text = format_vip_expiration(expires)
    else:
        expires_text = "Admin/Owner"
    await update.message.reply_text(
        "💎 **Panel VIP activo**\n\n"
        f"👤 Usuario: `{user_id}`\n"
        f"📅 Acceso hasta: **{expires_text}**\n\n"
        "Selecciona una opción del menú.\n"
        "Puedes usar **❌ Cancelar** en cualquier momento para cortar una acción.",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard(group_mode=in_group)
    )

async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    try:
        bot_id = context.bot.id
    except Exception:
        me = await context.bot.get_me()
        bot_id = me.id

    if not any(member.id == bot_id for member in update.message.new_chat_members):
        return

    chat = update.effective_chat
    await refresh_group_command_menu(context.bot, chat.id)
    await update.message.reply_text(
        "🤖 **Bot agregado al grupo**\n\n"
        "La activación y desactivación se manejan solo desde el chat privado del bot.\n"
        "Un administrador debe abrir `/grupos` y activar por ID.",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard(group_mode=True)
    )

# Initialize authorization system
auth_system = AuthSystem(ADMIN_ID, ALLOWED_GROUP)
for extra_admin_id in ADDITIONAL_ADMIN_IDS:
    if extra_admin_id != ADMIN_ID:
        auth_system.admin_users.add(extra_admin_id)

def is_owner(user_id: int) -> bool:
    return int(user_id) in OWNER_IDS

def owner_lines():
    return [f"⭐ Owner {name}: `{owner_id}`" for owner_id, name in OWNER_NAMES.items()]

def supervisor_lines():
    return [f"🛡️ Supervisor/Vendedor {name}: `{admin_id}`" for admin_id, name in SUPERVISOR_NAMES.items()]

def is_supervisor(user_id: int) -> bool:
    return int(user_id) in SUPERVISOR_ADMIN_IDS

def can_view_supervisor_panel(user_id: int) -> bool:
    return is_owner(user_id) or is_supervisor(user_id)

user_data_store = {}

# Sistema de modo de fechas manuales
fecha_manual_mode = {}  # {user_id: True/False}

# Sistema de modo de referencias manuales
referencia_manual_mode = {}  # {user_id: True/False}

# Sistema de referencias
REFERENCIAS_FILE = "referencias.json"

def cargar_referencias():
    """Carga las referencias desde el archivo JSON"""
    if os.path.exists(REFERENCIAS_FILE):
        try:
            with open(REFERENCIAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def guardar_referencias(referencias):
    """Guarda las referencias en el archivo JSON"""
    with open(REFERENCIAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(referencias, f, ensure_ascii=False, indent=2)

# ID del grupo requerido (debe estar unido sí o sí)
REQUIRED_GROUP_ID = -1003684729959

BOGOTA_TZ = pytz.timezone("America/Bogota")

def parse_vip_expiration(text: str):
    """Convierte una duración escrita por el admin en una fecha de vencimiento."""
    value = text.strip().lower()
    value = (
        value.replace("í", "i")
        .replace("á", "a")
        .replace("é", "e")
        .replace("ó", "o")
        .replace("ú", "u")
    )

    if value in {"permanente", "sin vencimiento", "nunca", "no vence"}:
        return None, "Permanente"

    now = datetime.now(BOGOTA_TZ)

    for date_format in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            expiration_date = datetime.strptime(value, date_format)
            expiration = BOGOTA_TZ.localize(
                expiration_date.replace(hour=23, minute=59, second=59)
            )
            return expiration.isoformat(), format_vip_expiration(expiration.isoformat())
        except ValueError:
            pass

    parts = value.split()
    amount_text = parts[0] if parts else ""
    if amount_text.endswith("h") and amount_text[:-1].isdigit():
        amount = int(amount_text[:-1])
        unit = "horas"
    elif amount_text.endswith("d") and amount_text[:-1].isdigit():
        amount = int(amount_text[:-1])
        unit = "dias"
    elif amount_text.isdigit():
        amount = int(amount_text)
        unit = " ".join(parts[1:]) if len(parts) > 1 else "dias"
    else:
        raise ValueError("Duración inválida")

    if amount <= 0:
        raise ValueError("La duración debe ser mayor a cero")

    if "hora" in unit or unit == "h":
        expiration = now + timedelta(hours=amount)
        return expiration.isoformat(), format_vip_expiration(expiration.isoformat())
    elif "sem" in unit:
        days = amount * 7
    elif "mes" in unit:
        days = amount * 30
    elif "dia" in unit or unit == "d" or unit == "":
        days = amount
    else:
        raise ValueError("Unidad inválida")

    expiration = now + timedelta(days=days)
    return expiration.isoformat(), format_vip_expiration(expiration.isoformat())

def format_vip_expiration(expires_at: str | None) -> str:
    """Muestra la fecha de vencimiento VIP en zona Colombia."""
    if not expires_at:
        return "Permanente"
    try:
        expiration = datetime.fromisoformat(expires_at)
        if expiration.tzinfo is None:
            expiration = BOGOTA_TZ.localize(expiration)
        expiration = expiration.astimezone(BOGOTA_TZ)
        return expiration.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(expires_at)

def get_vip_days_left(expires_at: str | None) -> int | None:
    if not expires_at:
        return None
    try:
        expiration = datetime.fromisoformat(expires_at)
        if expiration.tzinfo is None:
            expiration = BOGOTA_TZ.localize(expiration)
        delta = expiration.astimezone(BOGOTA_TZ) - datetime.now(BOGOTA_TZ)
        return max(0, delta.days)
    except Exception:
        return None

def is_maintenance_enabled() -> bool:
    return bool(BOT_SETTINGS.get("maintenance", False))

def set_maintenance(enabled: bool):
    BOT_SETTINGS["maintenance"] = enabled
    save_json_file(SETTINGS_FILE, BOT_SETTINGS)

def is_admin_control_chat(chat_id: int, user_id: int) -> bool:
    return int(chat_id) == int(user_id) or auth_system.is_group_active(chat_id)

def is_group_chat(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type in {"group", "supergroup"})

def parse_group_time(value: str) -> str | None:
    clean = value.strip().replace(".", ":")
    if ":" not in clean:
        return None
    hour_text, minute_text = clean.split(":", 1)
    if not hour_text.isdigit() or not minute_text.isdigit():
        return None
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"

def group_schedule_text(chat_id: int) -> str:
    schedule = auth_system.get_group_schedule(chat_id)
    if not schedule or not schedule.get("enabled"):
        return "Sin horario: funciona todo el día"
    state = "abierto" if auth_system.is_group_schedule_open(chat_id) else "cerrado"
    return f"{schedule.get('start')} a {schedule.get('end')} ({schedule.get('timezone', 'America/Bogota')}) - ahora {state}"

async def send_group_unavailable_message(update: Update):
    chat_id = update.effective_chat.id
    if not auth_system.is_group_active(chat_id):
        await update.message.reply_text(
            "⛔ Bot apagado en este grupo.\n\n"
            "Un admin del bot puede prenderlo desde el panel privado `/grupos`.",
            parse_mode='Markdown'
        )
        return

    await update.message.reply_text(
        "⏰ Bot fuera de horario en este grupo.\n\n"
        f"Horario actual: **{md_escape(group_schedule_text(chat_id))}**\n\n"
        "Un admin del bot puede cambiarlo desde privado con `/horario ID_DEL_GRUPO 08:00 18:00`.",
        parse_mode='Markdown'
    )

def is_group_disabled(update: Update) -> bool:
    return is_group_chat(update) and not auth_system.is_group_active(update.effective_chat.id)

def is_activation_command(text: str | None) -> bool:
    if not text:
        return False
    command = text.strip().split()[0].split("@")[0].lower()
    return command in {"/activargrupo", "/cashon"}

async def inactive_group_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not is_group_disabled(update):
        return
    if is_activation_command(update.message.text):
        return
    await update.message.reply_text(
        "⛔ Bot apagado en este grupo.\n\n"
        "No procesaré comandos ni botones aquí hasta que un admin lo active desde el panel privado `/grupos`.",
        parse_mode='Markdown'
    )
    raise ApplicationHandlerStop

async def inactive_group_callback_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.message:
        return
    chat = query.message.chat
    if chat.type not in {"group", "supergroup"} or auth_system.is_group_active(chat.id):
        return
    await query.answer("Bot apagado en este grupo.", show_alert=True)
    raise ApplicationHandlerStop

async def unsupported_update_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None and update.callback_query is None:
        raise ApplicationHandlerStop

def is_telegram_group_link(value: str | None) -> bool:
    if not value:
        return False
    clean = value.strip().lower()
    return (
        clean.startswith("https://t.me/")
        or clean.startswith("http://t.me/")
        or clean.startswith("t.me/")
        or clean.startswith("telegram.me/")
    )

def extract_group_link_from_args(args) -> str | None:
    for arg in args or []:
        if is_telegram_group_link(arg):
            return arg.strip()
    return None

async def get_chat_invite_link(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> str | None:
    try:
        chat = await context.bot.get_chat(chat_id)
        if getattr(chat, "invite_link", None):
            return chat.invite_link
    except Exception as e:
        logging.info(f"No se pudo leer invite_link del grupo {chat_id}: {e}")

    try:
        return await context.bot.export_chat_invite_link(chat_id)
    except Exception as e:
        logging.info(f"No se pudo exportar invite_link del grupo {chat_id}: {e}")
        return None

def format_iso_time(value: str | None) -> str:
    if not value:
        return "Sin actividad"
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(BOGOTA_TZ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return value or "Sin actividad"

def vip_status_text(target_user_id: int) -> str:
    is_vip = auth_system.is_authorized(target_user_id)
    expiration = auth_system.get_user_expiration(target_user_id)
    added = auth_system.get_user_added_by(target_user_id)
    last_activity = auth_system.get_user_last_activity(target_user_id)
    days_left = get_vip_days_left(expiration)
    added_name = md_escape(added.get('admin_name', 'Sin dato'))
    added_id = md_escape(added.get('admin_id', 'N/A'))
    return (
        "🔎 **Estado del usuario**\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{target_user_id}`\n"
        f"💎 VIP: **{'Sí' if is_vip else 'No'}**\n"
        f"📅 Vence: **{format_vip_expiration(expiration) if is_vip else 'No aplica'}**\n"
        f"⏳ Días restantes: **{days_left if days_left is not None and is_vip else 'No aplica'}**\n"
        f"👑 Admin: **{'Sí' if auth_system.is_admin(target_user_id) else 'No'}**\n"
        f"🚫 Baneado: **{'Sí' if auth_system.is_banned(target_user_id) else 'No'}**\n"
        f"🧾 Agregado por: {added_name} (`{added_id}`)\n"
        f"🕐 Última actividad: {format_iso_time(last_activity)}"
    )

def user_status_text(user_id: int) -> str:
    is_admin_user = auth_system.is_admin(user_id)
    is_owner_user = is_owner(user_id)
    is_vip = auth_system.is_authorized(user_id)
    is_banned = auth_system.is_banned(user_id)
    expiration = auth_system.get_user_expiration(user_id)
    added = auth_system.get_user_added_by(user_id)
    status = "Owner" if is_owner_user else "Admin" if is_admin_user else "VIP activo" if is_vip else "Sin VIP"
    if is_banned:
        status = "Baneado"
    return (
        "✅ **Mi estado**\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{user_id}`\n"
        f"💎 Estado: **{status}**\n"
        f"📅 Acceso hasta: **{format_vip_expiration(expiration) if is_vip else 'No aplica'}**\n"
        f"🧾 Activado por: {md_escape(added.get('admin_name', 'Sin dato'))}\n\n"
        "Usa /ayuda para ver opciones disponibles."
    )

async def alert_owner_error(context: ContextTypes.DEFAULT_TYPE, where: str, error: Exception):
    for owner_id in OWNER_IDS:
        try:
            await context.bot.send_message(
                chat_id=owner_id,
                text=(
                    "⚠️ Error del bot\n\n"
                    f"📍 Lugar: {where}\n"
                    f"🧩 Error: {str(error)[:800]}"
                )
            )
        except Exception:
            pass

async def maybe_warn_vip_expiration(update: Update):
    user_id = update.effective_user.id
    if auth_system.is_admin(user_id) or not auth_system.is_authorized(user_id):
        return
    days_left = get_vip_days_left(auth_system.get_user_expiration(user_id))
    if days_left in {0, 1, 3}:
        await update.message.reply_text(
            "⏳ **Aviso de vencimiento VIP**\n\n"
            f"Tu acceso vence en **{days_left} día(s)**.\n"
            "Contacta a un vendedor para renovarlo.",
            parse_mode='Markdown',
            reply_markup=sellers_keyboard(include_prices=False)
        )

async def is_member_of_group(bot, user_id):
    """Verifica si el usuario es miembro del grupo requerido"""
    if auth_system.is_admin(user_id):
        return True

    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_GROUP_ID, user_id=user_id)
        print(f"[DEBUG] Usuario {user_id} - Estado en grupo: {member.status}")
        
        # Solo permitir si es miembro activo del grupo
        is_member = member.status in ['member', 'administrator', 'creator', 'restricted']
        
        if not is_member:
            print(f"[ACCESO DENEGADO] Usuario {user_id} - Estado: {member.status}")
        else:
            print(f"[ACCESO PERMITIDO] Usuario {user_id} - Estado: {member.status}")
        
        return is_member
        
    except Exception as e:
        print(f"[ERROR CRÍTICO] No se pudo verificar membresía para usuario {user_id}: {e}")
        print(f"[ACCESO DENEGADO] Por seguridad, se deniega el acceso cuando hay errores")
        
        # SIEMPRE denegar acceso si hay cualquier error
        # Esto obliga a que el bot esté correctamente configurado
        return False

async def send_success_message(update: Update):
    """Envía mensaje de éxito después de generar un comprobante"""
    await update.message.reply_text(
        "✅ **Comprobante generado correctamente**\n\n"
        "Tu archivo esta listo.\n"
        "Puedes crear otro comprobante cuando quieras usando /comprobante.",
        parse_mode='Markdown'
    )

async def notify_main_admin(context: ContextTypes.DEFAULT_TYPE, admin_id: int, admin_name: str, action: str, target_info: str = ""):
    """Envía notificación al administrador principal sobre acciones de otros admins"""
    try:
        # Obtener fecha y hora actual
        now = datetime.now()
        fecha_hora = now.strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"🔔 **Notificación Administrativa**\n\n"
        message += f"👤 **Admin:** {admin_id}\n"
        message += f"📝 **Nombre:** {md_escape(admin_name or 'Sin nombre')}\n"
        message += f"⚡ **Acción:** {md_escape(action)}\n"
        if target_info:
            message += f"🎯 **Detalles:** {md_escape(target_info)}\n"
        message += f"🕐 **Fecha/Hora:** {fecha_hora}"
        
        for owner_id in OWNER_IDS:
            if owner_id == admin_id:
                continue
            await context.bot.send_message(
                chat_id=owner_id,
                text=message,
                parse_mode='Markdown'
            )
    except Exception as e:
        print(f"[ERROR] No se pudo enviar notificación a owners: {e}")

async def apply_vip_duration(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    admin_id: int,
    admin_name: str,
    target_user_id: int,
    nombre: str,
    duration_text: str,
    action_label: str = "activado",
    notify_user: bool = True,
):
    expires_at, fecha_vencimiento = parse_vip_expiration(duration_text)
    auth_system.add_user(
        target_user_id,
        nombre,
        expires_at=expires_at,
        added_by=admin_id,
        added_by_name=admin_name
    )

    now = datetime.now(BOGOTA_TZ)
    fecha_inicio = now.strftime("%d/%m/%Y %H:%M")
    fecha_agregado = now.strftime("%d/%m/%Y %H:%M:%S")
    nombre_escaped = md_escape(nombre)
    fecha_venc_escaped = md_escape(fecha_vencimiento)
    admin_name_escaped = md_escape(admin_name)
    duration_escaped = md_escape(duration_text)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ **VIP {action_label} correctamente**\n\n"
            "━━━━━━━━━━━━━━\n"
            f"🆔 Usuario: `{target_user_id}`\n"
            f"👤 Nombre: **{nombre_escaped}**\n"
            f"⏳ Duración: **{duration_escaped}**\n"
            f"🟢 Inicia: **{fecha_inicio}**\n"
            f"🔴 Termina: **{fecha_venc_escaped}**\n"
            f"🕐 Registro: {fecha_agregado}\n"
            f"👑 Admin: {admin_name_escaped}\n\n"
            "🟢 Estado: **Activo en el sistema**"
        ),
        parse_mode='Markdown'
    )

    if notify_user:
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"💎 **VIP {action_label}**\n\n"
                    "Tu acceso premium ya está listo.\n\n"
                    f"⏳ **Duración:** {duration_escaped}\n"
                    f"🟢 **Inicio:** {fecha_inicio}\n"
                    f"🔴 **Finaliza:** {fecha_venc_escaped}\n\n"
                    "🚀 Usa /comprobante para abrir el generador."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.warning(f"No se pudo notificar al usuario VIP {target_user_id}: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "⚠️ El VIP quedó guardado, pero no pude escribirle al usuario.\n"
                    "Esa persona debe iniciar el bot con /start o /comprobante."
                )
            )

    await notify_main_admin(
        context,
        admin_id,
        admin_name,
        f"VIP {action_label}",
        f"{target_user_id} | {nombre} | vence {fecha_vencimiento}"
    )

    return fecha_vencimiento

async def start_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Funcion que redirige a los usuarios que usan /start al comando correcto"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    auth_system.update_activity(user_id)

    if auth_system.is_banned(user_id):
        await update.message.reply_text("Estás baneado de nuestros servicios.")
        return

    if is_maintenance_enabled() and not auth_system.is_admin(user_id):
        await update.message.reply_text(
            "🛠️ **Bot en mantenimiento**\n\n"
            "Estamos ajustando el servicio. Intenta de nuevo más tarde.",
            parse_mode='Markdown'
        )
        return

    if auth_system.is_admin(user_id) and not is_group_chat(update):
        await menu_command(update, context)
        return

    if not auth_system.can_use_bot(user_id, chat_id):
        await send_vip_required_message(update)
        return

    await maybe_warn_vip_expiration(update)
    await send_main_menu(update)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    user = update.effective_user
    auth_system.update_activity(user_id)
    
    # Verificar primero si está baneado
    if auth_system.is_banned(user_id):
        await update.message.reply_text("Estás baneado por ratón ")
        return

    if is_maintenance_enabled() and not auth_system.is_admin(user_id):
        await update.message.reply_text(
            "🛠️ **Bot en mantenimiento**\n\n"
            "Estamos ajustando el servicio. Intenta de nuevo más tarde.",
            parse_mode='Markdown'
        )
        return
    
    is_admin = auth_system.is_admin(user_id)

    if not is_admin and not auth_system.can_use_bot(user_id, chat_id):
        await send_vip_required_message(update)
        return
    
    await maybe_warn_vip_expiration(update)
    await send_main_menu(update)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    auth_system.update_activity(user_id)
    if is_group_chat(update):
        if auth_system.can_use_bot(user_id, update.effective_chat.id):
            await send_main_menu(update)
        else:
            await send_vip_required_message(update)
        return

    if auth_system.is_admin(user_id):
        text = (
            "🧭 **Menú principal**\n\n"
            "━━━━━━━━━━━━━━\n"
            "🛠️ /panel - Gestión admin\n"
            "✅ /miestado - Ver tu estado\n"
            "📋 /usuarios vip - Ver usuarios\n"
            "🧾 /acciones - Acciones recientes\n"
            "💬 /soporte - Contactos\n"
            "❌ /cancelar - Cancelar acción pendiente"
        )
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=admin_panel_keyboard())
        return

    if auth_system.can_use_bot(user_id, update.effective_chat.id):
        await send_main_menu(update)
    else:
        await send_vip_required_message(update)

async def soporte_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💬 **Soporte y vendedores**\n\n"
        "Elige con quién quieres hablar:",
        parse_mode='Markdown',
        reply_markup=sellers_keyboard(include_prices=False)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    user = update.effective_user
    auth_system.update_activity(user_id)

    if is_group_disabled(update):
        return

    if text.lower() in {"cancelar", "/cancelar", "❌ cancelar", "salir", "parar"}:
        await cancelar_command(update, context)
        return

    if text == "📋 Comandos":
        await comandos_command(update, context)
        return

    if text == "📅 Fecha manual":
        await fechas_command(update, context)
        return

    if text == "🔢 Referencia manual":
        await refes_command(update, context)
        return

    if text == "💰 Precios":
        await precios_command(update, context)
        return

    if text == "📌 Reglas":
        await reglas_command(update, context)
        return

    if text == "✅ Mi estado":
        await miestado_command(update, context)
        return

    if text.lower() in {"menu", "/menu", "🧭 menú", "🧭 menu"}:
        await menu_command(update, context)
        return

    if is_maintenance_enabled() and not auth_system.is_admin(user_id):
        await update.message.reply_text(
            "🛠️ **Bot en mantenimiento**\n\n"
            "Estamos ajustando el servicio. Intenta de nuevo más tarde.",
            parse_mode='Markdown'
        )
        return

    # Mapeo de botones del teclado a tipos de comprobante
    button_mapping = {
        "🟣 Nequi": "comprobante1",
        "Nequi": "comprobante1",
        "Transfiya": "comprobante4", 
        "🔴 Daviplata": "comprobante_daviplata",
        "Daviplata": "comprobante_daviplata",
        "🔳 Nequi QR": "comprobante_qr",
        "Nequi QR": "comprobante_qr",
        "⚡ Bre B": "comprobante_nuevo",
        "Bre B": "comprobante_nuevo",
        "🚫 Anulado": "comprobante_anulado",
        "Anulado": "comprobante_anulado",
        "🏦 Ahorros": "comprobante_ahorros",
        "Ahorros": "comprobante_ahorros",
        "💼 Corriente": "comprobante_corriente",
        "Corriente": "comprobante_corriente",
        "↔️ BC a NQ": "comprobante_bc_nq_t",
        "BC a NQ": "comprobante_bc_nq_t",
        "🔲 BC QR": "comprobante_bc_qr",
        "BC QR": "comprobante_bc_qr",
        "🏛️ Nequi Corriente": "comprobante_nequi_bc",
        "Nequi Corriente": "comprobante_nequi_bc",
        "💰 Nequi Ahorros": "comprobante_nequi_ahorros",
        "Nequi Ahorros": "comprobante_nequi_ahorros"
    }

    # Si el mensaje es uno de los botones del teclado, verificar baneos
    if text in button_mapping and user_id not in user_data_store:
        # Verificar si está baneado solo cuando intenta usar el bot
        if auth_system.is_banned(user_id):
            await update.message.reply_text("🚫 Estas baneado. Si crees que es un error, contacta a un administrador.")
            return

        is_admin = auth_system.is_admin(user_id)

        if not is_admin and not auth_system.can_use_bot(user_id, chat_id):
            await send_vip_required_message(update)
            return
            
        tipo = button_mapping[text]
        user_data_store[user_id] = {"step": 0, "tipo": tipo, "chat_id": chat_id}

        prompts = {
            "comprobante1": ASK_NAME,
            "comprobante4": ASK_PHONE,
            "movimiento": ASK_NAME,
            "movimiento2": ASK_NAME,
            "comprobante_qr": ASK_BUSINESS,
            "comprobante_nuevo": ASK_NAME,
            "comprobante_anulado": ASK_NAME,
            "comprobante_corriente": ASK_NAME,
            "comprobante_daviplata": ASK_NAME,
            "comprobante_ahorros": ASK_NAME,
            "comprobante_bc_nq_t": ASK_PHONE,
            "comprobante_bc_qr": ASK_DESCRIPTION,
            "comprobante_nequi_bc": ASK_NAME
        }

        await update.message.reply_text(prompts.get(tipo, "📝 Ingresa el dato."))
        return

    if user_id not in user_data_store:
        return

    # Verificar baneos cuando el usuario está completando datos del bot
    if auth_system.is_banned(user_id):
        await update.message.reply_text("estas baneado de nuestros servicios si crees que esto es un error contacta a algun adminsitrador")
        return

    data = user_data_store[user_id]
    if data.get("chat_id") is not None and data.get("chat_id") != chat_id:
        return
    tipo = data["tipo"]
    step = data["step"]

    if tipo == "activar_grupo_id":
        if step == 0:
            try:
                data["group_id"] = int(text)
            except ValueError:
                await update.message.reply_text("❌ El ID del grupo debe ser numérico. Ejemplo: `-1001234567890`", parse_mode='Markdown')
                return
            group_id = data["group_id"]
            auth_system.activate_group(
                group_id,
                f"Grupo {group_id}",
                activated_by=user_id,
                activated_by_name=data.get("admin_name") or update.effective_user.first_name or "Admin",
                invite_link=None
            )
            await refresh_group_command_menu(context.bot, group_id)
            await update.message.reply_text(
                "✅ Grupo activado.",
                parse_mode='Markdown',
                reply_markup=group_panel_keyboard(update.effective_chat.id, update.effective_chat.type)
            )
            del user_data_store[user_id]
            return

    if tipo == "desactivar_grupo_id":
        if step == 0:
            try:
                group_id = int(text)
            except ValueError:
                await update.message.reply_text("❌ El ID del grupo debe ser numérico. Ejemplo: `-1001234567890`", parse_mode='Markdown')
                return
            if auth_system.deactivate_group(group_id, deactivated_by=user_id, deactivated_by_name=data.get("admin_name") or update.effective_user.first_name or "Admin"):
                await reset_group_command_menu(context.bot, group_id)
                await update.message.reply_text("⛔ Grupo desactivado.", parse_mode='Markdown', reply_markup=group_panel_keyboard(update.effective_chat.id, update.effective_chat.type))
                await notify_main_admin(context, user_id, update.effective_user.first_name, "Desactivó grupo", str(group_id))
            else:
                await update.message.reply_text("ℹ️ El grupo ya estaba desactivado.", parse_mode='Markdown', reply_markup=group_panel_keyboard(update.effective_chat.id, update.effective_chat.type))
            del user_data_store[user_id]
            return

    if tipo == "horario_grupo_id":
        if step == 0:
            try:
                group_id = int(text)
            except ValueError:
                await update.message.reply_text("❌ El ID del grupo debe ser numérico. Ejemplo: `-1001234567890`", parse_mode='Markdown')
                return
            if not auth_system.is_group_active(group_id):
                await update.message.reply_text("⛔ Ese grupo está apagado. Primero actívalo desde el panel.")
                return
            data["group_id"] = group_id
            data["step"] = 1
            await update.message.reply_text(
                "⏰ Envía el horario en formato `08:00 18:00`.\n\n"
                "También puedes escribir `off` para quitar el horario.",
                parse_mode='Markdown'
            )
            return
        if step == 1:
            group_id = data["group_id"]
            action = text.strip().lower()
            if action in {"off", "apagar", "quitar", "none", "sinhorario"}:
                auth_system.clear_group_schedule(group_id, updated_by=user_id, updated_by_name=data.get("admin_name") or update.effective_user.first_name or "Admin")
                await update.message.reply_text("✅ Horario quitado.", reply_markup=group_panel_keyboard(update.effective_chat.id, update.effective_chat.type))
                del user_data_store[user_id]
                return
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text("❌ Envía el horario así: `08:00 18:00`", parse_mode='Markdown')
                return
            start_time = parse_group_time(parts[0])
            end_time = parse_group_time(parts[1])
            if not start_time or not end_time:
                await update.message.reply_text("❌ Horario inválido. Usa formato de 24 horas: `08:00 18:00`", parse_mode='Markdown')
                return
            auth_system.set_group_schedule(
                group_id,
                start_time,
                end_time,
                updated_by=user_id,
                updated_by_name=data.get("admin_name") or update.effective_user.first_name or "Admin"
            )
            await update.message.reply_text(
                f"✅ Horario actualizado: **{start_time}** a **{end_time}**.",
                parse_mode='Markdown',
                reply_markup=group_panel_keyboard(update.effective_chat.id, update.effective_chat.type)
            )
            del user_data_store[user_id]
            return

    if tipo == "quitar_horario_grupo_id":
        if step == 0:
            try:
                group_id = int(text)
            except ValueError:
                await update.message.reply_text("❌ El ID del grupo debe ser numérico. Ejemplo: `-1001234567890`", parse_mode='Markdown')
                return
            if not auth_system.is_group_active(group_id):
                await update.message.reply_text("⛔ Ese grupo está apagado. Primero actívalo desde el panel.")
                return
            auth_system.clear_group_schedule(group_id, updated_by=user_id, updated_by_name=data.get("admin_name") or update.effective_user.first_name or "Admin")
            await update.message.reply_text("✅ Horario quitado.", reply_markup=group_panel_keyboard(update.effective_chat.id, update.effective_chat.type))
            del user_data_store[user_id]
            return

    if step == 0 and tipo in NAME_FIRST_TYPES and not is_valid_name_text(text):
        await update.message.reply_text(ERR_NAME)
        return

    if step == 10 and not is_valid_reference(text):
        await update.message.reply_text(ERR_REF)
        return

    # --- NEQUI ---
    if tipo == "comprobante1":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_PHONE)
        elif step == 1:
            # Validar número de teléfono
            if not text.isdigit() or len(text) != 10 or not text.startswith('3'):
                await update.message.reply_text(ERR_PHONE)
                return
            data["telefono"] = text
            data["step"] = 2
            await update.message.reply_text(ASK_VALUE)
        elif step == 2:
            if not text.replace("-", "", 1).isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor
            
            # Verificar si el modo de referencia manual está activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text(ASK_REF)
                return
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text(ASK_DATE)
                return
            
            output_path = generar_comprobante(data, COMPROBANTE1_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            # movimiento negativo
            data_mov = data.copy()
            data_mov["nombre"] = data["nombre"].upper()
            data_mov["valor"] = -abs(data["valor"])
            output_path_mov = generar_comprobante(data_mov, COMPROBANTE_MOVIMIENTO_CONFIG)
            with open(output_path_mov, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_mov)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE1_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            # movimiento negativo
            data_mov = data.copy()
            data_mov["nombre"] = data["nombre"].upper()
            data_mov["valor"] = -abs(data["valor"])
            output_path_mov = generar_comprobante(data_mov, COMPROBANTE_MOVIMIENTO_CONFIG)
            with open(output_path_mov, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_mov)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text(ASK_DATE)
                return
            
            output_path = generar_comprobante(data, COMPROBANTE1_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            # movimiento negativo
            data_mov = data.copy()
            data_mov["nombre"] = data["nombre"].upper()
            data_mov["valor"] = -abs(data["valor"])
            output_path_mov = generar_comprobante(data_mov, COMPROBANTE_MOVIMIENTO_CONFIG)
            with open(output_path_mov, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_mov)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual después de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE1_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            # movimiento negativo
            data_mov = data.copy()
            data_mov["nombre"] = data["nombre"].upper()
            data_mov["valor"] = -abs(data["valor"])
            output_path_mov = generar_comprobante(data_mov, COMPROBANTE_MOVIMIENTO_CONFIG)
            with open(output_path_mov, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_mov)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- TRANSFIYA ---
    elif tipo == "comprobante4":
        if step == 0:
            # Validar número de teléfono
            if not text.isdigit() or len(text) != 10 or not text.startswith('3'):
                await update.message.reply_text(ERR_PHONE)
                return
            data["telefono"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            if not text.replace("-", "", 1).isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor
            
            # Verificar si el modo de referencia manual está activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text(ASK_REF)
                return
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 2
                await update.message.reply_text(ASK_DATE)
                return
            
            output_path = generar_comprobante(data, COMPROBANTE4_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            # movimiento negativo
            data_mov2 = {
                "telefono": data["telefono"],
                "valor": -abs(data["valor"]),
                "nombre": data["telefono"],
            }
            output_path_mov2 = generar_comprobante(data_mov2, COMPROBANTE_MOVIMIENTO2_CONFIG)
            with open(output_path_mov2, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_mov2)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 2:
            # Procesar fecha manual para Transfiya
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE4_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            # movimiento negativo
            data_mov2 = {
                "telefono": data["telefono"],
                "valor": -abs(data["valor"]),
                "nombre": data["telefono"],
            }
            output_path_mov2 = generar_comprobante(data_mov2, COMPROBANTE_MOVIMIENTO2_CONFIG)
            with open(output_path_mov2, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_mov2)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para Transfiya
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text(ASK_DATE)
                return
            
            output_path = generar_comprobante(data, COMPROBANTE4_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov2 = {
                "telefono": data["telefono"],
                "valor": -abs(data["valor"]),
                "nombre": data["telefono"],
            }
            output_path_mov2 = generar_comprobante(data_mov2, COMPROBANTE_MOVIMIENTO2_CONFIG)
            with open(output_path_mov2, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_mov2)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual después de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE4_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov2 = {
                "telefono": data["telefono"],
                "valor": -abs(data["valor"]),
                "nombre": data["telefono"],
            }
            output_path_mov2 = generar_comprobante(data_mov2, COMPROBANTE_MOVIMIENTO2_CONFIG)
            with open(output_path_mov2, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_mov2)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- MOVIMIENTOS ---
    elif tipo in ["movimiento", "movimiento2"]:
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            if not text.isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor

            cfg = COMPROBANTE_MOVIMIENTO_CONFIG if tipo == "movimiento" else COMPROBANTE_MOVIMIENTO2_CONFIG
            output_path = generar_comprobante(data, cfg)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE QR ---
    elif tipo == "comprobante_qr":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            if not text.replace("-", "", 1).isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor

            # Verificar si el modo de referencia manual está activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text(ASK_REF)
                return

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 2
                await update.message.reply_text(ASK_DATE)
                return

            output_path = generar_comprobante(data, COMPROBANTE_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            # Movimiento adicional con plantilla 3
            data_mov_qr = {
                "nombre": data["nombre"].upper(),
                "valor": -abs(data["valor"])
            }
            output_path_movqr = generar_comprobante(data_mov_qr, COMPROBANTE_MOVIMIENTO3_CONFIG)
            with open(output_path_movqr, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movqr)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 2:
            # Procesar fecha manual para QR
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            # Movimiento adicional con plantilla 3
            data_mov_qr = {
                "nombre": data["nombre"].upper(),
                "valor": -abs(data["valor"])
            }
            output_path_movqr = generar_comprobante(data_mov_qr, COMPROBANTE_MOVIMIENTO3_CONFIG)
            with open(output_path_movqr, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movqr)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para QR
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text(ASK_DATE)
                return

            output_path = generar_comprobante(data, COMPROBANTE_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov_qr = {
                "nombre": data["nombre"].upper(),
                "valor": -abs(data["valor"])
            }
            output_path_movqr = generar_comprobante(data_mov_qr, COMPROBANTE_MOVIMIENTO3_CONFIG)
            with open(output_path_movqr, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movqr)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual después de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov_qr = {
                "nombre": data["nombre"].upper(),
                "valor": -abs(data["valor"])
            }
            output_path_movqr = generar_comprobante(data_mov_qr, COMPROBANTE_MOVIMIENTO3_CONFIG)
            with open(output_path_movqr, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movqr)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE NUEVO (LLAVES) ---
    elif tipo == "comprobante_nuevo":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            val_txt = text.replace(".", "").replace(",", ".")
            try:
                valor = float(val_txt)
                if valor < 1000:
                    await update.message.reply_text(ERR_VALUE_MIN)
                    return
                data["valor"] = valor
            except ValueError:
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            data["step"] = 2
            await update.message.reply_text(ASK_KEY)
        elif step == 2:
            data["llave"] = text
            data["step"] = 3
            await update.message.reply_text(ASK_BANK)
        elif step == 3:
            data["banco"] = text
            data["step"] = 4
            await update.message.reply_text(ASK_SENDER_PHONE)
        elif step == 4:
            # Validar número de teléfono del que envía
            if not text.isdigit() or len(text) != 10 or not text.startswith('3'):
                await update.message.reply_text(ERR_PHONE)
                return
            data["numero_envia"] = text

            # Verificar si el modo de referencia manual está activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text(ASK_REF)
                return

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 5
                await update.message.reply_text(ASK_DATE)
                return

            #  Generar comprobante principal
            output_path = generar_comprobante_nuevo(data, COMPROBANTE_NUEVO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            #  Generar movimiento automático con MVKEY (enmascarado)
            data_mov_llaves = {
                "nombre": enmascarar_nombre(data["nombre"]),  
                "valor": -abs(float(data["valor"]))
            }
            output_path_movllaves = generar_comprobante(data_mov_llaves, MVKEY_CONFIG)
            with open(output_path_movllaves, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movllaves)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 5:
            # Procesar fecha manual para comprobante NUEVO
            data["fecha_manual"] = text
            
            #  Generar comprobante principal
            output_path = generar_comprobante_nuevo(data, COMPROBANTE_NUEVO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            #  Generar movimiento automático con MVKEY (enmascarado)
            data_mov_llaves = {
                "nombre": enmascarar_nombre(data["nombre"]),  
                "valor": -abs(float(data["valor"]))
            }
            output_path_movllaves = generar_comprobante(data_mov_llaves, MVKEY_CONFIG)
            with open(output_path_movllaves, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movllaves)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para Bre B
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text(ASK_DATE)
                return

            output_path = generar_comprobante_nuevo(data, COMPROBANTE_NUEVO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov_llaves = {
                "nombre": enmascarar_nombre(data["nombre"]),  
                "valor": -abs(float(data["valor"]))
            }
            output_path_movllaves = generar_comprobante(data_mov_llaves, MVKEY_CONFIG)
            with open(output_path_movllaves, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movllaves)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual después de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante_nuevo(data, COMPROBANTE_NUEVO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov_llaves = {
                "nombre": enmascarar_nombre(data["nombre"]),  
                "valor": -abs(float(data["valor"]))
            }
            output_path_movllaves = generar_comprobante(data_mov_llaves, MVKEY_CONFIG)
            with open(output_path_movllaves, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movllaves)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE ANULADO ---
    elif tipo == "comprobante_anulado":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            if not text.replace("-", "", 1).isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 2
                await update.message.reply_text(ASK_DATE)
                return

            output_path = generar_comprobante_anulado(data, COMPROBANTE_ANULADO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ANULADO")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 2:
            # Procesar fecha manual para ANULADO
            data["fecha_manual"] = text
            
            output_path = generar_comprobante_anulado(data, COMPROBANTE_ANULADO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ANULADO")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE AHORROS ---
    elif tipo == "comprobante_ahorros":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_ACCOUNT_11)
        elif step == 1:
            # Validar que tenga 11 dígitos
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text(ERR_ACCOUNT_11)
                return
            data["numero_cuenta"] = text
            data["step"] = 2
            await update.message.reply_text(ASK_VALUE)
        elif step == 2:
            # Validar valor numérico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text(ASK_DATE)
                return

            # Generar comprobante
            output_path = generar_comprobante_ahorros(data, COMPROBANTE_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Ahorros")
            os.remove(output_path)
            
            # MOVIMIENTO DESACTIVADO
            # data_mov_ahorros = {
            #     "valor": data["valor"],
            #     "nombre": data["nombre"]
            # }
            # output_path_mov = generar_movimiento_bancolombia(data_mov_ahorros, MOVIMIENTO_BC_AHORROS_CONFIG)
            # with open(output_path_mov, "rb") as f:
            #     await update.message.reply_document(document=f, caption=" Movimiento Ahorros")
            # os.remove(output_path_mov)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual para Ahorros
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_ahorros(data, COMPROBANTE_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Ahorros")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE CORRIENTE ---
    elif tipo == "comprobante_corriente":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_ACCOUNT_11)
        elif step == 1:
            # Validar que tenga 11 dígitos
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text(ERR_ACCOUNT_11)
                return
            data["numero_cuenta"] = text
            data["step"] = 2
            await update.message.reply_text(ASK_VALUE)
        elif step == 2:
            # Validar valor numérico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text(ASK_DATE)
                return

            # Generar comprobante
            output_path = generar_comprobante_ahorros(data, COMPROBANTE_AHORROS2_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante de Corriente")
            os.remove(output_path)
            
            # MOVIMIENTO DESACTIVADO
            # data_mov_corriente = {
            #     "valor": data["valor"],
            #     "nombre": data["nombre"]
            # }
            # output_path_mov = generar_movimiento_bancolombia(data_mov_corriente, MOVIMIENTO_BC_CORRIENTE_CONFIG)
            # with open(output_path_mov, "rb") as f:
            #     await update.message.reply_document(document=f, caption=" Movimiento Corriente")
            # os.remove(output_path_mov)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual para Corriente
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_ahorros(data, COMPROBANTE_AHORROS2_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante de Corriente")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE DAVIPLATA ---
    elif tipo == "comprobante_daviplata":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            # Validar valor numérico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor
            data["step"] = 2
            await update.message.reply_text(ASK_LAST4_SEND)
        elif step == 2:
            # Validar cuenta que recibe (4 dígitos)
            if not text.isdigit() or len(text) != 4:
                await update.message.reply_text(ERR_LAST4)
                return
            data["recibe"] = text
            data["step"] = 3
            await update.message.reply_text(ASK_LAST4_RECEIVE)
        elif step == 3:
            # Validar cuenta que envía (4 dígitos)
            if not text.isdigit() or len(text) != 4:
                await update.message.reply_text(ERR_LAST4)
                return
            data["envia"] = text

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 4
                await update.message.reply_text(ASK_DATE)
                return

            # Generar comprobante
            output_path = generar_comprobante_daviplata(data, COMPROBANTE_DAVIPLATA_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Daviplata")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 4:
            # Procesar fecha manual para Daviplata
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_daviplata(data, COMPROBANTE_DAVIPLATA_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Daviplata")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE BC A NQ Y T ---
    elif tipo == "comprobante_bc_nq_t":
        if step == 0:
            # Validar número de teléfono
            if not text.isdigit() or len(text) != 10 or not text.startswith('3'):
                await update.message.reply_text(ERR_PHONE)
                return
            data["telefono"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            # Validar valor numérico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 2
                await update.message.reply_text(ASK_DATE)
                return

            # Generar comprobante
            output_path = generar_comprobante_bc_nq_t(data, COMPROBANTE_BC_NQ_T_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante BC a NQ")
            os.remove(output_path)
            
            # MOVIMIENTO DESACTIVADO
            # data_mov_nequi = {
            #     "valor": data["valor"],
            #     "nombre": data.get("telefono", "NEQUI")
            # }
            # output_path_mov = generar_movimiento_bancolombia(data_mov_nequi, MOVIMIENTO_BC_NEQUI_CONFIG)
            # with open(output_path_mov, "rb") as f:
            #     await update.message.reply_document(document=f, caption=" Movimiento BC a Nequi")
            # os.remove(output_path_mov)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 2:
            # Procesar fecha manual para BC a NQ
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_bc_nq_t(data, COMPROBANTE_BC_NQ_T_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante BC a NQ")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE BC QR ---
    elif tipo == "comprobante_bc_qr":
        if step == 0:
            data["descripcion_qr"] = text  # Descripción del QR
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor
            data["step"] = 2
            await update.message.reply_text(ASK_NAME)
        elif step == 2:
            if not is_valid_name_text(text):
                await update.message.reply_text(ERR_NAME)
                return
            data["nombre"] = text  # Nombre completo
            data["step"] = 3
            await update.message.reply_text(ASK_ACCOUNT_11)
        elif step == 3:
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text(ERR_ACCOUNT_11)
                return
            data["numero_cuenta"] = digitos

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 4
                await update.message.reply_text(ASK_DATE)
                return

            # Generar comprobante
            output_path = generar_comprobante_bc_qr(data, COMPROBANTE_BC_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante BC QR")
            os.remove(output_path)
            
            # MOVIMIENTO DESACTIVADO
            # data_mov_qr = {
            #     "valor": data["valor"],
            #     "nombre": data.get("punto_venta", "QR")
            # }
            # output_path_mov = generar_movimiento_bancolombia(data_mov_qr, MOVIMIENTO_BC_QR_CONFIG)
            # with open(output_path_mov, "rb") as f:
            #     await update.message.reply_document(document=f, caption=" Movimiento BC QR")
            # os.remove(output_path_mov)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 4:
            # Procesar fecha manual para BC QR
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_bc_qr(data, COMPROBANTE_BC_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante BC QR")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE NEQUI A BC ---
    elif tipo == "comprobante_nequi_bc":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            # Validar valor numérico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor
            data["step"] = 2
            await update.message.reply_text(ASK_ACCOUNT_11)
        elif step == 2:
            # Validar que tenga 11 dígitos
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text(ERR_ACCOUNT_11)
                return
            data["numero_cuenta"] = text

            # Verificar si el modo de referencia manual está activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text(ASK_REF)
                return

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text(ASK_DATE)
                return

            # Generar comprobante
            output_path = generar_comprobante_nequi_bc(data, COMPROBANTE_NEQUI_BC_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Nequi Corriente")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual para Nequi a BC
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_nequi_bc(data, COMPROBANTE_NEQUI_BC_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Nequi Corriente")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para Nequi Corriente
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text(ASK_DATE)
                return

            output_path = generar_comprobante_nequi_bc(data, COMPROBANTE_NEQUI_BC_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Nequi Corriente")
            os.remove(output_path)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual después de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante_nequi_bc(data, COMPROBANTE_NEQUI_BC_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Nequi Corriente")
            os.remove(output_path)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE NEQUI AHORROS ---
    elif tipo == "comprobante_nequi_ahorros":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(ASK_VALUE)
        elif step == 1:
            # Validar valor numérico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(ERR_VALUE_NUM)
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(ERR_VALUE_MIN)
                return
            data["valor"] = valor
            data["step"] = 2
            await update.message.reply_text(ASK_ACCOUNT_11)
        elif step == 2:
            # Validar que tenga 11 dígitos
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text(ERR_ACCOUNT_11)
                return
            data["numero_cuenta"] = text

            # Verificar si el modo de referencia manual está activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text(ASK_REF)
                return

            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text(ASK_DATE)
                return

            # Generar comprobante
            output_path = generar_comprobante_nequi_ahorros(data, COMPROBANTE_NEQUI_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Nequi Ahorros")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual para Nequi Ahorros
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_nequi_ahorros(data, COMPROBANTE_NEQUI_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Nequi Ahorros")
            os.remove(output_path)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para Nequi Ahorros
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text(ASK_DATE)
                return

            output_path = generar_comprobante_nequi_ahorros(data, COMPROBANTE_NEQUI_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Nequi Ahorros")
            os.remove(output_path)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual después de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante_nequi_ahorros(data, COMPROBANTE_NEQUI_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" Comprobante Nequi Ahorros")
            os.remove(output_path)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- AGREGAR USUARIO (ADMIN) ---
    elif tipo == "agregar_usuario":
        if step == 0:
            # Validar que sea un ID numérico
            if not text.isdigit():
                await update.message.reply_text("❌ El ID debe ser numérico. Intenta de nuevo:")
                return
            data["target_user_id"] = int(text)
            data["step"] = 1
            await update.message.reply_text(
                "💎 **Agregar VIP**\n\n"
                "Paso **2 de 3**\n"
                f"🆔 Usuario: `{data['target_user_id']}`\n\n"
                "Escribe el nombre o alias del cliente.",
                parse_mode='Markdown'
            )
        elif step == 1:
            data["nombre"] = text
            data["step"] = 2
            await update.message.reply_text(
                "💎 **Agregar VIP**\n\n"
                "Paso **3 de 3**\n"
                f"🆔 Usuario: `{data['target_user_id']}`\n"
                f"👤 Nombre: **{md_escape(data['nombre'])}**\n\n"
                + VIP_DURATION_TEXT,
                parse_mode='Markdown',
                reply_markup=vip_duration_keyboard()
            )
        elif step == 2:
            try:
                fecha_vencimiento = await apply_vip_duration(
                    context,
                    update.effective_chat.id,
                    user_id,
                    data["admin_name"],
                    data["target_user_id"],
                    data["nombre"],
                    text,
                    action_label="activado"
                )
                data["fecha_vencimiento"] = fecha_vencimiento
                logging.debug(f"[ADMIN] {user_id} agregó usuario {data['target_user_id']} ({data['nombre']}) - Vence: {data['fecha_vencimiento']}")
                del user_data_store[user_id]
            except ValueError:
                await update.message.reply_text(
                    "❌ **Duración inválida**\n\n"
                    "Usa algo desde **1 hora** en adelante.\n\n"
                    "Ejemplos: `1 hora`, `6 horas`, `7 dias`, `1 mes`, `permanente`.",
                    parse_mode='Markdown',
                    reply_markup=vip_duration_keyboard()
                )
            except Exception as e:
                logging.error(f"Error al agregar usuario: {e}")
                await update.message.reply_text(f"❌ Error al agregar usuario: {str(e)}")
                del user_data_store[user_id]

    # --- RENOVAR USUARIO (ADMIN) ---
    elif tipo == "renovar_usuario":
        if step == 0:
            if not text.isdigit():
                await update.message.reply_text("❌ El ID debe ser numérico. Intenta de nuevo:")
                return
            data["target_user_id"] = int(text)
            data["step"] = 1
            await update.message.reply_text(
                "🔁 **Renovar VIP**\n\n"
                f"Usuario seleccionado: `{data['target_user_id']}`\n\n"
                f"{VIP_DURATION_TEXT}",
                parse_mode='Markdown',
                reply_markup=vip_duration_keyboard()
            )
        elif step == 1:
            try:
                target_user_id = data["target_user_id"]
                current_name = auth_system.get_authorized_users().get(target_user_id, f"Usuario_{target_user_id}")
                fecha_vencimiento = await apply_vip_duration(
                    context,
                    update.effective_chat.id,
                    user_id,
                    data["admin_name"],
                    target_user_id,
                    current_name,
                    text,
                    action_label="renovado"
                )
                del user_data_store[user_id]
            except ValueError:
                await update.message.reply_text(
                    "❌ **Duración inválida**\n\n"
                    "Usa algo desde **1 hora** en adelante.\n\n"
                    "Ejemplos: `1 hora`, `6 horas`, `7 dias`, `1 mes`, `permanente`.",
                    parse_mode='Markdown',
                    reply_markup=vip_duration_keyboard()
                )
            except Exception as e:
                logging.error(f"Error al renovar usuario: {e}")
                await alert_owner_error(context, "renovar_usuario", e)
                await update.message.reply_text(f"❌ Error al renovar usuario: {str(e)}")
                del user_data_store[user_id]

# ================= ADMIN COMMANDS =================
def admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧾 Comprobantes", callback_data="admin_help_comprobante")],
        [InlineKeyboardButton("👥 Grupos por ID", callback_data="admin_groups_panel")],
        [
            InlineKeyboardButton("➕ Agregar persona", callback_data="admin_help_agregar"),
            InlineKeyboardButton("🔁 Renovar", callback_data="admin_help_renovar"),
        ],
        [
            InlineKeyboardButton("📊 Estadísticas", callback_data="admin_help_stats"),
            InlineKeyboardButton("📋 Usuarios", callback_data="admin_help_usuarios"),
        ],
        [
            InlineKeyboardButton("🔎 Revisar ID", callback_data="admin_help_vipcheck"),
            InlineKeyboardButton("🆔 Mi ID", callback_data="admin_help_id"),
        ],
        [InlineKeyboardButton("⚙️ Ajustes", callback_data="owner_summary")],
    ])

def group_panel_keyboard(chat_id: int | None = None, chat_type: str | None = None):
    buttons = [
        [InlineKeyboardButton("🤖 Agregar bot a un grupo", callback_data="admin_groups_invite")],
        [
            InlineKeyboardButton("✅ ON gratis por ID", callback_data="admin_groups_add_id"),
            InlineKeyboardButton("⛔ OFF por ID", callback_data="admin_groups_remove_id"),
        ],
        [
            InlineKeyboardButton("⏰ Poner horario", callback_data="admin_groups_schedule_id"),
            InlineKeyboardButton("🕐 Quitar horario", callback_data="admin_groups_clear_schedule_id"),
        ],
        [InlineKeyboardButton("📋 Grupos activos", callback_data="admin_groups_list")],
    ]
    buttons.append([InlineKeyboardButton("⬅️ Volver al panel", callback_data="admin_groups_back")])
    return InlineKeyboardMarkup(buttons)

def owner_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Control owners", callback_data="owner_summary")],
        [
            InlineKeyboardButton("📋 VIP por admin", callback_data="owner_vips_by_admin"),
            InlineKeyboardButton("🧾 Auditoría", callback_data="owner_audit"),
        ],
        [
            InlineKeyboardButton("👑 Admins", callback_data="owner_admins"),
            InlineKeyboardButton("📊 Resumen", callback_data="owner_summary"),
        ],
    ])

def format_audit_time(value):
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(BOGOTA_TZ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return value or "Sin fecha"

async def owner_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("Este panel es exclusivo del owner.")
        return

    await update.message.reply_text(
        "👑 **Panel privado owner**\n\n"
        "━━━━━━━━━━━━━━\n"
        "📋 Revisa VIP agregados por cada admin.\n"
        "🧾 Mira la auditoría de cambios.\n"
        "👑 Controla administradores.\n"
        "📊 Consulta el resumen general.\n\n"
        "Elige una opción:",
        parse_mode='Markdown',
        reply_markup=owner_panel_keyboard()
    )

async def owner_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not is_owner(user_id):
        await query.message.reply_text("Este panel es exclusivo del owner.")
        return

    if query.data == "owner_vips_by_admin":
        users = auth_system.get_authorized_users()
        if not users:
            await query.message.reply_text("📭 No hay VIP activos todavia.", reply_markup=owner_panel_keyboard())
            return

        lines = ["📋 **VIP agregados por admin**", "━━━━━━━━━━━━━━\n"]
        for uid, name in users.items():
            added = auth_system.get_user_added_by(uid)
            expires = format_vip_expiration(auth_system.get_user_expiration(uid))
            lines.append(
                f"💎 `{uid}`\n"
                f"👤 {md_escape(name)}\n"
                f"👑 Admin: {md_escape(added.get('admin_name', 'Sin dato'))} (`{md_escape(added.get('admin_id', 'N/A'))}`)\n"
                f"📅 Vence: {expires}"
            )
        await query.message.reply_text("\n".join(lines), parse_mode='Markdown', reply_markup=owner_panel_keyboard())
        return

    if query.data == "owner_audit":
        audit = auth_system.get_audit_log()[-15:]
        if not audit:
            await query.message.reply_text("🧾 No hay acciones registradas todavia.", reply_markup=owner_panel_keyboard())
            return

        lines = ["🧾 **Últimas acciones admin**", "━━━━━━━━━━━━━━\n"]
        for item in reversed(audit):
            lines.append(
                f"🕐 {format_audit_time(item.get('created_at'))}\n"
                f"⚙️ Acción: `{md_escape(item.get('action'))}`\n"
                f"👑 Admin: {md_escape(item.get('admin_name'))} (`{md_escape(item.get('admin_id'))}`)\n"
                f"🎯 Objetivo: `{md_escape(item.get('target_id'))}`\n"
                f"📝 Detalle: {md_escape(item.get('details') or 'Sin detalle')}"
            )
        await query.message.reply_text("\n".join(lines), parse_mode='Markdown', reply_markup=owner_panel_keyboard())
        return

    if query.data == "owner_admins":
        admins = auth_system.get_admin_users()
        lines = [
            "👑 **Administradores del bot**",
            "━━━━━━━━━━━━━━\n",
        ] + owner_lines() + supervisor_lines()
        for uid in admins:
            if uid in SUPERVISOR_ADMIN_IDS:
                continue
            lines.append(f"👑 Admin: `{uid}`")
        await query.message.reply_text("\n".join(lines), parse_mode='Markdown', reply_markup=owner_panel_keyboard())
        return

    if query.data == "owner_summary":
        stats = auth_system.get_stats()
        await query.message.reply_text(
            "📊 **Resumen owner**\n\n"
            "━━━━━━━━━━━━━━\n"
            f"💎 VIP activos: **{stats['total_authorized']}**\n"
            f"🚫 Baneados: **{stats['total_banned']}**\n"
            f"👑 Admins: **{stats['total_admins']}**\n"
            f"🧾 Acciones registradas: **{len(auth_system.get_audit_log())}**",
            parse_mode='Markdown',
            reply_markup=owner_panel_keyboard()
        )

async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_group_chat(update):
        if auth_system.can_use_bot(user_id, update.effective_chat.id):
            await send_main_menu(update)
        else:
            await send_vip_required_message(update)
        return

    if not auth_system.is_admin(user_id):
        await update.message.reply_text("Este panel solo esta disponible para administradores.")
        return

    message = (
        "🛠️ **Panel de administrador**\n\n"
        "━━━━━━━━━━━━━━\n"
        "👥 **Primero:** usa **PANEL GRUPOS / AGREGAR BOT** para meter el bot a grupos y activarlos.\n"
        "💎 Gestiona usuarios VIP.\n"
        "🚫 Controla baneos.\n"
        "👑 Administra permisos.\n"
        "📊 Revisa estadísticas.\n\n"
        "Selecciona una opción:"
    )
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=admin_panel_keyboard())

def active_groups_text() -> str:
    groups = auth_system.get_active_groups()
    lines = [
        "👥 **Panel de grupos**",
        "━━━━━━━━━━━━━━",
        "🔒 Este panel se maneja solo por privado para administradores.",
        "",
        "**Uso rápido**",
        "1. Agrega el bot al grupo.",
        "2. Copia el ID del grupo.",
        "3. Usa los botones por ID para activar, apagar o poner horario.",
        "",
        f"✅ Grupos activos: **{len(groups)}**",
        "",
        "📋 **Lista activa**",
    ]
    if not groups:
        lines.append("📭 No hay grupos activos.")
    else:
        for group_id, data in groups.items():
            title = md_escape(data.get("title") or f"Grupo {group_id}")
            admin_name = md_escape(data.get("activated_by_name") or "Admin")
            invite_link = data.get("invite_link")
            link_text = f"\n  🔗 {md_escape(invite_link)}" if invite_link else ""
            schedule_text = md_escape(group_schedule_text(group_id))
            lines.append(f"• `{group_id}` - {title} | por {admin_name}\n  ⏰ {schedule_text}{link_text}")
    lines.extend([
        "",
        "Comandos:",
        "• `/grupos` - abrir este panel",
        "• `/activargrupo ID_DEL_GRUPO` - activar por ID",
        "• `/desactivargrupo ID_DEL_GRUPO` - desactivar por ID",
        "• `/horario ID_DEL_GRUPO 08:00 18:00` - poner horario",
        "• `/horario ID_DEL_GRUPO off` - quitar horario"
    ])
    return "\n".join(lines)

async def send_group_panel(message, context: ContextTypes.DEFAULT_TYPE, chat_id: int | None = None, chat_type: str | None = None):
    await message.reply_text(
        active_groups_text(),
        parse_mode='Markdown',
        reply_markup=group_panel_keyboard(chat_id, chat_type)
    )

async def send_bot_invite_info(message, context: ContextTypes.DEFAULT_TYPE):
    try:
        bot_info = await context.bot.get_me()
        username = bot_info.username
    except Exception:
        username = None

    if username:
        invite_url = f"https://t.me/{username}?startgroup=true"
        text = (
            "🤖 Agregar bot a un grupo\n\n"
            f"1. Abre este enlace: {invite_url}\n"
            "2. Selecciona el grupo de Telegram.\n"
            "3. Vuelve a este chat privado.\n"
            "4. Entra a Activar por ID y envía el ID exacto del grupo.\n\n"
            "Así nadie puede prender o apagar el bot desde el grupo."
        )
    else:
        text = (
            "🤖 Agregar bot a un grupo\n\n"
            "No pude leer el username del bot ahora mismo.\n"
            "Agrégalo manualmente al grupo desde Telegram y luego vuelve a este panel para activarlo por ID."
        )

    await message.reply_text(text, disable_web_page_preview=True)

async def grupos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return

    if is_group_chat(update):
        await update.message.reply_text("🔒 El panel de grupos se maneja por privado. Escríbeme `/grupos` en el chat del bot.")
        return

    await send_group_panel(
        update.message,
        context,
        update.effective_chat.id,
        update.effective_chat.type
    )

async def activargrupo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_group_chat(update):
        await update.message.reply_text("🔒 Este control se maneja por privado. Abre el bot y usa `/grupos`.")
        return
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores del bot.")
        return

    invite_link = extract_group_link_from_args(context.args)
    if context.args:
        first_arg = context.args[0]
        if is_telegram_group_link(first_arg):
            await update.message.reply_text("❌ Para evitar confusiones, activa grupos solo con el ID exacto.")
            return
        else:
            try:
                group_id = int(first_arg)
            except ValueError:
                await update.message.reply_text(
                    "❌ Uso: `/activargrupo ID_DEL_GRUPO`",
                    parse_mode='Markdown'
                )
                return
            title = f"Grupo {group_id}"
    else:
        await update.message.reply_text(
            "👥 **Activar grupo**\n\n"
            "Envía el ID exacto del grupo desde el panel privado.\n\n"
            "Uso: `/activargrupo ID_DEL_GRUPO`",
            parse_mode='Markdown',
            reply_markup=group_panel_keyboard(update.effective_chat.id, update.effective_chat.type)
        )
        return

    created = auth_system.activate_group(
        group_id,
        title,
        activated_by=user_id,
        activated_by_name=update.effective_user.first_name or "Admin",
        invite_link=invite_link
    )
    await refresh_group_command_menu(context.bot, group_id)
    status_text = "✅ Grupo activado." if created else "✅ Grupo actualizado."
    await update.message.reply_text(
        status_text,
        parse_mode='Markdown',
        reply_markup=None if is_group_chat(update) else group_panel_keyboard(update.effective_chat.id, update.effective_chat.type)
    )
    await notify_main_admin(context, user_id, update.effective_user.first_name, "Activó grupo", f"{group_id} | {title}")

async def desactivargrupo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_group_chat(update):
        await update.message.reply_text("🔒 Este control se maneja por privado. Abre el bot y usa `/grupos`.")
        return
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores del bot.")
        return

    if context.args:
        if is_telegram_group_link(context.args[0]):
            await update.message.reply_text("❌ Para evitar confusiones, desactiva grupos solo con el ID exacto.")
            return
        else:
            try:
                group_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Uso: `/desactivargrupo ID_DEL_GRUPO`", parse_mode='Markdown')
                return
    else:
        await update.message.reply_text("❌ En privado debes usar: `/desactivargrupo ID_DEL_GRUPO`", parse_mode='Markdown')
        return

    if auth_system.deactivate_group(group_id, deactivated_by=user_id, deactivated_by_name=update.effective_user.first_name):
        await reset_group_command_menu(context.bot, group_id)
        await update.message.reply_text("⛔ Grupo desactivado.", parse_mode='Markdown')
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Desactivó grupo", str(group_id))
    else:
        await update.message.reply_text("ℹ️ El grupo ya estaba desactivado.", parse_mode='Markdown')

async def cashhorario_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_group_chat(update):
        await update.message.reply_text("🔒 El horario se maneja por privado desde el panel de grupos.")
        return
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores del bot.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "⏰ **Horario por ID**\n\n"
            "Usa:\n"
            "`/horario ID_DEL_GRUPO 08:00 18:00`\n"
            "`/horario ID_DEL_GRUPO off`",
            parse_mode='Markdown'
        )
        return

    try:
        group_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ El ID del grupo debe ser numérico.", parse_mode='Markdown')
        return

    if not auth_system.is_group_active(group_id):
        await update.message.reply_text("⛔ Ese grupo está apagado. Primero actívalo desde el panel.")
        return

    action = context.args[1].strip().lower()
    if action in {"off", "apagar", "quitar", "none", "sinhorario"}:
        auth_system.clear_group_schedule(
            group_id,
            updated_by=user_id,
            updated_by_name=update.effective_user.first_name or "Admin"
        )
        await update.message.reply_text("✅ Horario quitado.")
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Uso: `/horario ID_DEL_GRUPO 08:00 18:00` o `/horario ID_DEL_GRUPO off`",
            parse_mode='Markdown'
        )
        return

    start_time = parse_group_time(context.args[1])
    end_time = parse_group_time(context.args[2])
    if not start_time or not end_time:
        await update.message.reply_text(
            "❌ Horario inválido. Usa formato de 24 horas, por ejemplo: `/horario ID_DEL_GRUPO 08:00 18:00`",
            parse_mode='Markdown'
        )
        return

    auth_system.set_group_schedule(
        group_id,
        start_time,
        end_time,
        updated_by=user_id,
        updated_by_name=update.effective_user.first_name or "Admin"
    )
    await update.message.reply_text(
        f"✅ Horario actualizado: **{start_time}** a **{end_time}**.",
        parse_mode='Markdown'
    )

async def admin_groups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not auth_system.is_admin(user_id):
        await query.message.reply_text("Este panel solo esta disponible para administradores.")
        return

    chat_id = query.message.chat_id
    chat_type = getattr(query.message.chat, "type", None)

    if query.data in {"admin_groups_panel", "admin_groups_list"}:
        await send_group_panel(query.message, context, chat_id, chat_type)
        return

    if query.data == "admin_groups_invite":
        await send_bot_invite_info(query.message, context)
        return

    if query.data == "admin_groups_add_id":
        user_data_store[user_id] = {
            "step": 0,
            "tipo": "activar_grupo_id",
            "admin_name": query.from_user.first_name or "Admin",
            "chat_id": query.message.chat_id
        }
        await query.message.reply_text(
            "➕ **Agregar grupo por ID**\n\n"
            "Envía el ID del grupo.\n\n"
            "Ejemplo: `-1001234567890`",
            parse_mode='Markdown'
        )
        return

    if query.data == "admin_groups_remove_id":
        user_data_store[user_id] = {
            "step": 0,
            "tipo": "desactivar_grupo_id",
            "admin_name": query.from_user.first_name or "Admin",
            "chat_id": query.message.chat_id
        }
        await query.message.reply_text(
            "⛔ **Desactivar grupo por ID**\n\n"
            "Envía el ID exacto del grupo.\n\n"
            "Ejemplo: `-1001234567890`",
            parse_mode='Markdown'
        )
        return

    if query.data == "admin_groups_schedule_id":
        user_data_store[user_id] = {
            "step": 0,
            "tipo": "horario_grupo_id",
            "admin_name": query.from_user.first_name or "Admin",
            "chat_id": query.message.chat_id
        }
        await query.message.reply_text(
            "⏰ **Poner horario por ID**\n\n"
            "Envía el ID exacto del grupo.\n\n"
            "Ejemplo: `-1001234567890`",
            parse_mode='Markdown'
        )
        return

    if query.data == "admin_groups_clear_schedule_id":
        user_data_store[user_id] = {
            "step": 0,
            "tipo": "quitar_horario_grupo_id",
            "admin_name": query.from_user.first_name or "Admin",
            "chat_id": query.message.chat_id
        }
        await query.message.reply_text(
            "🕐 **Quitar horario por ID**\n\n"
            "Envía el ID exacto del grupo.\n\n"
            "Ejemplo: `-1001234567890`",
            parse_mode='Markdown'
        )
        return

    if query.data == "admin_groups_back":
        await query.message.reply_text(
            "🛠️ **Panel de administrador**\n\nSelecciona una opción:",
            parse_mode='Markdown',
            reply_markup=admin_panel_keyboard()
        )
        return

    if query.data.startswith("admin_groups_activate_"):
        try:
            target_group_id = int(query.data.replace("admin_groups_activate_", "", 1))
        except ValueError:
            await query.message.reply_text("❌ ID de grupo inválido.")
            return
        title = getattr(query.message.chat, "title", None) or f"Grupo {target_group_id}"
        invite_link = await get_chat_invite_link(context, target_group_id)
        created = auth_system.activate_group(
            target_group_id,
            title,
            activated_by=user_id,
            activated_by_name=query.from_user.first_name,
            invite_link=invite_link
        )
        await refresh_group_command_menu(context.bot, target_group_id)
        await query.message.reply_text(
            "✅ Grupo activado." if created else "✅ Grupo actualizado.",
            parse_mode='Markdown',
            reply_markup=group_panel_keyboard(chat_id, chat_type)
        )
        return

    if query.data.startswith("admin_groups_deactivate_"):
        try:
            target_group_id = int(query.data.replace("admin_groups_deactivate_", "", 1))
        except ValueError:
            await query.message.reply_text("❌ ID de grupo inválido.")
            return
        if auth_system.deactivate_group(target_group_id, deactivated_by=user_id, deactivated_by_name=query.from_user.first_name):
            await reset_group_command_menu(context.bot, target_group_id)
            await query.message.reply_text("⛔ Grupo desactivado.", parse_mode='Markdown', reply_markup=group_panel_keyboard(chat_id, chat_type))
        else:
            await query.message.reply_text("ℹ️ El grupo ya estaba desactivado.", parse_mode='Markdown')
        return

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not auth_system.is_admin(user_id):
        await query.message.reply_text("Este panel solo esta disponible para administradores.")
        return

    if query.data == "admin_help_agregar":
        user_data_store[user_id] = {
            "step": 0,
            "tipo": "agregar_usuario",
            "admin_name": query.from_user.first_name or "Admin",
            "chat_id": query.message.chat_id
        }
        await query.message.reply_text(
            "💎 **Agregar usuario VIP**\n\n"
            "Envía el ID de Telegram del usuario.\n\n"
            "Ejemplo: `123456789`",
            parse_mode='Markdown'
        )
        return

    help_messages = {
        "admin_help_comprobante": "🧾 **Comprobantes**\n\nUsa `/comprobante` para abrir el panel completo del generador.",
        "admin_help_eliminar": "➖ **Quitar VIP**\n\nUsa:\n`/eliminar ID_DEL_USUARIO`",
        "admin_help_renovar": "🔁 **Renovar VIP**\n\nUsa:\n`/renovar ID_DEL_USUARIO 1 hora`\n`/renovar ID_DEL_USUARIO 1 mes`\n\nTambién puedes escribir solo `/renovar` y seguir los pasos.",
        "admin_help_vipcheck": "🔎 **Revisar usuario**\n\nUsa:\n`/vipcheck ID_DEL_USUARIO`",
        "admin_help_ban": "🚫 **Banear usuario**\n\nUsa:\n`/ban ID_DEL_USUARIO`",
        "admin_help_unban": "✅ **Desbanear usuario**\n\nUsa:\n`/unban ID_DEL_USUARIO`",
        "admin_help_admin": "👑 **Agregar administrador**\n\nUsa:\n`/admin ID_DEL_USUARIO`",
        "admin_help_unadmin": "🔻 **Quitar administrador**\n\nUsa:\n`/unadmin ID_DEL_USUARIO`",
        "admin_help_stats": "📊 **Estadísticas**\n\nUsa:\n`/stats`",
        "admin_help_usuarios": "📋 **Listas de usuarios**\n\nUsa:\n`/usuarios vip`\n`/usuarios vencidos`\n`/usuarios baneados`\n`/usuarios admins`",
        "admin_help_setprecio": "💰 **Editar precios**\n\nUsa:\n`/setprecio bot 1_mes 25000`\n`/setprecio iphone 45000`\n`/setprecio daviplata 40000`\n`/setprecio nequi 3500000 48000`\n`/setprecio bancolombia 5000000 60000`",
        "admin_help_mantenimiento": "🛠️ **Mantenimiento**\n\nUsa:\n`/mantenimiento on`\n`/mantenimiento off`",
        "admin_help_grupos": "👥 **Grupos**\n\nUsa:\n`/grupos`\n`/activargrupo ID_DEL_GRUPO`\n`/desactivargrupo ID_DEL_GRUPO`",
        "admin_help_id": f"🆔 **Tu ID**\n\n`{user_id}`",
    }

    await query.message.reply_text(
        help_messages.get(query.data, "Opción no disponible."),
        parse_mode='Markdown',
        reply_markup=admin_panel_keyboard()
    )

async def vip_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not auth_system.is_admin(user_id):
        await query.message.reply_text("⛔ Esta opción es solo para administradores.")
        return

    data = user_data_store.get(user_id)
    if not data or data.get("tipo") not in {"agregar_usuario", "renovar_usuario"}:
        await query.message.reply_text(
            "ℹ️ No hay una activación VIP en curso.\n\n"
            "Usa /agregar o /renovar para empezar.",
            reply_markup=admin_panel_keyboard()
        )
        return

    duration_text = query.data.replace("vip_time_", "", 1)
    if duration_text == "cancelar":
        user_data_store.pop(user_id, None)
        await query.message.reply_text("✅ Acción VIP cancelada. Ya puedes usar otro comando.")
        return
    tipo = data.get("tipo")

    try:
        if tipo == "agregar_usuario":
            if data.get("step") != 2:
                await query.message.reply_text("Primero completa el ID y el nombre del usuario.")
                return
            fecha_vencimiento = await apply_vip_duration(
                context,
                query.message.chat_id,
                user_id,
                data["admin_name"],
                data["target_user_id"],
                data["nombre"],
                duration_text,
                action_label="activado"
            )
            logging.debug(f"[ADMIN] {user_id} agregó usuario {data['target_user_id']} ({data['nombre']}) - Vence: {fecha_vencimiento}")
        else:
            if data.get("step") != 1:
                await query.message.reply_text("Primero envía el ID del usuario a renovar.")
                return
            target_user_id = data["target_user_id"]
            current_name = auth_system.get_authorized_users().get(target_user_id, f"Usuario_{target_user_id}")
            await apply_vip_duration(
                context,
                query.message.chat_id,
                user_id,
                data["admin_name"],
                target_user_id,
                current_name,
                duration_text,
                action_label="renovado"
            )

        del user_data_store[user_id]
    except ValueError:
        await query.message.reply_text(
            "❌ **Duración inválida**\n\n"
            "Usa algo desde **1 hora** en adelante.",
            parse_mode='Markdown',
            reply_markup=vip_duration_keyboard()
        )
    except Exception as e:
        logging.error(f"Error al aplicar duración VIP: {e}")
        await alert_owner_error(context, "vip_duration_callback", e)
        await query.message.reply_text(f"❌ Error al guardar el VIP: {str(e)}")

async def vip_manage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not auth_system.is_admin(user_id):
        await query.message.reply_text("⛔ Esta opción es solo para administradores.")
        return

    parts = query.data.split("_")
    if len(parts) < 4:
        await query.message.reply_text("❌ Acción inválida.")
        return

    action = parts[2]
    option = parts[3] if action == "renew" else ""
    try:
        target_user_id = int(parts[4] if action == "renew" else parts[3])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ ID inválido.")
        return

    admin_name = query.from_user.first_name or "Admin"
    current_name = auth_system.get_authorized_users().get(target_user_id, f"Usuario_{target_user_id}")

    if action == "confirmremove":
        await query.message.reply_text(
            f"⚠️ ¿Seguro que quieres quitar el VIP a `{target_user_id}`?",
            parse_mode='Markdown',
            reply_markup=confirm_action_keyboard("remove", target_user_id)
        )
        return

    if action == "confirmban":
        await query.message.reply_text(
            f"⚠️ ¿Seguro que quieres banear a `{target_user_id}`?",
            parse_mode='Markdown',
            reply_markup=confirm_action_keyboard("ban", target_user_id)
        )
        return

    if action == "cancel":
        await query.message.reply_text("✅ Acción cancelada.")
        return

    if action == "history":
        await send_user_history(query.message, target_user_id)
        return

    if action == "renew":
        duration_map = {
            "1h": "1 hora",
            "7d": "7 dias",
            "1m": "1 mes",
            "perm": "permanente",
        }
        duration = duration_map.get(option)
        if not duration:
            await query.message.reply_text("❌ Duración inválida.")
            return
        await apply_vip_duration(
            context,
            query.message.chat_id,
            user_id,
            admin_name,
            target_user_id,
            current_name,
            duration,
            action_label="renovado"
        )
        return

    if action == "remove":
        if auth_system.remove_user(target_user_id, removed_by=user_id, removed_by_name=admin_name):
            await query.message.reply_text(f"✅ VIP removido para `{target_user_id}`.", parse_mode='Markdown')
            await notify_main_admin(context, user_id, admin_name, "Eliminó usuario", str(target_user_id))
        else:
            await query.message.reply_text(f"ℹ️ `{target_user_id}` no estaba en VIP.", parse_mode='Markdown')
        return

    if action == "ban":
        auth_system.ban_user(target_user_id, banned_by=user_id, banned_by_name=admin_name)
        await query.message.reply_text(f"🚫 Usuario `{target_user_id}` baneado.", parse_mode='Markdown')
        await notify_main_admin(context, user_id, admin_name, "Baneó usuario", str(target_user_id))
        return

    await query.message.reply_text("❌ Acción no disponible.")

async def users_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not auth_system.is_admin(query.from_user.id):
        await query.message.reply_text("⛔ Esta opción es solo para administradores.")
        return
    parts = query.data.split("_")
    try:
        mode = parts[2]
        offset = int(parts[3])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ Página inválida.")
        return
    await send_users_page(query.message, mode, offset)

async def send_user_history(message, target_user_id: int):
    audit = [
        item for item in auth_system.get_audit_log()
        if str(item.get("target_id")) == str(target_user_id)
    ][-20:]
    lines = ["📜 **Historial de usuario**", "━━━━━━━━━━━━━━", f"🆔 Usuario: `{target_user_id}`\n"]
    if not audit:
        lines.append("📭 No hay historial registrado.")
    for item in reversed(audit):
        lines.append(
            f"🕐 {format_audit_time(item.get('created_at'))}\n"
            f"⚙️ {md_escape(item.get('action'))}\n"
            f"👑 {md_escape(item.get('admin_name'))} (`{md_escape(item.get('admin_id'))}`)\n"
            f"📝 {md_escape(item.get('details') or 'Sin detalle')}"
        )
    await message.reply_text("\n\n".join(lines), parse_mode='Markdown')

async def agregar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("❌ Comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if not is_admin_control_chat(chat_id, user_id):
        await update.message.reply_text(
            "⛔ **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
        return
        return
    
    # Iniciar proceso interactivo
    user_data_store[user_id] = {
        "step": 0, 
        "tipo": "agregar_usuario",
        "admin_name": update.effective_user.first_name or "Admin",
        "chat_id": update.effective_chat.id
    }
    await update.message.reply_text(
        "💎 **Agregar VIP**\n\n"
        "Paso **1 de 3**\n"
        "Envía el ID de Telegram del usuario.\n\n"
        "Ejemplo: `123456789`",
        parse_mode='Markdown'
    )

async def renovar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return

    if not is_admin_control_chat(chat_id, user_id):
        await update.message.reply_text("⛔ Este comando solo puede usarse en privado o en el grupo autorizado.")
        return

    if len(context.args) >= 2:
        try:
            target_user_id = int(context.args[0])
            duration_text = " ".join(context.args[1:])
            current_name = auth_system.get_authorized_users().get(target_user_id, f"Usuario_{target_user_id}")
            await apply_vip_duration(
                context,
                update.effective_chat.id,
                user_id,
                update.effective_user.first_name or "Admin",
                target_user_id,
                current_name,
                duration_text,
                action_label="renovado"
            )
            return
        except ValueError:
            await update.message.reply_text(
                "❌ Uso: `/renovar ID 1 hora`\n\n"
                "Ejemplos: `/renovar 123456789 1 hora`, `/renovar 123456789 7 dias`, `/renovar 123456789 permanente`",
                parse_mode='Markdown'
            )
            return

    user_data_store[user_id] = {
        "step": 0,
        "tipo": "renovar_usuario",
        "admin_name": update.effective_user.first_name or "Admin",
        "chat_id": update.effective_chat.id
    }
    await update.message.reply_text(
        "🔁 **Renovar VIP**\n\n"
        "Paso **1 de 2**\n"
        "Envía el ID del usuario que vas a renovar.\n\n"
        "Ejemplo: `123456789`",
        parse_mode='Markdown'
    )

async def eliminar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if not is_admin_control_chat(chat_id, user_id):
        await update.message.reply_text("⛔ Validación incorrecta.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso: `/eliminar ID_DEL_USUARIO`", parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(context.args[0])
        if auth_system.remove_user(target_user_id, removed_by=user_id, removed_by_name=update.effective_user.first_name):
            await update.message.reply_text(f"✅ Usuario `{target_user_id}` removido del VIP.", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"ℹ️ Usuario `{target_user_id}` no estaba en VIP.", parse_mode='Markdown')
        logging.debug(f"[ADMIN] {user_id} eliminó usuario {target_user_id} en chat {chat_id}")
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Eliminó usuario", str(target_user_id))
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if not is_admin_control_chat(chat_id, user_id):
        await update.message.reply_text(
            "⛔ **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
    
    auth_system.cleanup_expired_users()
    stats = auth_system.get_stats()
    authorized_users = auth_system.get_authorized_users()
    banned_users = auth_system.get_banned_users()
    admin_users = auth_system.get_admin_users()
    
    message = "📊 **Estadísticas del bot**\n\n"
    message += "━━━━━━━━━━━━━━\n"
    message += f"💎 VIP activos: **{stats['total_authorized']}**\n"
    message += f"🚫 Baneados: **{stats['total_banned']}**\n"
    message += f"👑 Administradores: **{stats['total_admins']}**\n"
    message += f"👥 Grupos activos: **{stats['total_groups']}**\n"
    message += f"📣 Grupo/canal: `{stats['allowed_group']}`\n\n"
    
    # Mostrar administradores
    message += "👑 **Administradores**\n"
    for line in owner_lines():
        message += f"{line}\n"
    for line in supervisor_lines():
        message += f"{line}\n"
    if admin_users:
        for uid in admin_users:
            if uid in SUPERVISOR_ADMIN_IDS:
                continue
            user_name = authorized_users.get(uid, f"Usuario_{uid}")
            message += f"👑 `{uid}` - {md_escape(user_name)}\n"
    
    if authorized_users:
        message += "\n💎 **Usuarios VIP**\n"
        for uid, nombre in authorized_users.items():
            if uid != auth_system.admin_id and uid not in admin_users:
                vencimiento = format_vip_expiration(auth_system.get_user_expiration(uid))
                message += f"• `{uid}` - {md_escape(nombre)} - vence: {vencimiento}\n"
    else:
        message += "\n📭 No hay usuarios VIP activos.\n"
    
    if banned_users:
        message += "\n🚫 **Usuarios baneados**\n"
        for uid in banned_users:
            message += f"• `{uid}`\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if not is_admin_control_chat(chat_id, user_id):
        await update.message.reply_text(
            "⛔ **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
        return
    
    if not context.args:
        await update.message.reply_text("Uso: `/ban ID_DEL_USUARIO motivo opcional`", parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(context.args[0])
        reason = " ".join(context.args[1:]).strip() or "Sin motivo"
        auth_system.ban_user(target_user_id, banned_by=user_id, banned_by_name=update.effective_user.first_name)
        auth_system.log_action("ban_reason", user_id, update.effective_user.first_name, target_user_id, reason)
        await update.message.reply_text(
            f"🚫 Usuario `{target_user_id}` baneado.\n\n📝 Motivo: {md_escape(reason)}",
            parse_mode='Markdown'
        )
        logging.debug(f"[ADMIN] {user_id} baneó usuario {target_user_id} en chat {chat_id}")
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Baneó usuario", f"{target_user_id} | {reason}")
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if not is_admin_control_chat(chat_id, user_id):
        await update.message.reply_text(
            "⛔ **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
        return
    
    if not context.args:
        await update.message.reply_text("Uso: `/unban ID_DEL_USUARIO`", parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(context.args[0])
        if auth_system.unban_user(target_user_id, unbanned_by=user_id, unbanned_by_name=update.effective_user.first_name):
            await update.message.reply_text(f"✅ Usuario `{target_user_id}` desbaneado.", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"ℹ️ Usuario `{target_user_id}` no estaba baneado.", parse_mode='Markdown')
        logging.debug(f"[ADMIN] {user_id} desbaneó usuario {target_user_id} en chat {chat_id}")
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Desbaneó usuario", str(target_user_id))
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")

async def vipcheck_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return

    if not context.args:
        await update.message.reply_text("Uso: `/vipcheck ID_DEL_USUARIO`", parse_mode='Markdown')
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")
        return

    await update.message.reply_text(
        vip_status_text(target_user_id),
        parse_mode='Markdown',
        reply_markup=vip_manage_keyboard(target_user_id)
    )

async def historial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return
    if not context.args:
        await update.message.reply_text("Uso: `/historial ID_DEL_USUARIO`", parse_mode='Markdown')
        return
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")
        return
    await send_user_history(update.message, target_user_id)

async def usuarios_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return

    mode = context.args[0].lower() if context.args else "vip"
    if mode not in {"vip", "activos", "vencidos", "expired", "baneados", "ban", "admins", "admin"}:
        await update.message.reply_text(
            "Uso: `/usuarios vip`, `/usuarios vencidos`, `/usuarios baneados` o `/usuarios admins`",
            parse_mode='Markdown'
        )
        return

    await send_users_page(update.message, mode, 0)

async def send_users_page(message, mode: str, offset: int = 0):
    auth_system.cleanup_expired_users()
    page_size = 10
    mode = mode.lower()

    if mode in {"vip", "activos"}:
        rows = [
            f"• `{uid}` - {md_escape(name)} - vence: {format_vip_expiration(auth_system.get_user_expiration(uid))}"
            for uid, name in auth_system.get_authorized_users().items()
        ]
        title = "💎 **Usuarios VIP activos**"
        mode_key = "vip"
    elif mode in {"vencidos", "expired"}:
        audit = [a for a in auth_system.get_audit_log() if a.get("action") in {"remove_vip", "expired_vip"}]
        rows = [
            f"• `{md_escape(item.get('target_id'))}` - {format_audit_time(item.get('created_at'))} - {md_escape(item.get('details') or 'Sin detalle')}"
            for item in reversed(audit)
        ]
        title = "⏳ **Últimos VIP removidos/vencidos**"
        mode_key = "vencidos"
    elif mode in {"baneados", "ban"}:
        rows = [f"• `{uid}`" for uid in auth_system.get_banned_users()]
        title = "🚫 **Usuarios baneados**"
        mode_key = "baneados"
    else:
        rows = owner_lines() + supervisor_lines() + [
            f"• `{uid}`" for uid in auth_system.get_admin_users()
            if uid not in SUPERVISOR_ADMIN_IDS
        ]
        title = "👑 **Administradores**"
        mode_key = "admins"

    total = len(rows)
    page = rows[offset:offset + page_size]
    lines = [title, "━━━━━━━━━━━━━━", f"Página: **{(offset // page_size) + 1}** | Total: **{total}**\n"]
    lines.extend(page or ["📭 No hay registros para mostrar."])
    await message.reply_text(
        "\n".join(lines),
        parse_mode='Markdown',
        reply_markup=users_page_keyboard(mode_key, offset, total, page_size)
    )

async def setprecio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "💰 **Editar precios**\n\n"
            "`/setprecio bot 1_mes 25000`\n"
            "`/setprecio bot 7_dias 10000`\n"
            "`/setprecio iphone 45000`\n"
            "`/setprecio daviplata 40000`\n"
            "`/setprecio nequi 3500000 48000`\n"
            "`/setprecio bancolombia 5000000 60000`",
            parse_mode='Markdown'
        )
        return

    category = context.args[0].lower()
    changed = False

    if category == "bot" and len(context.args) >= 3:
        plan_key = context.args[1].replace("_", " ").lower()
        new_price = normalize_price(context.args[2])
        updated = []
        for name, price in PRICE_DATA["bot"]:
            if plan_key in name.lower().replace("$", ""):
                updated.append((name, new_price))
                changed = True
            else:
                updated.append((name, price))
        PRICE_DATA["bot"] = updated
    elif category in {"iphone", "nequiiphone"}:
        PRICE_DATA["nequi_iphone"] = normalize_price(context.args[1])
        changed = True
    elif category == "daviplata":
        PRICE_DATA["daviplata"] = normalize_price(context.args[1])
        changed = True
    elif category in {"nequi", "app"} and len(context.args) >= 3:
        amount = normalize_price(context.args[1])
        new_price = normalize_price(context.args[2])
        updated = []
        for current_amount, price, emoji in PRICE_DATA["nequi_app"]:
            if current_amount.replace(".", "") == amount.replace(".", ""):
                updated.append((current_amount, new_price, emoji))
                changed = True
            else:
                updated.append((current_amount, price, emoji))
        PRICE_DATA["nequi_app"] = updated
    elif category == "bancolombia" and len(context.args) >= 3:
        amount = normalize_price(context.args[1])
        new_price = normalize_price(context.args[2])
        updated = []
        for current_amount, price in PRICE_DATA["bancolombia_app"]:
            if current_amount.replace(".", "") == amount.replace(".", ""):
                updated.append((current_amount, new_price))
                changed = True
            else:
                updated.append((current_amount, price))
        PRICE_DATA["bancolombia_app"] = updated

    if not changed:
        await update.message.reply_text("❌ No encontré ese plan. Revisa `/setprecio`.", parse_mode='Markdown')
        return

    save_json_file(PRICES_FILE, PRICE_DATA)
    auth_system.log_action("set_price", user_id, update.effective_user.first_name, None, " ".join(context.args))
    await update.message.reply_text(
        "✅ **Precio actualizado**\n\n"
        "El nuevo precio ya se verá en `/precios`.",
        parse_mode='Markdown'
    )

async def mantenimiento_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return

    if not context.args or context.args[0].lower() not in {"on", "off"}:
        state = "activo" if is_maintenance_enabled() else "apagado"
        await update.message.reply_text(
            f"🛠️ Mantenimiento actual: **{state}**\n\nUsa `/mantenimiento on` o `/mantenimiento off`.",
            parse_mode='Markdown'
        )
        return

    enabled = context.args[0].lower() == "on"
    set_maintenance(enabled)
    auth_system.log_action("maintenance", user_id, update.effective_user.first_name, None, "on" if enabled else "off")
    await update.message.reply_text(f"🛠️ Mantenimiento **{'activado' if enabled else 'desactivado'}**.", parse_mode='Markdown')

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para owners.")
        return
    files = ["auth_data.json", PRICES_FILE, SETTINGS_FILE]
    sent = 0
    for path in files:
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            await update.message.reply_document(document=f, filename=path)
        sent += 1
    await update.message.reply_text(f"✅ Backup enviado. Archivos: {sent}")

async def acciones_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return

    audit = auth_system.get_audit_log()[-20:]
    allowed_actions = {"add_vip", "remove_vip", "ban", "unban", "add_admin", "remove_admin", "maintenance", "set_price"}
    visible = [item for item in audit if item.get("action") in allowed_actions]

    if not is_owner(user_id):
        visible = [
            item for item in visible
            if item.get("action") in {"add_vip", "remove_vip", "ban", "unban", "set_price"}
        ][-10:]

    lines = ["🧾 **Acciones recientes**", "━━━━━━━━━━━━━━"]
    if not visible:
        lines.append("📭 No hay acciones recientes para mostrar.")
    for item in reversed(visible):
        lines.append(
            f"🕐 {format_audit_time(item.get('created_at'))}\n"
            f"⚙️ {md_escape(item.get('action'))}\n"
            f"👑 {md_escape(item.get('admin_name'))} (`{md_escape(item.get('admin_id'))}`)\n"
            f"🎯 `{md_escape(item.get('target_id'))}`"
        )

    await update.message.reply_text("\n\n".join(lines), parse_mode='Markdown')

async def supervisor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not can_view_supervisor_panel(user_id):
        await update.message.reply_text("⛔ Panel disponible solo para supervisor y owners.")
        return
    stats = auth_system.get_stats()
    text = (
        "🛡️ **Panel supervisor**\n\n"
        "━━━━━━━━━━━━━━\n"
        f"💎 VIP activos: **{stats['total_authorized']}**\n"
        f"🚫 Baneados: **{stats['total_banned']}**\n"
        f"🆔 Tu ID: `{user_id}`\n\n"
        "Accesos rápidos:\n"
        "📋 /usuarios vip\n"
        "🧾 /acciones\n"
        "🔎 /vipcheck ID\n"
        "❌ /cancelar"
    )
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=admin_panel_keyboard())

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para owners.")
        return
    if not context.args:
        await update.message.reply_text("Uso: `/broadcast mensaje para usuarios VIP`", parse_mode='Markdown')
        return
    text = " ".join(context.args)
    users = auth_system.get_authorized_users()
    sent = 0
    failed = 0
    for target_id in users:
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"📢 **Aviso importante**\n\n{md_escape(text)}",
                parse_mode='Markdown'
            )
            sent += 1
        except Exception:
            failed += 1
    auth_system.log_action("broadcast", user_id, update.effective_user.first_name, None, text[:120])
    await update.message.reply_text(f"✅ Broadcast enviado.\n\nEnviados: {sent}\nFallidos: {failed}")

async def preciosadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return
    await update.message.reply_text(
        "💰 **Panel rápido de precios**\n\n"
        "━━━━━━━━━━━━━━\n"
        "Usa estos formatos para editar:\n\n"
        "`/setprecio bot 7_dias 10000`\n"
        "`/setprecio bot 1_mes 25000`\n"
        "`/setprecio iphone 45000`\n"
        "`/setprecio daviplata 40000`\n"
        "`/setprecio nequi 3500000 48000`\n"
        "`/setprecio bancolombia 5000000 60000`\n\n"
        "Luego revisa con /precios.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🤖 Ver Bot VIP", callback_data="prices_bot_vip"),
                InlineKeyboardButton("📲 Ver Apps", callback_data="prices_nequi_app"),
            ]
        ])
    )

async def ayuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await comandos_command(update, context)

async def comandos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    in_group = is_group_chat(update)
    reply_markup = main_menu_keyboard(group_mode=True) if in_group else admin_panel_keyboard() if auth_system.is_admin(user_id) else user_home_keyboard()
    await update.message.reply_text(
        group_comandos_disponibles_text() if in_group else comandos_disponibles_text(user_id),
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def horarios_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_group_chat(update):
        await update.message.reply_text("ℹ️ Ese comando solo está disponible en privado.")
        return
    await update.message.reply_text(
        "🕒 **Horarios disponibles**\n\n"
        "El acceso funciona con membresía VIP activa. Si necesitas activación o soporte, contacta a un vendedor.",
        parse_mode='Markdown',
        reply_markup=sellers_keyboard(include_prices=False)
    )

async def reglas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        group_rules_text() if is_group_chat(update) else RULES_TEXT,
        parse_mode='Markdown'
    )

async def miestado_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_group_chat(update):
        await update.message.reply_text("ℹ️ Ese comando solo está disponible en privado.")
        return
    auth_system.update_activity(update.effective_user.id)
    await update.message.reply_text(user_status_text(update.effective_user.id), parse_mode='Markdown')

async def adminhelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("⛔ Comando disponible solo para administradores.")
        return
    await update.message.reply_text(
        "🛠️ **Ayuda admin**\n\n"
        "━━━━━━━━━━━━━━\n"
        "💎 `/agregar` - Agregar VIP por pasos\n"
        "🔁 `/renovar ID 1 mes` - Renovar VIP\n"
        "🔎 `/vipcheck ID` - Ver estado\n"
        "📋 `/usuarios vip` - Listar usuarios\n"
        "👥 `/grupos` - Panel de grupos\n"
        "✅ `/activargrupo ID` - Activar grupo por ID\n"
        "⛔ `/desactivargrupo ID` - Desactivar grupo por ID\n"
        "🧾 `/acciones` - Ver acciones recientes permitidas\n"
        "📜 `/historial ID` - Ver historial de un usuario\n"
        "🛡️ `/supervisor` - Panel limitado de supervisor\n"
        "❌ `/cancelar` - Cancelar acción pendiente\n"
        "🚫 `/ban ID` - Banear\n"
        "✅ `/unban ID` - Desbanear\n"
        "💰 `/setprecio` - Editar precios\n"
        "🛠️ `/mantenimiento on/off` - Modo mantenimiento\n"
        "👑 `/owner` - Panel privado owner",
        parse_mode='Markdown'
    )

async def grupo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = update.effective_chat

    if is_group_chat(update):
        await update.message.reply_text("🔒 Los datos del grupo se manejan por privado desde `/grupos`.")
        return

    if not auth_system.is_admin(user_id):
        await update.message.reply_text("Comando disponible solo para administradores del bot.")
        return

    groups = auth_system.get_active_groups()
    group_data = groups.get(chat.id, {})
    invite_link = group_data.get("invite_link")
    if not invite_link and chat.type in {"group", "supergroup"}:
        invite_link = await get_chat_invite_link(context, chat.id)

    await update.message.reply_text(
        "Datos de este chat\n\n"
        f"Nombre: {chat.title or chat.first_name or 'Sin nombre'}\n"
        f"Tipo: {chat.type}\n"
        f"ID: {chat.id}\n\n"
        f"Activo para el bot: {'Sí' if auth_system.is_group_active(chat.id) else 'No'}\n"
        f"Horario: {group_schedule_text(chat.id)}\n"
        f"Link: {invite_link or 'No disponible'}\n\n"
        "Usa /grupos para activar o desactivar por ID."
    )

async def verificar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para verificar el estado de membresía del usuario"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Intentar verificar membresía
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_GROUP_ID, user_id=user_id)
        status = member.status
        
        status_emoji = {
            'creator': '👑',
            'administrator': '🔧',
            'member': '✅',
            'restricted': '⚠️',
            'left': '❌',
            'kicked': '🚫'
        }
        
        emoji = status_emoji.get(status, '❓')
        
        message = f"{emoji} **Estado de Verificación**\n\n"
        message += f"🆔 Tu ID: `{user_id}`\n"
        message += f"👥 Grupo ID: `{REQUIRED_GROUP_ID}`\n"
        message += f"📊 Estado: **{status.upper()}**\n\n"
        
        if status in ['member', 'administrator', 'creator', 'restricted']:
            if auth_system.is_admin(user_id):
                message += "✅ **Eres administrador del bot**"
            elif auth_system.can_use_bot(user_id, chat_id):
                message += "✅ **Eres usuario VIP**"
            else:
                message += "✅ **Estas en el grupo**\n\n"
                message += "🔴 **No eres usuario VIP**\n"
                message += "Contacta a un vendedor para activar tu acceso."
        else:
            message += "❌ **No tienes acceso al bot**\n"
            message += f"👉 Únete aquí: {GROUP_INVITE_URL}"
        
        reply_markup = sellers_keyboard() if (
            status in ['member', 'administrator', 'creator', 'restricted']
            and not auth_system.is_admin(user_id)
            and not auth_system.can_use_bot(user_id, chat_id)
        ) else None
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        error_msg = str(e)
        
        message = "⚠️ **ERROR DE CONFIGURACIÓN**\n\n"
        
        if "bot is not a member" in error_msg.lower() or "chat not found" in error_msg.lower():
            message += "🤖 **El bot NO está en el grupo**\n\n"
            message += "🔴 **IMPORTANTE:** El bot debe estar en el grupo para funcionar\n\n"
            message += "📌 **Pasos para solucionarlo:**\n"
            message += "1️⃣ Agrega el bot al grupo\n"
            message += "2️⃣ Hazlo administrador del grupo\n"
            message += "3️⃣ Reinicia el bot\n\n"
            message += "❌ **Mientras tanto, NADIE puede usar el bot**"
        elif "forbidden" in error_msg.lower():
            message += "🚫 **El bot no tiene permisos de administrador**\n\n"
            message += "🔴 **IMPORTANTE:** El bot necesita ser admin\n\n"
            message += "📌 **Solución:**\n"
            message += "1️⃣ Ve a la configuración del grupo\n"
            message += "2️⃣ Busca al bot en la lista de miembros\n"
            message += "3️⃣ Hazlo administrador\n\n"
            message += "❌ **Mientras tanto, NADIE puede usar el bot**"
        else:
            message += f"🔴 **Error técnico:** `{md_escape(error_msg)}`\n\n"
            message += "❌ **El bot no puede verificar miembros**\n"
            message += "📞 Contacta a los administradores:"
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=sellers_keyboard())

async def precios_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los precios del servicio premium"""
    if is_group_chat(update):
        await update.message.reply_text("ℹ️ Ese comando solo está disponible en privado.")
        return
    if not await require_channel_for_plans(update, context):
        return

    await update.message.reply_text(
        "💎 **Catalogo VIP**\n"
        "━━━━━━━━━━━━━━\n\n"
        "🤖 **TARIFAS BOT**\n"
        f"{format_bot_prices()}\n\n"
        "📲 **APLICACIONES VIP**\n"
        f"{format_app_prices()}\n\n"
        "━━━━━━━━━━━━━━\n"
        "📞 **Para comprar o activar tu acceso, contacta a un vendedor:**",
        parse_mode='Markdown',
        reply_markup=sellers_keyboard()
    )

async def cancelar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in user_data_store:
        tipo = user_data_store[user_id].get("tipo", "orden")
        del user_data_store[user_id]
        await update.message.reply_text(
            "✅ **Acción cancelada**\n\n"
            f"Se cerró la acción pendiente: `{md_escape(tipo)}`.\n"
            "Ya puedes usar otro comando normalmente.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "ℹ️ No tienes acciones pendientes.\n\n"
            "Usa /comprobante para abrir el menú o /panel si eres admin."
        )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text(" Solo el administrador puede usar este comando.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if not is_admin_control_chat(chat_id, user_id):
        await update.message.reply_text("⛔ Este comando solo se puede usar en el grupo autorizado o en privado.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Uso: `/admin ID_DEL_USUARIO`", parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(context.args[0])
        auth_system.add_admin(target_user_id, added_by=user_id, added_by_name=update.effective_user.first_name)
        await update.message.reply_text(f"👑 Usuario `{target_user_id}` agregado como administrador.", parse_mode='Markdown')
        logging.debug(f"[ADMIN] {user_id} agregó administrador {target_user_id} en chat {chat_id}")
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Agregó administrador", str(target_user_id))
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")

async def unadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text(" Solo el administrador puede usar este comando.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if not is_admin_control_chat(chat_id, user_id):
        await update.message.reply_text("⛔ Este comando solo se puede usar en el grupo autorizado o en privado.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso: `/unadmin ID_DEL_USUARIO`", parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(context.args[0])
        if auth_system.remove_admin(target_user_id, removed_by=user_id, removed_by_name=update.effective_user.first_name):
            await update.message.reply_text(f"✅ Usuario `{target_user_id}` removido como administrador.", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"ℹ️ Usuario `{target_user_id}` no era administrador.", parse_mode='Markdown')
        logging.debug(f"[ADMIN] {user_id} removió administrador {target_user_id} en chat {chat_id}")
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Removió administrador", str(target_user_id))
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para fotos - actualmente no se usa"""
    pass

async def refe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda una foto como referencia cuando se responde a ella"""
    user_id = update.effective_user.id
    
    # Verificar si es admin
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("❌ Este comando solo está disponible para administradores.")
        return
    
    # Verificar si está respondiendo a un mensaje
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Debes responder a una foto con /refe para guardarla como referencia.")
        return
    
    # Verificar si el mensaje tiene una foto
    replied_message = update.message.reply_to_message
    if not replied_message.photo:
        await update.message.reply_text("❌ El mensaje debe contener una foto.")
        return
    
    try:
        # Obtener la foto de mayor calidad
        photo = replied_message.photo[-1]
        file_id = photo.file_id
        
        # Obtener información adicional
        admin_name = update.effective_user.first_name or "Admin"
        now = datetime.now(pytz.timezone("America/Bogota"))
        fecha = now.strftime("%d/%m/%Y %H:%M:%S")
        
        # Cargar referencias existentes
        referencias = cargar_referencias()
        
        # Agregar nueva referencia
        nueva_referencia = {
            "file_id": file_id,
            "guardado_por": admin_name,
            "user_id": user_id,
            "fecha": fecha,
            "numero": len(referencias) + 1
        }
        
        referencias.append(nueva_referencia)
        guardar_referencias(referencias)
        
        await update.message.reply_text(
            f"✅ **Referencia guardada**\n\n"
            f"📸 **Número:** #{nueva_referencia['numero']}\n"
            f"👤 **Guardado por:** {admin_name}\n"
            f"📅 **Fecha:** {fecha}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"Error al guardar referencia: {e}")
        await update.message.reply_text(f"❌ Error al guardar referencia: {str(e)}")

async def referencias_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra todas las referencias guardadas"""
    user_id = update.effective_user.id
    
    # Verificar si es admin
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("❌ Este comando solo está disponible para administradores.")
        return
    
    try:
        referencias = cargar_referencias()
        
        if not referencias:
            await update.message.reply_text("📭 No hay referencias guardadas aún.")
            return
        
        # Enviar las primeras 5 referencias
        await enviar_referencias_paginadas(update, context, referencias, 0)
        
    except Exception as e:
        logging.error(f"Error al mostrar referencias: {e}")
        await update.message.reply_text(f"❌ Error al mostrar referencias: {str(e)}")

async def enviar_referencias_paginadas(update_or_query, context: ContextTypes.DEFAULT_TYPE, referencias, offset):
    """Envía referencias en grupos de 5"""
    # Determinar si es un update o un callback_query
    if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query is not None:
        query = update_or_query.callback_query
        chat_id = query.message.chat_id
        is_callback = True
    else:
        chat_id = update_or_query.effective_chat.id
        is_callback = False
    
    total = len(referencias)
    fin = min(offset + 5, total)
    referencias_a_enviar = referencias[offset:fin]
    
    # Lista para guardar los message_ids de las fotos enviadas
    message_ids = []
    
    # Enviar cada referencia como foto (sin compresión usando send_document)
    for ref in referencias_a_enviar:
        caption = (
            f"📸 **Referencia #{ref['numero']}**\n"
            f"👤 Guardado por: {md_escape(ref['guardado_por'])}\n"
            f"📅 Fecha: {md_escape(ref['fecha'])}"
        )
        
        try:
            # Primero obtener el archivo
            file = await context.bot.get_file(ref['file_id'])
            # Descargar el archivo
            file_path = await file.download_to_drive()
            
            # Enviar como documento para evitar compresión
            with open(file_path, 'rb') as photo_file:
                msg = await context.bot.send_document(
                    chat_id=chat_id,
                    document=photo_file,
                    caption=caption,
                    parse_mode='Markdown',
                    filename=f"referencia_{ref['numero']}.jpg"
                )
            message_ids.append(msg.message_id)
            
            # Eliminar archivo temporal
            try:
                os.remove(file_path)
            except:
                pass
                
        except Exception as e:
            logging.error(f"Error al enviar referencia #{ref['numero']}: {e}")
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error al enviar referencia #{ref['numero']}: {str(e)}"
            )
            message_ids.append(msg.message_id)
    
    # Si hay más referencias, mostrar botón
    if fin < total:
        keyboard = [[InlineKeyboardButton(
            f"📥 Enviar las siguientes 5 ({fin + 1}-{min(fin + 5, total)} de {total})",
            callback_data=f"ref_next_{fin}_{','.join(map(str, message_ids))}"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="👇 Presiona el botón para ver más referencias:",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Todas las referencias han sido enviadas."
        )

async def referencias_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el callback de paginación de referencias"""
    query = update.callback_query
    await query.answer()
    
    # Extraer datos del callback
    data_parts = query.data.split('_')
    offset = int(data_parts[2])
    message_ids_str = data_parts[3]
    message_ids = [int(mid) for mid in message_ids_str.split(',')]
    
    # Borrar mensajes anteriores
    for msg_id in message_ids:
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=msg_id
            )
        except Exception as e:
            logging.error(f"Error al borrar mensaje {msg_id}: {e}")
    
    # Borrar el mensaje del botón
    try:
        await query.message.delete()
    except:
        pass
    
    # Cargar referencias y enviar las siguientes
    referencias = cargar_referencias()
    await enviar_referencias_paginadas(update, context, referencias, offset)

async def prices_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra precios separados para Bot VIP y App Nequi VIP."""
    query = update.callback_query
    await query.answer()

    if not await require_channel_for_plans(update, context):
        return

    if query.data == "prices_bot_vip":
        title = "🤖 **TARIFAS BOT**"
        description = (
            "Acceso premium al bot por ID de Telegram.\n"
            "El plan queda activo con fecha de vencimiento."
        )
        price_text = format_bot_prices()
    else:
        title = "📲 **APLICACIONES VIP**"
        description = (
            "Tarifas disponibles para aplicaciones y servicios VIP.\n"
            "La activacion se coordina con un vendedor."
        )
        price_text = format_app_prices()

    await query.message.reply_text(
        f"{title}\n\n"
        f"{description}\n\n"
        f"{price_text}\n\n"
        "━━━━━━━━━━━━━━\n"
        "📞 **Contacta a un vendedor:**",
        parse_mode='Markdown',
        reply_markup=sellers_keyboard(include_prices=False)
    )

async def check_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_member_of_required_channel(context.bot, query.from_user.id):
        await query.message.reply_text(
            "Todavia no apareces como miembro del canal.\n\n"
            "Unete, espera unos segundos y vuelve a tocar **Ya me uni**.",
            parse_mode='Markdown',
            reply_markup=optional_group_keyboard()
        )
        return

    await query.message.reply_text(
        "✅ **Canal verificado**\n\n"
        "Ya puedes ver los planes disponibles.",
        parse_mode='Markdown'
    )
    await query.message.reply_text(
        "💎 **Catalogo VIP**\n"
        "━━━━━━━━━━━━━━\n\n"
        "🤖 **TARIFAS BOT**\n"
        f"{format_bot_prices()}\n\n"
        "📲 **APLICACIONES VIP**\n"
        f"{format_app_prices()}\n\n"
        "━━━━━━━━━━━━━━\n"
        "📞 **Para comprar o activar tu acceso, contacta a un vendedor:**",
        parse_mode='Markdown',
        reply_markup=sellers_keyboard()
    )

async def rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    is_group = query.message and query.message.chat and query.message.chat.type in {"group", "supergroup"}
    await query.message.reply_text(group_rules_text() if is_group else RULES_TEXT, parse_mode='Markdown')

async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(user_status_text(query.from_user.id), parse_mode='Markdown')

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "🧭 **Menú rápido**\n\n"
        "Usa los botones para consultar estado, reglas, planes o soporte.",
        parse_mode='Markdown',
        reply_markup=user_home_keyboard()
    )

async def request_access_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    text = (
        "💎 **Solicitud de acceso**\n\n"
        f"👤 Usuario: {md_escape(user.first_name or 'Sin nombre')}\n"
        f"🆔 ID: `{user.id}`\n"
        f"🔗 Username: @{md_escape(user.username) if user.username else 'sin_username'}\n\n"
        "El usuario quiere activar acceso VIP."
    )
    for target in OWNER_IDS + SUPERVISOR_ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=target, text=text, parse_mode='Markdown')
        except Exception:
            pass
    await query.message.reply_text(
        "✅ Solicitud enviada.\n\nUn vendedor revisará tu ID y te contactará para activar el acceso.",
        reply_markup=sellers_keyboard(include_prices=False)
    )

async def fechas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa/desactiva el modo de fechas manuales"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si está baneado
    if auth_system.is_banned(user_id):
        await update.message.reply_text("Estás baneado de nuestros servicios")
        return
    
    # Verificar autorización
    if not auth_system.can_use_bot(user_id, chat_id):
        await send_vip_required_message(update)
        return
    
    # Alternar modo de fechas manuales
    if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
        fecha_manual_mode[user_id] = False
        await update.message.reply_text(
            "📅 **Fecha automática activada**\n\n"
            "✅ El bot volverá a usar la fecha actual automáticamente.",
            parse_mode='Markdown'
        )
    else:
        fecha_manual_mode[user_id] = True
        await update.message.reply_text(
            "📅 **Fecha manual activada**\n\n"
            "📝 Ingresa la fecha cuando el bot la solicite.\n\n"
            "Ejemplo: `06 de diciembre de 2025 a las 02:30 p. m.`\n\n"
            "Toca **📅 Fecha manual** otra vez o usa /fechas para volver a automático.",
            parse_mode='Markdown'
        )

async def refes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa/desactiva el modo de referencias manuales"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si está baneado
    if auth_system.is_banned(user_id):
        await update.message.reply_text("Estás baneado de nuestros servicios")
        return
    
    # Verificar autorización
    if not auth_system.can_use_bot(user_id, chat_id):
        await send_vip_required_message(update)
        return
    
    # Alternar modo de referencias manuales
    if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
        referencia_manual_mode[user_id] = False
        await update.message.reply_text(
            "🔢 **Referencia automática activada**\n\n"
            "✅ El bot volverá a generar la referencia automáticamente.",
            parse_mode='Markdown'
        )
    else:
        referencia_manual_mode[user_id] = True
        await update.message.reply_text(
            "🔢 **Referencia manual activada**\n\n"
            "🔢 Ingresa la referencia cuando el bot la solicite.\n\n"
            "Ejemplo: `M12345678`\n\n"
            "Toca **🔢 Referencia manual** otra vez o usa /refes para volver a automático.",
            parse_mode='Markdown'
        )

def public_bot_commands():
    return [
        BotCommand("start", "Iniciar"),
        BotCommand("comprobante", "Abrir generador"),
        BotCommand("comandos", "Ver comandos"),
        BotCommand("reglas", "Reglas de uso"),
        BotCommand("miestado", "Ver mi estado"),
        BotCommand("soporte", "Contactar soporte"),
        BotCommand("cancelar", "Cancelar acción actual"),
    ]

def group_bot_commands():
    return [
        BotCommand("comprobante", "Abrir generador"),
        BotCommand("reglas", "Reglas de uso"),
        BotCommand("cancelar", "Cancelar acción"),
    ]

def admin_bot_commands():
    return public_bot_commands() + [
        BotCommand("panel", "Panel de administrador"),
        BotCommand("grupos", "Panel de grupos"),
        BotCommand("agregar", "Agregar VIP"),
        BotCommand("renovar", "Renovar VIP"),
        BotCommand("usuarios", "Listar usuarios"),
        BotCommand("vipcheck", "Revisar VIP"),
    ]

def owner_bot_commands():
    return admin_bot_commands() + [
        BotCommand("owner", "Panel privado owner"),
    ]

async def refresh_group_command_menu(bot, group_id: int):
    """Show only the basic user commands in active groups to avoid admin clutter."""
    try:
        await bot.set_my_commands(
            group_bot_commands(),
            scope=BotCommandScopeChat(chat_id=group_id)
        )
    except Exception as e:
        logging.warning(f"No se pudieron configurar comandos para el grupo {group_id}: {e}")

async def reset_group_command_menu(bot, group_id: int):
    """Hide command suggestions when the bot is disabled in a group."""
    try:
        await bot.set_my_commands(
            [],
            scope=BotCommandScopeChat(chat_id=group_id)
        )
    except Exception as e:
        logging.warning(f"No se pudieron restaurar comandos publicos para el grupo {group_id}: {e}")

async def setup_bot_commands(app):
    public_commands = public_bot_commands()
    admin_commands = admin_bot_commands()
    owner_commands = owner_bot_commands()

    await app.bot.set_my_commands(public_commands)
    scoped_admin_ids = list(dict.fromkeys(OWNER_IDS + ADDITIONAL_ADMIN_IDS))
    for admin_id in scoped_admin_ids:
        try:
            await app.bot.set_my_commands(
                owner_commands if is_owner(admin_id) else admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            logging.warning(
                f"No se pudieron configurar comandos privados para {admin_id}: {e}. "
                "Ese usuario debe abrir el bot con /start una vez."
            )

    for group_id in auth_system.get_active_groups():
        await refresh_group_command_menu(app.bot, group_id)

    try:
        expired = auth_system.cleanup_expired_users()
        expiring_lines = []
        for uid, name in auth_system.get_authorized_users().items():
            days_left = get_vip_days_left(auth_system.get_user_expiration(uid))
            if days_left in {0, 1, 3}:
                expiring_lines.append(f"• `{uid}` - {md_escape(name)} - vence en {days_left} día(s)")

        if expired or expiring_lines:
            message = "⏳ **Resumen de vencimientos VIP**\n\n"
            if expired:
                message += "🚫 **Vencidos removidos:**\n"
                message += "\n".join(f"• `{uid}`" for uid in expired)
                message += "\n\n"
            if expiring_lines:
                message += "⚠️ **Próximos a vencer:**\n"
                message += "\n".join(expiring_lines)
            for owner_id in OWNER_IDS:
                await app.bot.send_message(chat_id=owner_id, text=message, parse_mode='Markdown')
    except Exception as e:
        logging.warning(f"No se pudo enviar resumen de vencimientos: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logging.warning("Conflicto de getUpdates: hay otra instancia del bot corriendo con el mismo token.")
        return

    logging.error("Error no controlado", exc_info=context.error)
    try:
        for owner_id in OWNER_IDS:
            await context.bot.send_message(
                chat_id=owner_id,
                text=(
                    "⚠️ Error no controlado\n\n"
                    f"{str(context.error)[:900]}"
                )
            )
    except Exception:
        pass

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(setup_bot_commands).build()

    app.add_handler(MessageHandler(filters.ALL, unsupported_update_guard), group=-2)
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.COMMAND, inactive_group_guard), group=-1)
    app.add_handler(CallbackQueryHandler(inactive_group_callback_guard), group=-1)

    app.add_handler(CommandHandler("comprobante", start))
    app.add_handler(CommandHandler("cashcomprobante", start))
    app.add_handler(CommandHandler("start", start_redirect))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("soporte", soporte_command))
    app.add_handler(CommandHandler("cashsoporte", soporte_command))
    app.add_handler(CommandHandler("fechas", fechas_command))
    app.add_handler(CommandHandler("cashfechas", fechas_command))
    app.add_handler(CommandHandler("refes", refes_command))
    app.add_handler(CommandHandler("cashrefes", refes_command))
    app.add_handler(CommandHandler("precios", precios_command))
    app.add_handler(CommandHandler("comandos", comandos_command))
    app.add_handler(CommandHandler("cashcomandos", comandos_command))
    app.add_handler(CommandHandler("horarios", horarios_command))
    app.add_handler(CommandHandler("miestado", miestado_command))
    app.add_handler(CommandHandler("reglas", reglas_command))
    app.add_handler(CommandHandler("cashreglas", reglas_command))
    app.add_handler(CommandHandler("ayuda", ayuda_command))
    app.add_handler(CommandHandler("adminhelp", adminhelp_command))
    app.add_handler(CommandHandler("panel", admin_panel_command))
    app.add_handler(CommandHandler("owner", owner_panel_command))
    app.add_handler(CommandHandler("agregar", agregar_command))
    app.add_handler(CommandHandler("renovar", renovar_command))
    app.add_handler(CommandHandler("eliminar", eliminar_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("usuarios", usuarios_command))
    app.add_handler(CommandHandler("grupos", grupos_command))
    app.add_handler(CommandHandler("activargrupo", activargrupo_command))
    app.add_handler(CommandHandler("cashon", activargrupo_command))
    app.add_handler(CommandHandler("desactivargrupo", desactivargrupo_command))
    app.add_handler(CommandHandler("cashoff", desactivargrupo_command))
    app.add_handler(CommandHandler("cashhorario", cashhorario_command))
    app.add_handler(CommandHandler("cashschedule", cashhorario_command))
    app.add_handler(CommandHandler("horario", cashhorario_command))
    app.add_handler(CommandHandler("acciones", acciones_command))
    app.add_handler(CommandHandler("historial", historial_command))
    app.add_handler(CommandHandler("vipcheck", vipcheck_command))
    app.add_handler(CommandHandler("setprecio", setprecio_command))
    app.add_handler(CommandHandler("preciosadmin", preciosadmin_command))
    app.add_handler(CommandHandler("mantenimiento", mantenimiento_command))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("supervisor", supervisor_command))
    app.add_handler(CommandHandler("grupo", grupo_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("cancelar", cancelar_command))
    app.add_handler(CommandHandler("cashcancelar", cancelar_command))
    app.add_handler(CommandHandler("verificar", verificar_command))
    app.add_handler(CommandHandler("refe", refe_command))
    app.add_handler(CommandHandler("referencias", referencias_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_added_to_group))
    app.add_handler(CallbackQueryHandler(prices_callback, pattern="^prices_(bot_vip|nequi_app)$"))
    app.add_handler(CallbackQueryHandler(check_channel_callback, pattern="^check_channel$"))
    app.add_handler(CallbackQueryHandler(rules_callback, pattern="^show_rules$"))
    app.add_handler(CallbackQueryHandler(status_callback, pattern="^show_status$"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^show_menu$"))
    app.add_handler(CallbackQueryHandler(request_access_callback, pattern="^request_access$"))
    app.add_handler(CallbackQueryHandler(admin_groups_callback, pattern="^admin_groups_"))
    app.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_help_"))
    app.add_handler(CallbackQueryHandler(vip_duration_callback, pattern="^vip_time_"))
    app.add_handler(CallbackQueryHandler(vip_manage_callback, pattern="^vip_manage_"))
    app.add_handler(CallbackQueryHandler(users_page_callback, pattern="^users_page_"))
    app.add_handler(CallbackQueryHandler(owner_panel_callback, pattern="^owner_"))
    app.add_handler(CallbackQueryHandler(referencias_callback, pattern="^ref_next_"))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("unadmin", unadmin_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    public_webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    railway_public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if not public_webhook_url and railway_public_domain:
        public_webhook_url = f"https://{railway_public_domain}"
    if not public_webhook_url:
        public_webhook_url = "https://curry-production-41e1.up.railway.app"

    if public_webhook_url:
        webhook_path = os.getenv("WEBHOOK_PATH", "telegram-webhook").strip("/")
        webhook_url = f"{public_webhook_url.rstrip('/')}/{webhook_path}"
        logging.info("Iniciando Curry por webhook en Railway.")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", "8080")),
            url_path=webhook_path,
            webhook_url=webhook_url,
            secret_token=os.getenv("WEBHOOK_SECRET") or None,
            drop_pending_updates=True,
        )
        return

    logging.info("Iniciando Curry por polling.")
    app.run_polling(
        bootstrap_retries=-1,
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()

