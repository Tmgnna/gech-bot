# ============================================================
#  CAR EQUB BOT + ADMIN PANEL  — Professional Edition v2
# ============================================================
import asyncio, hmac, hashlib, time, logging, re, random, html, os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import config as cfg
import database as db

logging.basicConfig(level=getattr(logging, cfg.LOG_LEVEL, logging.INFO),
                    format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("equb")

# ============================================================
#  TEXTS
# ============================================================
T = {
    "am": {
        "welcome": (
            "🎟️ <b>እንኳን ደህና መጡ!</b>\n\n"
            "🚗 <b>የመኪና ዕጣ/እቁብ መግዣ ቦት</b>\n\n"
            "✨ እውነተኛ ዕድል ይሞክሩ፦\n"
            "🎯 ቀላል ምርጫ\n"
            "🎲 ራስ-ሰር የዕጣ ቁጥር\n"
            "🔒 የተጠበቀ ክፍያ\n\n"
            "👇 ቋንቋ ይምረጡ፦"
        ),
        "menu": (
            "🏠 <b>ዋና ምናሌ</b>\n\n"
            "ሰላም <b>{name}</b> 👋\n\n"
            "🎟️ ዕጣ ግዛ — አዲስ ዕድል ይጀምሩ\n"
            "📋 የእኔ ዕጣዎች — ያሉዎትን ይመልከቱ"
        ),
        "buy": "🎟️ ዕጣ ግዛ",
        "my": "📋 የእኔ ዕጣዎች",
        "how": "📖 እንዴት እንደሚሰራ",
        "support": "☎️ ድጋፍ",
        "back": "🔙 ተመለስ",
        "home": "🏠 ዋና ምናሌ",
        "pick_car": "🚗 <b>የሚፈልጉትን መኪና ይምረጡ፦</b>",
        "car_info": (
            "🚗 <b>{name}</b>\n{desc}\n\n"
            "💰 ዋጋ: <b>{price} ብር</b>\n"
            "📅 የመዝጊያ ቀን: {closing}\n"
            "🎯 የዕጣ ክልል: {tmin}–{tmax}\n"
            "🟢 ቀሪ: <b>{remaining}</b>\n"
            "🔴 የተያዙ: {taken}"
        ),
        "select_ticket": "🎟️ <b>የዕጣ ቁጥር ይምረጡ</b>\n\nራስ-ሰር ወይም በእጅ መምረጥ ይችላሉ፦",
        "random_btn": "🎲 ራስ-ሰር ምረጥ",
        "manual_btn": "✍️ ቁጥር አስገባ",
        "ask_number": "✍️ <b>የዕጣ ቁጥር ያስገቡ</b>\n\nከ {tmin} እስከ {tmax} ባለው ክልል ውስጥ፦",
        "invalid_number": "❌ ቁጥሩ {tmin}–{tmax} መሆን አለበት። እንደገና ይሞክሩ፦",
        "taken_number": "❌ <b>ቁጥር #{n} ተይዟል!</b>\n\nሌላ ይምረጡ ወይም ራስ-ሰር ይጠቀሙ፦",
        "no_available": "😔 ሁሉም ዕጣ ተይዟል።",
        "ticket_held": (
            "✅ <b>ዕጣ #{n} ለእርስዎ ተይዟል!</b>\n\n"
            "⏰ የሚጠብቅዎ ጊዜ: <b>{mins} ደቂቃ</b>\n\n"
            "አሁን ክፍያውን ይፈጽሙ 👇"
        ),
        "banks": (
            "💳 <b>የክፍያ አካውንቶች</b>\n\n"
            "🏦 CBE: <code>1000805382159</code>\n"
            "🏦 BOA: <code>267410666</code>\n"
            "🏦 Awash: <code>013201812592600</code>\n\n"
            "👤 <b>ባለቤት:</b> ጌታቸዉ ፍቃዱ ጅራታ\n\n"
            "💡 <i>ቁጥሩን በመጫን ቀላሉ ይቅዱ</i>\n\n"
            "⚠️ ክፍያ ከፈጸሙ በኋላ «ክፍያ ፈጸምኩ» ይጫኑ።"
        ),
        "paid_btn": "📤 ክፍያ ፈጸምኩ",
        "cancel_btn": "❌ ሰርዝ",
        "ask_shot": "📸 <b>የክፍያ ስክሪንሾት ይላኩ</b>\n\nክፍያውን ያረጋግጡና ፎቶ ይላኩ፦",
        "bad_shot": "❌ እባክዎ ፎቶ (ስክሪንሾት) ብቻ ይላኩ።",
        "ask_name": "👤 <b>ሙሉ ስምዎን ያስገቡ</b>\n\nለማንነት ማረጋገጫ፦",
        "ask_phone": "📱 <b>ስልክ ቁጥርዎን ያስገቡ</b>\n\nምሳሌ: 0912345678",
        "bad_phone": "❌ ስልክ ቁጥሩ ትክክል አይደለም። እንደ 0912345678 ያስገቡ፦",
        "confirm": (
            "📋 <b>ያረጋግጡ</b>\n\n"
            "🚗 {car}\n🎟️ ዕጣ: <b>#{ticket}</b>\n"
            "👤 {name}\n📱 {phone}"
        ),
        "confirm_ok": "✅ አረጋግጥ",
        "confirm_no": "❌ ሰርዝ",
        "canceled": "❌ ጥያቄው ተሰርዟል። ዕጣው ነፃ ሆኗል።",
        "sent": "✅ <b>ጥያቄዎ ለአድሚን ተልኳል!</b>\n\n⏰ በ24 ሰዓት ውስጥ ምላሽ ይጠብቁ።",
        "approved": "🎉 <b>ዕጣዎ ተረጋግጧል!</b>\n\n🚗 {car}\n🎟️ ዕጣ: #{ticket}\n\nመልካም ዕድል! 🍀",
        "rejected": "❌ <b>ጥያቄዎ ተመልሷል</b>\n\nምክንያት: {reason}",
        "no_orders": "📭 <b>እስካሁን ዕጣ የለዎትም።</b>",
        "orders": "🎟️ <b>የእርስዎ ዕጣዎች</b>\n",
        "how_text": (
            "📖 <b>እንዴት እንደሚሰራ</b>\n\n"
            "1️⃣ «ዕጣ ግዛ» ይጫኑ\n"
            "2️⃣ መኪና ይምረጡ\n"
            "3️⃣ የዕጣ ቁጥር ይምረጡ (ራስ-ሰር/እጅ)\n"
            "4️⃣ ክፍያ ይፈጽሙ\n"
            "5️⃣ ስክሪንሾት + ስም + ስልክ ይላኩ\n"
            "6️⃣ አድሚን ያረጋግጣል ✅"
        ),
        "support_text": "☎️ <b>ድጋፍ</b>\n\n{ss}",
        "session_expired": "⏰ የእርስዎ ዕጣ ጊዜ አልፏል። እንደገና ይሞክሩ።",
        "back_to_cars": "🔙 ወደ መኪናዎች",
        "choose_other": "🔄 ሌላ ቁጥር ምረጥ",
        "reminder": "⏰ <b>ማስታወሻ!</b>\n\nየዕጣ ቁጥር #{ticket} ጊዜው <b>1 ደቂቃ</b> ብቻ ቀርቷል! ክፍያውን አሁን ይፈጽሙ።",
    },
    "om": {
        "welcome": (
            "🎟️ <b>Baga nagaan dhuftan!</b>\n\n"
            "🚗 <b>Bot carraa konkolaataa</b>\n\n"
            "✨ Carraa dhugaa yaalaa:\n"
            "🎯 Filannoo salphaa\n"
            "🎲 Lakkoofsa ofumaan\n"
            "🔒 Kaffaltii nagaa\n\n"
            "👇 Afaan filadhaa:"
        ),
        "menu": (
            "🏠 <b>Menu Guddaa</b>\n\n"
            "Akkam <b>{name}</b> 👋\n\n"
            "🎟️ Carraa biti — Carraa haaraa jalqabi\n"
            "📋 Carraa koo — Kan qabdan ilaalaa"
        ),
        "buy": "🎟️ Carraa biti",
        "my": "📋 Carraa koo",
        "how": "📖 Akkamitti hojjeta",
        "support": "☎️ Deeggarsa",
        "back": "🔙 Deebi'i",
        "home": "🏠 Menu Guddaa",
        "pick_car": "🚗 <b>Konkolaataa filadhaa:</b>",
        "car_info": (
            "🚗 <b>{name}</b>\n{desc}\n\n"
            "💰 Gatii: <b>{price} Birr</b>\n"
            "📅 Guyyaa cufiinsaa: {closing}\n"
            "🎯 Carraa: {tmin}–{tmax}\n"
            "🟢 Hafe: <b>{remaining}</b>\n"
            "🔴 Qabame: {taken}"
        ),
        "select_ticket": "🎟️ <b>Lakkoofsa carraa filadhaa</b>\n\nOfumaan yookaan harkaan filachuu dandeessu:",
        "random_btn": "🎲 Ofumaan fili",
        "manual_btn": "✍️ Lakkoofsa galchi",
        "ask_number": "✍️ <b>Lakkoofsa carraa galchi</b>\n\n{min}–{max} gidduu:",
        "invalid_number": "❌ {tmin}–{tmax} gidduu ta'uu qaba. Irra deebi'i:",
        "taken_number": "❌ <b>Lakkoofsi #{n} qabameera!</b>\n\nKan biraa filadhu:",
        "no_available": "😔 Carraan hundi qabameera.",
        "ticket_held": (
            "✅ <b>Carraa #{n} siif qabameera!</b>\n\n"
            "⏰ Yeroo eegumsaa: <b>{mins} daqiiqaa</b>\n\n"
            "Amma kaffaltii raawwadhu 👇"
        ),
        "banks": (
            "💳 <b>Herrega kaffaltii</b>\n\n"
            "🏦 CBE: <code>1000805382159</code>\n"
            "🏦 BOA: <code>267410666</code>\n"
            "🏦 Awash: <code>013201812592600</code>\n\n"
            "👤 <b>Abbaa herregaa:</b> Geetachoo Fikaduu Jiraataa\n\n"
            "💡 <i>Lakkoofsa tuquun salphaatti garagalchi</i>\n\n"
            "⚠️ Kaffaltii booda «Kaffaltii raawwadhe» tuqi."
        ),
        "paid_btn": "📤 Kaffaltii raawwadhe",
        "cancel_btn": "❌ Haqi",
        "ask_shot": "📸 <b>Suuraa kaffaltii ergi</b>\n\nSuuraa ergi:",
        "bad_shot": "❌ Maaloo suuraa qofa ergi.",
        "ask_name": "👤 <b>Maqaa guutuu galchi</b>\n\nEenyummaa mirkaneessuuf:",
        "ask_phone": "📱 <b>Lakkoofsa bilbilaa galchi</b>\n\nFkn: 0912345678",
        "bad_phone": "❌ Bilbilli sirrii miti. Akka 0912345678:",
        "confirm": (
            "📋 <b>Mirkaneessi</b>\n\n"
            "🚗 {car}\n🎟️ Carraa: <b>#{ticket}</b>\n"
            "👤 {name}\n📱 {phone}"
        ),
        "confirm_ok": "✅ Mirkaneessi",
        "confirm_no": "❌ Haqi",
        "canceled": "❌ Haqameera. Carraan bilisa ta'e.",
        "sent": "✅ <b>Adminitti ergameera!</b>\n\n⏰ Sa'aatii 24 keessatti deebii eegaa.",
        "approved": "🎉 <b>Carraan keessan mirkanaa'e!</b>\n\n🚗 {car}\n🎟️ Carraa: #{ticket}\n\nCarraa gaarii! 🍀",
        "rejected": "❌ <b>Gaaffiin deebi'e</b>\n\nSababa: {reason}",
        "no_orders": "📭 <b>Carraa hin qabdan.</b>",
        "orders": "🎟️ <b>Carraa keessan</b>\n",
        "how_text": (
            "📖 <b>Akkamitti hojjeta</b>\n\n"
            "1️⃣ «Carraa biti» tuqi\n2️⃣ Konkolaataa filadhu\n"
            "3️⃣ Lakkoofsa carraa filadhu\n4️⃣ Kaffaltii raawwadhu\n"
            "5️⃣ Screenshot + Maqaa + Bilbila ergi\n6️⃣ Admin mirkaneessa ✅"
        ),
        "support_text": "☎️ <b>Deeggarsa</b>\n\n{ss}",
        "session_expired": "⏰ Yeroon carraa keessan dabreera.",
        "back_to_cars": "🔙 Konkolaataa",
        "choose_other": "🔄 Lakkoofsa biraa fili",
        "reminder": "⏰ <b>Yaadachiisa!</b>\n\nCarraan #{ticket} yeroo <b>1 daqiiqaa</b> qofa hafe! Amma kaffaltii raawwadhu.",
    },
}

def t(lang, key, **kw):
    txt = T.get(lang, T["am"]).get(key, "")
    return txt.format(**{k: html.escape(str(v), quote=True) for k, v in kw.items()}) if kw else txt

# ============================================================
#  KEYBOARDS
# ============================================================
def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇪🇹 አማርኛ", callback_data="lang:am"),
        InlineKeyboardButton(text="🇪🇹 Afaan Oromoo", callback_data="lang:om"),
    ]])

def main_menu(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "buy"), callback_data="menu:buy")],
        [InlineKeyboardButton(text=t(lang, "my"), callback_data="menu:my")],
        [
            InlineKeyboardButton(text=t(lang, "how"), callback_data="menu:how"),
            InlineKeyboardButton(text=t(lang, "support"), callback_data="menu:support"),
        ],
    ])

def cars_kb(lang, cars):
    rows = []
    for c in cars:
        rows.append([InlineKeyboardButton(
            text=f"🚗 {html.escape(str(c[1]))}  ·  {c[3]} ብር",
            callback_data=f"car:{c[0]}"
        )])
    rows.append([InlineKeyboardButton(text=t(lang, "home"), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def car_kb(lang, car_id, can_buy=True):
    rows = []
    if can_buy:
        rows.append([InlineKeyboardButton(
            text="🎟️ ዕጣ ምረጥ / Carraa fili",
            callback_data=f"buy:{car_id}"
        )])
    rows.append([InlineKeyboardButton(
        text=t(lang, "back_to_cars"), callback_data="menu:buy"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def ticket_action_kb(lang, car_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "random_btn"),
                                 callback_data=f"tkt:rand:{car_id}"),
            InlineKeyboardButton(text=t(lang, "manual_btn"),
                                 callback_data=f"tkt:man:{car_id}"),
        ],
        [InlineKeyboardButton(text=t(lang, "back"),
                              callback_data=f"car:{car_id}")],
    ])

def pay_kb(lang, oid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "paid_btn"),
                              callback_data=f"pay:paid:{oid}")],
        [InlineKeyboardButton(text=t(lang, "cancel_btn"),
                              callback_data=f"pay:cancel:{oid}")],
    ])

def confirm_kb(lang, oid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "confirm_ok"),
                                 callback_data=f"ok:{oid}"),
            InlineKeyboardButton(text=t(lang, "confirm_no"),
                                 callback_data=f"cancel:{oid}"),
        ],
    ])

def admin_kb(oid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"adm:ok:{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"adm:no:{oid}"),
    ]])

# ============================================================
#  BOT SETUP
# ============================================================
bot = Bot(cfg.BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

class BuyFSM(StatesGroup):
    manual_number = State()
    shot = State()
    name = State()
    phone = State()
    confirm = State()

class RejectFSM(StatesGroup):
    reason = State()

async def get_lang(uid):
    u = await db.get_user(uid)
    return u[3] if u and u[3] else "am"

# ---------- /start (with Car Photo) ----------
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    u = await db.get_user(msg.from_user.id)
    lang = u[3] if u and u[3] else "am"
    
    # Save user
    await db.save_user(msg.from_user.id, msg.from_user.username or "",
                       msg.from_user.full_name, lang)

    # Get first active car image
    cars = await db.list_cars(active_only=True)
    image = None
    if cars:
        for c in cars:
            if len(c) > 8 and c[8]: # image column
                image = c[8]
                break

    if u and u[3]:
        # Returning user
        txt = t(lang, "menu", name=msg.from_user.full_name)
        kb = main_menu(lang)
    else:
        # New user → language picker
        txt = t("am", "welcome")
        kb = lang_kb()

    try:
        if image:
            await msg.answer_photo(image, caption=txt, reply_markup=kb)
        else:
            await msg.answer(txt, reply_markup=kb)
    except Exception as e:
        log.error(f"Start photo error: {e}")
        await msg.answer(txt, reply_markup=kb)

@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await db.save_user(cb.from_user.id, cb.from_user.username or "",
                       cb.from_user.full_name, lang)
    txt = t(lang, "menu", name=cb.from_user.full_name)
    kb = main_menu(lang)
    try:
        await cb.message.delete()
    except Exception:
        pass
    
    # Try to keep image if exists
    cars = await db.list_cars(active_only=True)
    image = None
    if cars:
        for c in cars:
            if len(c) > 8 and c[8]:
                image = c[8]
                break

    try:
        if image:
            await cb.message.answer_photo(image, caption=txt, reply_markup=kb)
        else:
            await cb.message.answer(txt, reply_markup=kb)
    except Exception:
        await cb.message.answer(txt, reply_markup=kb)
    await cb.answer()

# ---------- Main Menu ----------
@dp.callback_query(F.data == "menu:home")
async def menu_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    txt = t(lang, "menu", name=cb.from_user.full_name)
    try:
        await cb.message.edit_text(txt, reply_markup=main_menu(lang))
    except Exception:
        await cb.message.answer(txt, reply_markup=main_menu(lang))
    await cb.answer()

@dp.callback_query(F.data == "menu:how")
async def menu_how(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    try:
        await cb.message.edit_text(
            t(lang, "how_text"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t(lang, "home"),
                                     callback_data="menu:home")
            ]])
        )
    except Exception:
        await cb.message.answer(t(lang, "how_text"))
    await cb.answer()

@dp.callback_query(F.data == "menu:support")
async def menu_support(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    try:
        await cb.message.edit_text(
            t(lang, "support_text", ss=cfg.SUPPORT_USERNAME),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t(lang, "home"),
                                     callback_data="menu:home")
            ]])
        )
    except Exception:
        await cb.message.answer(t(lang, "support_text", ss=cfg.SUPPORT_USERNAME))
    await cb.answer()

@dp.callback_query(F.data == "menu:my")
async def menu_my(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    rows = await db.user_orders(cb.from_user.id)
    if not rows:
        txt = t(lang, "no_orders")
    else:
        icons = {"pending": "⏳", "approved": "✅", "rejected": "❌",
                 "held": "🔒", "blocked": "🚫"}
        lines = [t(lang, "orders")]
        for oid, tno, st, car in rows:
            lines.append(f"{icons.get(st,'•')} <b>#{tno}</b> · {car or '-'} — {st}")
        txt = "\n".join(lines)
    try:
        await cb.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text=t(lang, "home"),
                                     callback_data="menu:home")
            ]]))
    except Exception:
        await cb.message.answer(txt)
    await cb.answer()

@dp.callback_query(F.data == "menu:buy")
async def menu_buy(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    cars = await db.list_cars(active_only=True)
    if not cars:
        await cb.answer("📭 ምንም ንቁ መኪና የለም", show_alert=True)
        return
    try:
        await cb.message.edit_text(t(lang, "pick_car"),
                                   reply_markup=cars_kb(lang, cars))
    except Exception:
        await cb.message.answer(t(lang, "pick_car"),
                                reply_markup=cars_kb(lang, cars))
    await cb.answer()

# ---------- Car Detail ----------
@dp.callback_query(F.data.startswith("car:"))
async def show_car(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    car_id = int(cb.data.split(":")[1])
    car = await db.get_car(car_id)
    if not car:
        await cb.answer("❌ Car not found", show_alert=True); return
    stats = await db.car_stats(car_id)
    text = t(lang, "car_info",
             name=car[1], desc=car[2] or "-", price=car[3],
             closing=car[6] or "-", tmin=car[4], tmax=car[5],
             remaining=stats["remaining"], taken=stats["taken"])
    can_buy = stats["remaining"] > 0 and car[7]
    try:
        await cb.message.edit_text(text, reply_markup=car_kb(lang, car_id, can_buy))
    except Exception:
        await cb.message.answer(text, reply_markup=car_kb(lang, car_id, can_buy))
    await cb.answer()

# ---------- Buy: Ticket Selection ----------
@dp.callback_query(F.data.startswith("buy:"))
async def buy_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    car_id = int(cb.data.split(":")[1])
    car = await db.get_car(car_id)
    if not car or not car[7]:
        await cb.answer("❌ መኪና አይገኝም", show_alert=True); return
    await state.update_data(car_id=car_id, car_name=car[1],
                            tmin=car[4], tmax=car[5], price=car[3])
    try:
        await cb.message.edit_text(t(lang, "select_ticket"),
                                   reply_markup=ticket_action_kb(lang, car_id))
    except Exception:
        await cb.message.answer(t(lang, "select_ticket"),
                                reply_markup=ticket_action_kb(lang, car_id))
    await cb.answer()

# ---------- Random pick ----------
@dp.callback_query(F.data.startswith("tkt:rand:"))
async def pick_random(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    car_id = int(cb.data.split(":")[2])
    car = await db.get_car(car_id)
    if not car:
        await cb.answer("❌", show_alert=True); return
    taken = await db.taken_numbers(car_id)
    total = car[5] - car[4] + 1
    if len(taken) >= total:
        await cb.answer(t(lang, "no_available"), show_alert=True); return
    for _ in range(30):
        n = random.randint(car[4], car[5])
        if n not in taken:
            break
    else:
        avail = [x for x in range(car[4], car[5]+1) if x not in taken]
        if not avail:
            await cb.answer(t(lang, "no_available"), show_alert=True); return
        n = random.choice(avail)
    oid = await db.hold_ticket(car_id, cb.from_user.id, n, cfg.HOLD_MINUTES)
    if not oid:
        await cb.answer(t(lang, "taken_number", n=n), show_alert=True)
        return
    await state.update_data(oid=oid, ticket=n)
    txt = t(lang, "ticket_held", n=n, mins=cfg.HOLD_MINUTES)
    try:
        await cb.message.edit_text(txt)
    except Exception:
        await cb.message.answer(txt)
    await cb.message.answer(t(lang, "banks"), reply_markup=pay_kb(lang, oid))
    await cb.answer("🎲")

# ---------- Manual number ----------
@dp.callback_query(F.data.startswith("tkt:man:"))
async def manual_number(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    car_id = int(cb.data.split(":")[2])
    car = await db.get_car(car_id)
    if not car:
        await cb.answer("❌", show_alert=True); return
    await state.update_data(car_id=car_id, car_name=car[1],
                            tmin=car[4], tmax=car[5], price=car[3])
    await state.set_state(BuyFSM.manual_number)
    await cb.message.answer(t(lang, "ask_number", tmin=car[4], tmax=car[5]))
    await cb.answer()

@dp.message(BuyFSM.manual_number, F.text)
async def process_manual_number(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    d = await state.get_data()
    txt = msg.text.strip()
    if not txt.isdigit():
        await msg.answer(t(lang, "invalid_number", tmin=d["tmin"], tmax=d["tmax"]))
        return
    n = int(txt)
    if not (d["tmin"] <= n <= d["tmax"]):
        await msg.answer(t(lang, "invalid_number", tmin=d["tmin"], tmax=d["tmax"]))
        return
    if not await db.is_ticket_available(d["car_id"], n):
        await msg.answer(
            t(lang, "taken_number", n=n),
            reply_markup=ticket_action_kb(lang, d["car_id"]))
        await state.clear()
        return
    oid = await db.hold_ticket(d["car_id"], msg.from_user.id, n, cfg.HOLD_MINUTES)
    if not oid:
        await msg.answer(t(lang, "taken_number", n=n))
        await state.clear()
        return
    await state.update_data(oid=oid, ticket=n)
    await msg.answer(t(lang, "ticket_held", n=n, mins=cfg.HOLD_MINUTES))
    await msg.answer(t(lang, "banks"), reply_markup=pay_kb(lang, oid))

# ---------- Payment: screenshot ----------
@dp.callback_query(F.data.startswith("pay:paid:"))
async def pay_paid(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    oid = int(cb.data.split(":")[2])
    o = await db.get_order(oid)
    if not o or o[2] != cb.from_user.id or o[7] != "held":
        await cb.answer(t(lang, "session_expired"), show_alert=True); return
    await state.update_data(oid=oid)
    await state.set_state(BuyFSM.shot)
    await cb.message.answer(t(lang, "ask_shot"))
    await cb.answer()

@dp.callback_query(F.data.startswith("pay:cancel:"))
async def pay_cancel(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    oid = int(cb.data.split(":")[2])
    o = await db.get_order(oid)
    if not o or o[2] != cb.from_user.id or o[7] != "held":
        await cb.answer("Order not found or no longer held", show_alert=True); return
    await db.release_order(oid, user_id=cb.from_user.id)
    await state.clear()
    try:
        await cb.message.edit_text(t(lang, "canceled"),
                                   reply_markup=main_menu(lang))
    except Exception:
        await cb.message.answer(t(lang, "canceled"))
    await cb.answer()

@dp.message(BuyFSM.shot, F.photo)
async def f_shot(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await state.update_data(shot=msg.photo[-1].file_id)
    await state.set_state(BuyFSM.name)
    await msg.answer(t(lang, "ask_name"))

@dp.message(BuyFSM.shot)
async def f_shot_bad(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await msg.answer(t(lang, "bad_shot"))

@dp.message(BuyFSM.name, F.text)
async def f_name(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    name = msg.text.strip()
    if len(name) < 2:
        await msg.answer("❌ " + t(lang, "ask_name"))
        return
    await state.update_data(name=name)
    await state.set_state(BuyFSM.phone)
    await msg.answer(t(lang, "ask_phone"))

@dp.message(BuyFSM.phone, F.text)
async def f_phone(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    p = msg.text.strip().replace(" ", "").replace("-", "")
    if not re.match(r"^(\+2519|09|07)\d{8}$", p):
        await msg.answer(t(lang, "bad_phone")); return
    await state.update_data(phone=p)
    d = await state.get_data()
    await state.set_state(BuyFSM.confirm)
    txt = t(lang, "confirm", car=d["car_name"], ticket=d["ticket"],
            name=d["name"], phone=p)
    await msg.answer_photo(d["shot"], caption=txt,
                           reply_markup=confirm_kb(lang, d["oid"]))

# ---------- Confirm ----------
@dp.callback_query(F.data.startswith("cancel:"))
async def cancel_order(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    oid = int(cb.data.split(":")[1])
    o = await db.get_order(oid)
    if not o or o[2] != cb.from_user.id or o[7] != "held":
        await cb.answer("Order not found or no longer held", show_alert=True); return
    await db.release_order(oid, user_id=cb.from_user.id)
    await state.clear()
    try:
        await cb.message.edit_caption(caption=t(lang, "canceled"))
    except Exception:
        await cb.message.answer(t(lang, "canceled"))
    await cb.message.answer(t(lang, "menu", name=cb.from_user.full_name),
                            reply_markup=main_menu(lang))
    await cb.answer()

@dp.callback_query(F.data.startswith("ok:"))
async def confirm_order(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    oid = int(cb.data.split(":")[1])
    d = await state.get_data()
    o = await db.get_order(oid)
    if not o or o[2] != cb.from_user.id or o[7] != "held" or d.get("oid") != oid or not d.get("shot"):
        await cb.answer(t(lang, "session_expired"), show_alert=True); return
    changed = await db.confirm_hold(oid, d.get("name", ""), d.get("phone", ""), d.get("shot"), user_id=cb.from_user.id)
    if not changed:
        await cb.answer(t(lang, "session_expired"), show_alert=True); return
    await state.clear()
    try:
        await cb.message.edit_caption(caption=t(lang, "sent"))
    except Exception:
        await cb.message.answer(t(lang, "sent"))
    await cb.message.answer(t(lang, "menu", name=cb.from_user.full_name),
                            reply_markup=main_menu(lang))
    admin_text = (
        f"🔔 <b>አዲስ ጥያቄ #{oid}</b>\n\n"
        f"🚗 {html.escape(str(d['car_name']), quote=True)}\n"
        f"👤 {html.escape(str(d['name']), quote=True)}\n"
        f"📱 {html.escape(str(d['phone']), quote=True)}\n"
        f"🎟️ ዕጣ: <b>#{d['ticket']}</b>\n"
        f"💬 @{cb.from_user.username or '-'} — <code>{cb.from_user.id}</code>"
    )
    try:
        await bot.send_photo(cfg.ADMIN_GROUP_ID, photo=d["shot"],
                             caption=admin_text, reply_markup=admin_kb(oid))
    except Exception as e:
        log.error(f"Admin send failed: {e}")
    await cb.answer()

# ---------- Telegram Admin ----------
@dp.callback_query(F.data.startswith("adm:ok:"))
async def adm_ok(cb: CallbackQuery):
    if cb.from_user.id not in cfg.ADMIN_IDS:
        await cb.answer("❌ ፈቃድ የለዎትም", show_alert=True); return
    oid = int(cb.data.split(":")[2])
    o = await db.get_order(oid)
    if not o: await cb.answer("Not found"); return
    changed = await db.update_order_status(oid, "approved", expected_status="pending", actor=f"telegram:{cb.from_user.id}")
    if not changed:
        await cb.answer("Already processed", show_alert=True); return
    car = await db.get_car(o[1])
    try:
        await bot.send_message(o[2], t("am", "approved",
                             car=car[1] if car else "-", ticket=o[3]))
    except Exception as e:
        log.error(e)
    try:
        await cb.message.edit_caption(
            caption=(cb.message.caption or "") + "\n\n✅ <b>ጸድቋል</b>",
            reply_markup=None)
    except Exception: pass
    await cb.answer("✅ Approved")

@dp.callback_query(F.data.startswith("adm:no:"))
async def adm_no(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in cfg.ADMIN_IDS:
        await cb.answer("❌ ፈቃድ የለዎትም", show_alert=True); return
    oid = int(cb.data.split(":")[2])
    await state.update_data(rej_oid=oid)
    await state.set_state(RejectFSM.reason)
    await cb.message.reply("📝 የመመለሻ ምክንያት ይጻፉ / Sababa deebii barreessi:")
    await cb.answer()

@dp.message(RejectFSM.reason, F.text)
async def adm_rej_reason(msg: Message, state: FSMContext):
    d = await state.get_data()
    oid = d.get("rej_oid"); await state.clear()
    o = await db.get_order(oid)
    if not o or o[7] != "pending": await msg.answer("Order not found or already processed"); return
    changed = await db.update_order_status(oid, "rejected", msg.text.strip(), expected_status="pending", actor=f"telegram:{msg.from_user.id}")
    if not changed: await msg.answer("Order already processed"); return
    try:
        await bot.send_message(o[2], t("am", "rejected", reason=msg.text.strip()))
    except Exception as e: log.error(e)
    await msg.answer(f"❌ Order #{oid} ተመልሷል።")

# ============================================================
#  AUTO REMINDER (Feature 8)
# ============================================================
async def reminder_task():
    """በየ30 ሰከንዱ የሚያልቁ ቲኬቶችን ያሳውቃል"""
    while True:
        try:
            await asyncio.sleep(30)
            expiring = await db.get_expiring_holds()
            for oid, uid, ticket_no, _ in expiring:
                lang = await get_lang(uid)
                try:
                    await bot.send_message(
                        uid,
                        t(lang, "reminder", ticket=ticket_no)
                    )
                    await db.mark_reminder_sent(oid)
                except Exception as e:
                    log.error(f"Reminder failed for {uid}: {e}")
                    await db.mark_reminder_sent(oid)
        except Exception as e:
            log.error(f"Reminder task error: {e}")

# ============================================================
#  ADMIN WEB PANEL
# ============================================================
def make_token():
    ts = str(int(time.time()))
    sig = hmac.new(cfg.SECRET_KEY.encode(), ts.encode(),
                   hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"

def verify_token(tok):
    try:
        ts, sig = tok.split(".")
        exp = hmac.new(cfg.SECRET_KEY.encode(), ts.encode(),
                       hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, exp): return False
        age = time.time() - int(ts)
        if age < -30 or age > cfg.SESSION_TTL_SECONDS: return False
        return True
    except Exception:
        return False

def authed(req):
    return verify_token(req.cookies.get("auth", ""))

def auth_mw():
    @web.middleware
    async def mw(req, handler):
        if req.path.startswith("/admin") and req.path not in ("/admin/login",):
            if not authed(req):
                raise web.HTTPFound("/admin/login")
        return await handler(req)
    return mw

CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:#0a0e14;color:#e7e9ea;line-height:1.5;padding-bottom:75px;font-size:15px}
a{color:#1d9bf0;text-decoration:none}
.nav{background:#11161d;border-bottom:1px solid #232a33;padding:14px 16px;
display:flex;justify-content:space-between;align-items:center;
position:sticky;top:0;z-index:100;backdrop-filter:blur(20px)}
.nav h1{font-size:16px;color:#1d9bf0;font-weight:700}
.nav .badge-live{background:#003d24;color:#00ba7c;padding:3px 10px;
border-radius:10px;font-size:10px;font-weight:700}
.wrap{max-width:1200px;margin:16px auto;padding:0 12px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px}
@media(min-width:500px){.grid{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}}
.stat{background:#11161d;border:1px solid #232a33;border-radius:14px;padding:16px;
position:relative;overflow:hidden}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;
background:linear-gradient(90deg,#1d9bf0,#00ba7c)}
.stat .lbl{font-size:10px;color:#71767b;text-transform:uppercase;
letter-spacing:.8px;font-weight:700}
.stat .val{font-size:26px;font-weight:800;margin-top:6px;color:#e7e9ea}
.stat.blue .val{color:#1d9bf0}
.stat.green .val{color:#00ba7c}
.stat.yellow .val{color:#ffd400}
.stat.red .val{color:#f4212e}
.card{background:#11161d;border:1px solid #232a33;border-radius:14px;
padding:18px;margin-bottom:14px}
.card h2{font-size:15px;margin-bottom:14px;color:#e7e9ea;font-weight:700;
display:flex;align-items:center;gap:8px}
table{width:100%;border-collapse:collapse}
th,td{padding:12px 8px;text-align:left;font-size:13px;
border-bottom:1px solid #232a33}
th{color:#71767b;font-weight:700;font-size:10px;text-transform:uppercase;
letter-spacing:.5px}
tr:last-child td{border-bottom:none}
.btn{display:inline-block;padding:12px 20px;border-radius:26px;border:none;
font-size:14px;font-weight:700;cursor:pointer;background:#1d9bf0;color:#fff;
text-align:center;line-height:1.2;touch-action:manipulation;
transition:transform .1s}
.btn:active{transform:scale(.97)}
.btn.r{background:#f4212e}.btn.g{background:#00ba7c}
.btn.y{background:#ffd400;color:#000}
.btn.s{padding:8px 14px;font-size:13px}
.btn.full{display:block;width:100%}
input,textarea,select{width:100%;padding:13px;border-radius:11px;
background:#0a0e14;border:1px solid #232a33;color:#e7e9ea;font-size:15px;
font-family:inherit;margin-bottom:12px;-webkit-appearance:none}
input:focus,textarea:focus,select:focus{outline:none;border-color:#1d9bf0}
label{display:block;font-size:11px;color:#71767b;margin-bottom:6px;
font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.badge{padding:5px 11px;border-radius:14px;font-size:10px;font-weight:700;
display:inline-block;text-transform:uppercase;letter-spacing:.5px}
.badge.pending{background:#5c4a00;color:#ffd400}
.badge.approved{background:#003d24;color:#00ba7c}
.badge.rejected{background:#3d0008;color:#f4212e}
.badge.held{background:#1a3a5c;color:#1d9bf0}
.badge.blocked{background:#2f3336;color:#a0a0a0}
.login{max-width:400px;margin:60px auto;background:#11161d;padding:32px;
border-radius:20px;border:1px solid #232a33;box-shadow:0 20px 60px rgba(0,0,0,.5)}
.login h1{text-align:center;margin-bottom:24px;color:#1d9bf0;font-size:22px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.form-grid .full{grid-column:1/-1}
@media(max-width:500px){.form-grid{grid-template-columns:1fr}}
.bottom-nav{position:fixed;bottom:0;left:0;right:0;background:#11161d;
border-top:1px solid #232a33;display:flex;justify-content:space-around;
padding:8px 0;z-index:100;backdrop-filter:blur(20px);
padding-bottom:max(8px,env(safe-area-inset-bottom))}
.bottom-nav a{flex:1;text-align:center;padding:6px;color:#71767b;
font-size:10px;font-weight:700;display:flex;flex-direction:column;
align-items:center;gap:3px;text-transform:uppercase;letter-spacing:.5px}
.bottom-nav a.active{color:#1d9bf0}
.bottom-nav a .ic{font-size:22px;line-height:1}
.order-card{background:#0f1419;border:1px solid #232a33;border-radius:12px;
padding:14px;margin-bottom:12px}
.order-card .row{display:flex;justify-content:space-between;
align-items:center;margin-bottom:8px;font-size:13px;gap:10px}
.order-card .row .k{color:#71767b;font-size:10px;text-transform:uppercase;
font-weight:700;letter-spacing:.5px;white-space:nowrap}
.order-card .actions{display:flex;gap:8px;margin-top:12px}
.order-card .actions .btn{flex:1;padding:12px}
.empty{text-align:center;color:#71767b;padding:50px 20px;font-size:14px}
.empty .big{font-size:48px;margin-bottom:12px;opacity:.5}
</style>
"""

def layout(title, body, active=""):
    def link(href, text, key):
        cls = 'class="active"' if key == active else ""
        return f'<a href="{href}" {cls}>{text}</a>'
    return f"""<!doctype html><html lang="am"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#11161d">
<title>{title}</title>{CSS}</head><body>
<div class="nav">
  <h1>🚗 Car Equb Admin</h1>
  <span class="badge-live">● LIVE</span>
</div>
<div class="wrap">{body}</div>
<div class="bottom-nav">
  {link('/admin','<span class="ic">📊</span>Dash','dash')}
  {link('/admin/cars','<span class="ic">🚗</span>Cars','cars')}
  {link('/admin/orders','<span class="ic">📋</span>Orders','orders')}
  {link('/admin/holds','<span class="ic">🔒</span>Holds','holds')}
  {link('/admin/broadcast','<span class="ic">📢</span>Send','broadcast')}
  {link('/admin/audit','<span class="ic">🧾</span>Audit','audit')}
  {link('/admin/logout','<span class="ic">🚪</span>Out','')}
</div>
</body></html>"""

# ---------- Auth ----------
_LOGIN_FAILURES = {}

def _login_locked(ip):
    count, since = _LOGIN_FAILURES.get(ip, (0, 0))
    if time.time() - since >= cfg.LOGIN_LOCK_SECONDS:
        _LOGIN_FAILURES.pop(ip, None)
        return False
    return count >= cfg.LOGIN_MAX_ATTEMPTS

async def login_get(req):
    err = req.query.get("err", "")
    msg = ('<p style="color:#f4212e;text-align:center;margin-bottom:14px;'
           'font-weight:600">❌ የተሳሳተ የይለፍ ቃል</p>') if err else ""
    return web.Response(text=f"""<!doctype html><html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login</title>{CSS}</head><body>
<div class="login"><h1>🚗 Admin Login</h1>{msg}
<form method="POST" action="/admin/login">
<label>Password</label>
<input type="password" name="pw" required autofocus>
<button class="btn full">🔓 Login</button>
</form></div></body></html>""", content_type="text/html")

async def login_post(req):
    ip = req.remote or "unknown"
    if _login_locked(ip):
        raise web.HTTPFound("/admin/login?err=locked")
    data = await req.post()
    supplied = str(data.get("pw", ""))
    if hmac.compare_digest(supplied, cfg.ADMIN_PASSWORD):
        _LOGIN_FAILURES.pop(ip, None)
        r = web.HTTPFound("/admin")
        r.set_cookie("auth", make_token(), max_age=cfg.SESSION_TTL_SECONDS,
                     httponly=True, secure=cfg.COOKIE_SECURE, samesite="Lax", path="/")
        raise r
    count, since = _LOGIN_FAILURES.get(ip, (0, time.time()))
    _LOGIN_FAILURES[ip] = (count + 1, since)
    raise web.HTTPFound("/admin/login?err=1")

async def logout(req):
    r = web.HTTPFound("/admin/login")
    r.del_cookie("auth", path="/")
    raise r

# ---------- Dashboard ----------
async def dash(req):
    g = await db.global_stats()
    cars = await db.list_cars(active_only=False)
    car_rows = ""
    for c in cars:
        s = await db.car_stats(c[0])
        car_rows += f"""<tr>
        <td>#{c[0]}</td><td>{html.escape(str(c[1]), quote=True)}</td>
        <td>{s['approved']}✅ {s['pending']}⏳ {s['held']}🔒 {s['blocked']}🚫</td>
        <td><b style="color:#00ba7c">{s['remaining']}</b></td></tr>"""
    body = f"""
    <div class="grid">
      <div class="stat blue"><div class="lbl">Users</div>
      <div class="val">{g['users']}</div></div>
      <div class="stat green"><div class="lbl">Active</div>
      <div class="val">{g['cars']}</div></div>
      <div class="stat yellow"><div class="lbl">Pending</div>
      <div class="val">{g['pending']}</div></div>
      <div class="stat blue"><div class="lbl">Approved</div>
      <div class="val">{g['approved']}</div></div>
      <div class="stat blue"><div class="lbl">Held</div>
      <div class="val">{g['held']}</div></div>
      <div class="stat red"><div class="lbl">Blocked</div>
      <div class="val">{g['blocked']}</div></div>
      <div class="stat green"><div class="lbl">Approved value (Birr)</div>
      <div class="val">{g.get('approved_revenue', 0):,}</div></div>
    </div>
    <div class="card"><h2>🚗 Cars Overview</h2>
    <table><thead><tr><th>ID</th><th>Name</th>
    <th>Status</th><th>Left</th></tr></thead>
    <tbody>{car_rows or '<tr><td colspan="4" style="text-align:center;color:#71767b;padding:20px">No cars</td></tr>'}</tbody></table></div>
    <div class="card">
      <a href="/admin/orders?status=pending" class="btn full y"
      style="margin-bottom:8px">⏳ View Pending</a>
      <a href="/admin/broadcast" class="btn full">📢 Send Broadcast</a>
    </div>"""
    return web.Response(text=layout("Dashboard", body, "dash"),
                        content_type="text/html")

# ---------- Cars ----------
async def cars_list(req):
    cars = await db.list_cars(active_only=False)
    cards = ""
    for c in cars:
        s = await db.car_stats(c[0])
        img = c[8] if len(c) > 8 and c[8] else ""
        img_html = f'<img src="{html.escape(str(img), quote=True)}" style="width:60px;height:60px;border-radius:8px;object-fit:cover">' if img else '🚗'
        cards += f"""<div class="order-card">
          <div class="row">
            <span>{img_html} <b>#{c[0]}</b> {html.escape(str(c[1]), quote=True)}</span>
            <span>{'🟢' if c[7] else '🔴'}</span>
          </div>
          <div class="row"><span class="k">Price</span>
          <span><b>{c[3]} ብር</b></span></div>
          <div class="row"><span class="k">Tickets</span>
          <span>{c[4]} – {c[5]}</span></div>
          <div class="row"><span class="k">Status</span>
          <span>✅{s['approved']} ⏳{s['pending']} 🔒{s['held']} 🚫{s['blocked']}</span></div>
          <div class="row"><span class="k">Remaining</span>
          <span><b style="color:#00ba7c">{s['remaining']}/{s['total']}</b></span></div>
          <div class="actions">
            <a href="/admin/cars/{c[0]}" class="btn full s">✏️ Edit</a>
            <form method="POST" action="/admin/cars/{c[0]}/del" style="flex:1"
             onsubmit="return confirm('Delete car #{c[0]}?')">
              <button class="btn r full s">🗑️</button>
            </form>
          </div>
        </div>"""
    body = f"""
    <div class="card">
      <h2>➕ አዲስ መኪና</h2>
      <form method="POST" action="/admin/cars/add">
        <label>የመኪና ስም</label>
        <input name="name" required placeholder="Toyota Corolla 2020">
        <label>ዋጋ (ብር)</label>
        <input name="price" type="number" value="500" required>
        <div class="form-grid">
          <div><label>ዕጣ ከ</label>
          <input name="tmin" type="number" value="1"></div>
          <div><label>ዕጣ እስከ</label>
          <input name="tmax" type="number" value="4000"></div>
        </div>
        <label>የመዝጊያ ቀን</label>
        <input name="closing" placeholder="30/12/2026">
        <label>ፎቶ URL (አማራጭ)</label>
        <input name="image" placeholder="https://example.com/car.jpg">
        <label>መግለጫ</label>
        <textarea name="desc" rows="2"></textarea>
        <button class="btn full">➕ Add Car</button>
      </form>
    </div>
    <h2 style="margin:16px 0 12px;font-size:13px;color:#71767b;
      text-transform:uppercase;letter-spacing:.5px">
      🚗 Cars ({len(cars)})</h2>
    <div>{cards or '<div class="empty"><div class="big">🚗</div>No cars</div>'}</div>"""
    return web.Response(text=layout("Cars", body, "cars"),
                        content_type="text/html")

async def car_add(req):
    d = await req.post()
    await db.add_car(
        d.get("name", "").strip(), d.get("desc", "").strip(),
        int(d.get("price", 500) or 500),
        int(d.get("tmin", 1) or 1),
        int(d.get("tmax", 4000) or 4000),
        d.get("closing", "").strip(),
        d.get("image", "").strip())
    raise web.HTTPFound("/admin/cars")

async def car_edit_get(req):
    cid = int(req.match_info["id"])
    c = await db.get_car(cid)
    if not c: raise web.HTTPFound("/admin/cars")
    s = await db.car_stats(cid)
    img = c[8] if len(c) > 8 and c[8] else ""
    body = f"""
    <div class="card"><h2>✏️ Edit Car #{cid}</h2>
    <form method="POST" action="/admin/cars/{cid}">
      <label>የመኪና ስም</label>
      <input name="name" value="{html.escape(str(c[1]), quote=True)}" required>
      <label>ዋጋ (ብር)</label>
      <input name="price" type="number" value="{c[3]}">
      <div class="form-grid">
        <div><label>ዕጣ ከ</label>
        <input name="tmin" type="number" value="{c[4]}"></div>
        <div><label>ዕጣ እስከ</label>
        <input name="tmax" type="number" value="{c[5]}"></div>
      </div>
      <label>የመዝጊያ ቀን</label>
      <input name="closing" value="{html.escape(str(c[6] or ''), quote=True)}">
      <label>ፎቶ URL</label>
      <input name="image" value="{html.escape(str(img), quote=True)}" placeholder="https://example.com/car.jpg">
      <label>ሁኔታ</label>
      <select name="active">
        <option value="1" {'selected' if c[7] else ''}>🟢 ንቁ</option>
        <option value="0" {'' if c[7] else 'selected'}>🔴 ተዘግቷል</option>
      </select>
      <label>መግለጫ</label>
      <textarea name="desc" rows="2">{html.escape(str(c[2] or ''))}</textarea>
      <button class="btn full">💾 Save</button>
      <a href="/admin/cars" class="btn full"
      style="background:#232a33;margin-top:8px;display:block;text-align:center">
      Cancel</a>
    </form></div>
    <div class="card">
      <h2>📊 Statistics</h2>
      <div class="order-card">
        <div class="row"><span class="k">Total</span>
        <span><b>{s['total']}</b></span></div>
        <div class="row"><span class="k">Approved</span>
        <span>✅ {s['approved']}</span></div>
        <div class="row"><span class="k">Pending</span>
        <span>⏳ {s['pending']}</span></div>
        <div class="row"><span class="k">Held</span>
        <span>🔒 {s['held']}</span></div>
        <div class="row"><span class="k">Blocked</span>
        <span>🚫 {s['blocked']}</span></div>
        <div class="row"><span class="k">Remaining</span>
        <span><b style="color:#00ba7c">{s['remaining']}</b></span></div>
      </div>
    </div>"""
    return web.Response(text=layout("Edit Car", body, "cars"),
                        content_type="text/html")

async def car_edit_post(req):
    cid = int(req.match_info["id"])
    d = await req.post()
    await db.update_car(
        cid, d.get("name", "").strip(), d.get("desc", "").strip(),
        int(d.get("price", 500) or 500),
        int(d.get("tmin", 1) or 1),
        int(d.get("tmax", 4000) or 4000),
        d.get("closing", "").strip(),
        int(d.get("active", 1)),
        d.get("image", "").strip())
    raise web.HTTPFound("/admin/cars")

async def car_del(req):
    cid = int(req.match_info["id"])
    await db.delete_car(cid)
    raise web.HTTPFound("/admin/cars")

# ---------- Orders ----------
async def orders_list(req):
    car_id = req.query.get("car_id", "")
    status = req.query.get("status", "")
    car_filter = int(car_id) if car_id.isdigit() else None
    valid = ("pending","approved","rejected","held","blocked")
    status_filter = status if status in valid else None

    cars = await db.list_cars(active_only=False)
    car_opts = '<option value="">ሁሉም</option>'
    for c in cars:
        sel = "selected" if car_filter == c[0] else ""
        car_opts += f'<option value="{c[0]}" {sel}>#{c[0]} {html.escape(str(c[1]), quote=True)}</option>'
    st_opts = '<option value="">ሁሉም</option>'
    for s in valid:
        sel = "selected" if status_filter == s else ""
        st_opts += f'<option value="{s}" {sel}>{s.title()}</option>'

    orders = await db.list_orders(car_id=car_filter,
                                  status=status_filter, limit=300)
    cards = ""
    for o in orders:
        oid, cid, uid, tno, name, phone, shot, st, reason, created, carname = o
        actions = ""
        if st == "pending":
            actions = f"""
            <form method="POST" action="/admin/orders/{oid}/ok" style="flex:1">
              <button class="btn g full s">✅ Approve</button></form>
            <form method="POST" action="/admin/orders/{oid}/no" style="flex:1"
             onsubmit="var r=prompt('ምክንያት:','');this.reason.value=r||'';
             return r!==null">
              <input type="hidden" name="reason">
              <button class="btn r full s">❌ Reject</button></form>
            """
        elif st in ("held","blocked"):
            actions = f"""
            <form method="POST" action="/admin/orders/{oid}/release" style="flex:1"
             onsubmit="return confirm('Release this ticket?')">
              <button class="btn y full s">🔓 Release</button></form>
            """
        reason_html = ""
        if reason:
            reason_html = (f'<div class="row"><span class="k">Reason</span>'
                           f'<span style="color:#71767b">{html.escape(str(reason), quote=True)}</span></div>')
        user_line = html.escape(str(name), quote=True) if name else "—"
        if uid:
            user_line = f'<a href="tg://user?id={uid}">{name or "user"}</a>'
        cards += f"""<div class="order-card">
          <div class="row">
            <span><b>#{oid}</b> · {html.escape(str(carname or '-'), quote=True)}</span>
            <span class="badge {st}">{st}</span>
          </div>
          <div class="row"><span class="k">Ticket</span>
          <span><b style="color:#1d9bf0;font-size:16px">🎟️ {tno}</b></span></div>
          <div class="row"><span class="k">User</span>
          <span>{user_line}</span></div>
          <div class="row"><span class="k">Phone</span>
          {f'<a href="tel:{html.escape(str(phone), quote=True)}">{html.escape(str(phone), quote=True)}</a>' if phone else '—'}</div>
          {reason_html}
          <div class="row"><span class="k">Date</span>
          <span style="font-size:11px;color:#71767b">{created[:16]}</span></div>
          <div class="actions">{actions}</div>
        </div>"""

    body = f"""
    <div class="card">
      <h2>🔍 Filter</h2>
      <form method="GET">
        <label>መኪና</label><select name="car_id">{car_opts}</select>
        <label>ሁኔታ</label><select name="status">{st_opts}</select>
        <button class="btn full">Apply</button>
      </form>
    </div>
    <h2 style="margin:16px 0 12px;font-size:13px;color:#71767b;
      text-transform:uppercase;letter-spacing:.5px">
      📋 Orders ({len(orders)})</h2>
    <div>{cards or '<div class="empty"><div class="big">📭</div>No orders</div>'}</div>"""
    return web.Response(text=layout("Orders", body, "orders"),
                        content_type="text/html")

async def order_ok(req):
    oid = int(req.match_info["id"])
    o = await db.get_order(oid)
    if o and o[7] == "pending":
        changed = await db.update_order_status(oid, "approved", expected_status="pending", actor="web_admin")
        if changed:
            car = await db.get_car(o[1])
            try:
                await bot.send_message(o[2], t("am", "approved",
                    car=car[1] if car else "-", ticket=o[3]))
            except Exception as e: log.error(e)
    raise web.HTTPFound(req.headers.get("Referer", "/admin/orders"))

async def order_no(req):
    oid = int(req.match_info["id"])
    d = await req.post()
    reason = (d.get("reason") or "").strip() or "ያልተገለጸ"
    o = await db.get_order(oid)
    if o and o[7] == "pending":
        changed = await db.update_order_status(oid, "rejected", reason, expected_status="pending", actor="web_admin")
        if changed:
            try:
                await bot.send_message(o[2], t("am", "rejected", reason=reason))
            except Exception as e: log.error(e)
    raise web.HTTPFound(req.headers.get("Referer", "/admin/orders"))

async def order_release(req):
    oid = int(req.match_info["id"])
    await db.release_order(oid)
    raise web.HTTPFound(req.headers.get("Referer", "/admin/orders"))

# ---------- Holds ----------
async def holds_page(req):
    cars = await db.list_cars(active_only=False)
    car_opts = '<option value="">መኪና ይምረጡ</option>'
    for c in cars:
        car_opts += f'<option value="{c[0]}">#{c[0]} {html.escape(str(c[1]), quote=True)} ({c[4]}–{c[5]})</option>'

    orders = await db.list_orders(status="held", limit=100)
    blocked = await db.list_orders(status="blocked", limit=100)
    items = ""
    for o in orders + blocked:
        oid, cid, uid, tno, name, phone, shot, st, reason, created, carname = o
        items += f"""<div class="order-card">
          <div class="row">
            <span><b>🎟️ {tno}</b> · {carname or '-'}</span>
            <span class="badge {st}">{st}</span>
          </div>
          <div class="row"><span class="k">User</span>
          <span>{name or ('ID: '+str(uid) if uid else '—')}</span></div>
          <div class="actions">
            <form method="POST" action="/admin/orders/{oid}/release" style="flex:1"
             onsubmit="return confirm('Release #{tno}?')">
              <button class="btn y full s">🔓 Release</button></form>
          </div>
        </div>"""

    body = f"""
    <div class="card">
      <h2>🚫 Block Numbers</h2>
      <form method="POST" action="/admin/holds/block">
        <label>መኪና</label>
        <select name="car_id" required>{car_opts}</select>
        <div class="form-grid">
          <div><label>ከ ቁጥር</label>
          <input name="n_from" type="number" required min="1"></div>
          <div><label>እስከ ቁጥር</label>
          <input name="n_to" type="number" required min="1"></div>
        </div>
        <label>ምክንያት</label>
        <input name="reason" placeholder="ለምሳሌ: የአድሚን መያዣ">
        <button class="btn full r">🚫 Block</button>
      </form>
    </div>
    <h2 style="margin:16px 0 12px;font-size:13px;color:#71767b;
      text-transform:uppercase;letter-spacing:.5px">
      🔒 Held / 🚫 Blocked ({len(orders) + len(blocked)})</h2>
    <div>{items or '<div class="empty"><div class="big">🔓</div>No held/blocked</div>'}</div>"""
    return web.Response(text=layout("Holds", body, "holds"),
                        content_type="text/html")

async def hold_block(req):
    d = await req.post()
    try:
        car_id = int(d.get("car_id"))
        n_from = int(d.get("n_from"))
        n_to = int(d.get("n_to"))
        reason = d.get("reason", "").strip()
        if n_from > n_to:
            n_from, n_to = n_to, n_from
        if n_to - n_from > 500:
            raise ValueError("Range too large (max 500)")
        await db.block_range(car_id, n_from, n_to, reason)
    except Exception as e:
        log.error(f"Block failed: {e}")
    raise web.HTTPFound("/admin/holds")

# ---------- Broadcast (Feature 4) ----------
async def broadcast_page(req):
    cars = await db.list_cars(active_only=False)
    car_opts = '<option value="all">👥 ሁሉም ተጠቃሚዎች (All Users)</option>'
    for c in cars:
        car_opts += f'<option value="{c[0]}">🚗 #{c[0]} {html.escape(str(c[1]), quote=True)} የገዙ</option>'
    body = f"""
    <div class="card">
      <h2>📢 መልእክት ላክ (Broadcast)</h2>
      <form method="POST" action="/admin/broadcast/send">
        <label>ለማን ይላክ?</label>
        <select name="target">{car_opts}</select>
        <label>መልእክት</label>
        <textarea name="message" rows="6" required
        placeholder="የመልእክት ጽሑፍ... ለምሳሌ: ⚠️ ነገ የመጨረሻ ቀን ነው!"></textarea>
        <button class="btn full">📤 መልእክት ላክ</button>
      </form>
    </div>
    <div class="card">
      <p style="color:#71767b;font-size:13px;line-height:1.6">
        ⚠️ <b>ማሳሰቢያ:</b><br>
        • መልእክቱ በቀጥታ ለተጠቃሚዎች ይላካል<br>
        • ብዙ ተጠቃሚዎች ካሉ (500+) ሊወስድ ይችላል<br>
        • HTML tags ይደገፋሉ (&lt;b&gt;, &lt;i&gt;, &lt;code&gt;)
      </p>
    </div>"""
    return web.Response(text=layout("Broadcast", body, "broadcast"),
                        content_type="text/html")

async def broadcast_send(req):
    d = await req.post()
    target = d.get("target", "all")
    message = d.get("message", "").strip()

    if not message:
        raise web.HTTPFound("/admin/broadcast")

    if target == "all":
        user_ids = await db.get_all_user_ids()
    else:
        user_ids = await db.get_users_by_car(int(target))

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, message)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            log.error(f"Broadcast failed for {uid}: {e}")
            failed += 1

    body = f"""
    <div class="card">
      <h2>✅ Broadcast አልቋል</h2>
      <div class="grid">
        <div class="stat green"><div class="lbl">Sent</div>
        <div class="val">{sent}</div></div>
        <div class="stat red"><div class="lbl">Failed</div>
        <div class="val">{failed}</div></div>
      </div>
      <a href="/admin/broadcast" class="btn full"
      style="margin-top:16px">🔙 Back to Broadcast</a>
    </div>"""
    return web.Response(text=layout("Broadcast Result", body, "broadcast"),
                        content_type="text/html")

async def audit_page(req):
    rows = await db.list_audit_logs(250)
    cards = ""
    for row in rows:
        lid, actor, action, entity_type, entity_id, details, created = row
        cards += f"""<div class="order-card">
          <div class="row"><b>#{lid} · {html.escape(str(action), quote=True)}</b>
          <span style="font-size:11px;color:#71767b">{html.escape(str(created), quote=True)}</span></div>
          <div class="row"><span class="k">Actor</span><span>{html.escape(str(actor), quote=True)}</span></div>
          <div class="row"><span class="k">Entity</span><span>{html.escape(str(entity_type or '-'), quote=True)} #{entity_id or '-'}</span></div>
          <div class="row"><span class="k">Details</span><span>{html.escape(str(details or '-'), quote=True)}</span></div>
        </div>"""
    return web.Response(text=layout("Audit Log", cards or '<div class="empty">No audit events yet</div>', "audit"), content_type="text/html")

# ============================================================
#  APP SETUP
# ============================================================
def build_web():
    app = web.Application(middlewares=[auth_mw()])
    app["bot"] = bot
    app.router.add_get("/", lambda r: web.HTTPFound("/admin"))
    app.router.add_get("/health", lambda r: web.json_response({"ok": True}))
    app.router.add_get("/admin/login", login_get)
    app.router.add_post("/admin/login", login_post)
    app.router.add_get("/admin/logout", logout)
    app.router.add_get("/admin", dash)
    app.router.add_get("/admin/", dash)
    app.router.add_get("/admin/cars", cars_list)
    app.router.add_post("/admin/cars/add", car_add)
    app.router.add_get("/admin/cars/{id}", car_edit_get)
    app.router.add_post("/admin/cars/{id}", car_edit_post)
    app.router.add_post("/admin/cars/{id}/del", car_del)
    app.router.add_get("/admin/orders", orders_list)
    app.router.add_post("/admin/orders/{id}/ok", order_ok)
    app.router.add_post("/admin/orders/{id}/no", order_no)
    app.router.add_post("/admin/orders/{id}/release", order_release)
    app.router.add_get("/admin/holds", holds_page)
    app.router.add_post("/admin/holds/block", hold_block)
    app.router.add_get("/admin/broadcast", broadcast_page)
    app.router.add_post("/admin/broadcast/send", broadcast_send)
    app.router.add_get("/admin/audit", audit_page)
    return app

async def on_startup(app):
    await db.init_db()
    # Start reminder task
    asyncio.create_task(reminder_task())
    log.info("🔔 Reminder task started")
    
    if cfg.USE_WEBHOOK:
        url = f"{cfg.WEBHOOK_URL}{cfg.WEBHOOK_PATH}"
        await bot.set_webhook(url, secret_token=cfg.WEBHOOK_SECRET,
                              drop_pending_updates=True)
        log.info(f"✅ Webhook set: {url}")

async def on_shutdown(app):
    if cfg.USE_WEBHOOK:
        try: await bot.delete_webhook()
        except Exception: pass

def main():
    cfg.validate_settings()
    db.DB_PATH = cfg.DATABASE_PATH
    app = build_web()
    if cfg.USE_WEBHOOK:
        SimpleRequestHandler(dispatcher=dp, bot=bot,
                             secret_token=cfg.WEBHOOK_SECRET
                             ).register(app, path=cfg.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        app.on_startup.append(on_startup)
        app.on_cleanup.append(on_shutdown)
        log.info(f"🚀 Listening on {cfg.HOST}:{cfg.PORT}")
        web.run_app(app, host=cfg.HOST, port=cfg.PORT, print=None)
    else:
        async def run_poll():
            await db.init_db()
            asyncio.create_task(reminder_task())
            log.info("🤖 Polling mode")
            await dp.start_polling(bot)
        asyncio.run(run_poll())

if __name__ == "__main__":
    main()
