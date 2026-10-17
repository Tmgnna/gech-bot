# ============================================================
#  CAR EQUB BOT + ADMIN PANEL  — Professional Edition v5
#  Features: Saved Profile, Quick Buy, Auto-Submit, Simplified UI, Polling Fix
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
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
            "🚗 <b>የዛሬው የዕጣ መኪና</b>\n\n"
            "እንኳን ደህና መጡ፣ <b>{name}</b>! 👋\n\n"
            "🏆 <b>የሚያሸንፉት መኪና</b>\n"
            "🚘 <b>{car_name}</b>\n"
            "📝 {description}\n\n"
            "💵 የአንድ ዕጣ ዋጋ፦ <b>{price} ብር</b>\n"
            "🎟️ የቀሩ ዕጣዎች፦ <b>{remaining}</b>\n\n"
            "👤 የእቁቡ ባለቤት፦ <b>ጌትነት ፍቃዱ ጂራታ</b>\n\n"
            "👇 ለመሳተፍ <b>«ዕጣ ግዛ»</b> የሚለውን ይጫኑ።\n"
            "🍀 መልካም ዕድል!"
        ),
        "quick_btn": "⚡ ፈጣን ግዢ (በራስ-ሰር)",
        "buy": "✍️ ቁጥር መምረጥ (በእጅ)",
        "my": "📋 የእኔ ዕጣዎች",
        "how": "📖 እንዴት እንደሚሰራ",
        "support": "☎️ ድጋፍ",
        "back": "🔙 ተመለስ",
        "home": "🏠 መነሻ",
        "select_ticket": "🎟️ <b>የዕጣ ቁጥር ይምረጡ</b>\n\nራስ-ሰር ወይም በእጅ መምረጥ ይችላሉ፦",
        "random_btn": "🎲 ራስ-ሰር ምረጥ",
        "manual_btn": "✍️ ቁጥር አስገባ",
        "ask_number": "✍️ <b>የዕጣ ቁጥር ያስገቡ</b>\n\nከ {tmin} እስከ {tmax} ባለው ክልል ውስጥ፦",
        "invalid_number": "❌ ቁጥሩ {tmin}–{tmax} መሆን አለበት። እንደገና ይሞክሩ፦",
        "taken_number": "❌ <b>ቁጥር #{n} ተይዟል!</b>\n\nሌላ ይምረጡ ወይም ራስ-ሰር ይጠቀሙ፦",
        "no_available": "😔 ሁሉም ዕጣ ተይዟል።",
        "ticket_held": (
            "✅ <b>ዕጣ #{n} ለእርስዎ ተይዟል!</b>\n\n"
            "💰 የሚከፍሉት: <b>{price} ብር</b>\n"
            "⏰ የክፍያ ጊዜ: <b>{mins} ደቂቃ</b>\n\n"
            "👇 ቀጣይ እርምጃዎች፦\n"
            "1. ከታች ካሉት አካውንቶች አንዱ ላይ ይክፈሉ።\n"
            "2. ‘ክፍያ ፈጸምኩ’ ይጫኑ።\n"
            "3. የክፍያ ስክሪንሾት ይላኩ።"
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
        "ask_shot": "📸 <b>የክፍያ ማስረጃ</b>\n\nክፍያውን ከፈጸሙ በኋላ ግልጽ የሆነ ስክሪንሾት እንደ ፎቶ ይላኩ።",
        "bad_shot": "❌ እባክዎ ፎቶ (ስክሪንሾት) ብቻ ይላኩ።",
        "ask_name": "👤 <b>ሙሉ ስም</b>\n\nበክፍያው ላይ ያለውን ሙሉ ስምዎን ይጻፉ፦",
        "ask_phone": "📱 <b>ስልክ ቁጥር</b>\n\nለምሳሌ፦ 0912345678 ወይም +251912345678",
        "bad_phone": "❌ ስልክ ቁጥሩ ትክክል አይደለም። እንደ 0912345678 ያስገቡ፦",
        "canceled": "❌ ጥያቄው ተሰርዟል። ዕጣው ነፃ ሆኗል።",
        "sent": "✅ <b>ተጠናቋል! ጥያቄዎ ተልኳል።</b>\n\n🧾 የክፍያ ማስረጃዎ ለአድሚን ተልኳል።\n⏳ አድሚን ክፍያውን እስኪያረጋግጥ ይጠብቁ።\n📋 ሁኔታውን ‘የእኔ ዕጣዎች’ ውስጥ ማየት ይችላሉ።",
        "approved": "🎉 <b>ዕጣዎ ተረጋግጧል!</b>\n\n🚗 {car}\n🎟️ ዕጣ: #{ticket}\n\nመልካም ዕድል! 🍀",
        "rejected": "❌ <b>ጥያቄዎ ተመልሷል</b>\n\nምክንያት: {reason}",
        "no_orders": "📭 <b>እስካሁን ዕጣ የለዎትም።</b>",
        "orders": "🎟️ <b>የእርስዎ ዕጣዎች</b>\n",
        "how_text": (
            "📖 <b>እንዴት እንደሚሰራ</b>\n\n"
            "1️⃣ ‘ፈጣን ግዢ’ ወይም ‘ቁጥር መምረጥ’ ይጫኑ።\n"
            "2️⃣ የባንክ አካውንቱን በመጠቀም ይክፈሉ።\n"
            "3️⃣ ‘ክፍያ ፈጸምኩ’ በመጫን ስክሪንሾት ይላኩ።\n"
            "4️⃣ (ለመጀመሪያ ጊዜ ብቻ) ስምና ስልክ ይጻፉ።\n"
            "5️⃣ አድሚን ክፍያውን ያረጋግጣል።\n\n"
            "💡 ማስታወሻ፦ ዕጣ ቁጥሩ በጊዜያዊነት ብቻ ይያዛል። በተጠቀሰው ጊዜ ውስጥ ክፍያ ይፈጽሙ።"
        ),
        "support_text": "☎️ <b>ድጋፍ</b>\n\n{ss}",
        "session_expired": "⏰ የእርስዎ ዕጣ ጊዜ አልፏል። እንደገና ይሞክሩ።",
        "back_to_cars": "🔙 ወደ መኪናዎች",
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
            "🚗 <b>Konkolaataa carraa har'aa</b>\n\n"
            "Baga nagaan dhuftan, <b>{name}</b>! 👋\n\n"
            "🏆 <b>Konkolaataa injifachuu dandeessan</b>\n"
            "🚘 <b>{car_name}</b>\n"
            "📝 {description}\n\n"
            "💵 Gatii carraa tokkoo: <b>{price} Birr</b>\n"
            "🎟️ Carraa hafe: <b>{remaining}</b>\n\n"
            "👤 Abbaa Equb: <b>Geetinet Fikadu Jiraata</b>\n\n"
            "👇 Hirmaachuuf <b>«Carraa biti»</b> tuqi.\n"
            "🍀 Carraa gaarii!"
        ),
        "quick_btn": "⚡ Saffisaa biti (Ofumaan)",
        "buy": "✍️ Lakkoofsa filadhu (Harkaan)",
        "my": "📋 Carraa koo",
        "how": "📖 Akkamitti hojjeta",
        "support": "☎️ Deeggarsa",
        "back": "🔙 Deebi'i",
        "home": "🏠 Jalqaba",
        "select_ticket": "🎟️ <b>Lakkoofsa carraa filadhaa</b>\n\nOfumaan yookaan harkaan filachuu dandeessu:",
        "random_btn": "🎲 Ofumaan fili",
        "manual_btn": "✍️ Lakkoofsa galchi",
        "ask_number": "✍️ <b>Lakkoofsa carraa galchi</b>\n\nLakkoofsa {tmin} hanga {tmax} gidduu galchi:",
        "invalid_number": "❌ {tmin}–{tmax} gidduu ta'uu qaba. Irra deebi'i:",
        "taken_number": "❌ <b>Lakkoofsi #{n} qabameera!</b>\n\nKan biraa filadhu:",
        "no_available": "😔 Carraan hundi qabameera.",
        "ticket_held": (
            "✅ <b>Carraan #{n} siif qabameera!</b>\n\n"
            "💰 Kaffaltii: <b>{price} Birr</b>\n"
            "⏰ Yeroo kaffaltii: <b>{mins} daqiiqaa</b>\n\n"
            "👇 Tarkaanfii itti aanu:\n"
            "1. Herrega armaan gadii keessaa tokko irratti kaffali.\n"
            "2. ‘Kaffaltii raawwadhe’ tuqi.\n"
            "3. Suuraa kaffaltii ergi."
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
        "ask_shot": "📸 <b>Ragaa kaffaltii</b>\n\nErga kaffaltee booda screenshot ifa ta'e akka suuraatti ergi.",
        "bad_shot": "❌ Maaloo suuraa qofa ergi.",
        "ask_name": "👤 <b>Maqaa guutuu</b>\n\nMaqaa kaffaltii irratti mul'atu galchi:",
        "ask_phone": "📱 <b>Lakkoofsa bilbilaa</b>\n\nFakkeenya: 0912345678 ykn +251912345678",
        "bad_phone": "❌ Bilbilli sirrii miti. Akka 0912345678:",
        "canceled": "❌ Haqameera. Carraan bilisa ta'e.",
        "sent": "✅ <b>Xumurameera! Gaaffiin kee ergameera.</b>\n\n🧾 Ragaan kaffaltii adminitti ergameera.\n⏳ Admin kaffaltii hanga mirkaneessutti eegi.\n📋 Haala isaa ‘Carraa koo’ keessaa ilaaluu dandeessa.",
        "approved": "🎉 <b>Carraan keessan mirkanaa'e!</b>\n\n🚗 {car}\n🎟️ Carraa: #{ticket}\n\nCarraa gaarii! 🍀",
        "rejected": "❌ <b>Gaaffiin deebi'e</b>\n\nSababa: {reason}",
        "no_orders": "📭 <b>Carraa hin qabdan.</b>",
        "orders": "🎟️ <b>Carraa keessan</b>\n",
        "how_text": (
            "📖 <b>Akkamitti hojjeta?</b>\n\n"
            "1️⃣ ‘Saffisaa biti’ ykn ‘Lakkoofsa filadhu’ tuqi.\n"
            "2️⃣ Herrega kaffaltii fayyadamuun kaffali.\n"
            "3️⃣ ‘Kaffaltii raawwadhe’ tuqiitii screenshot ergi.\n"
            "4️⃣ (Yeroo jalqabaaf qofa) maqaa fi bilbila galchi.\n"
            "5️⃣ Admin kaffaltii mirkaneessa.\n\n"
            "💡 Hubachiisa: Lakkoofsi yeroo muraasaaf qofa siif qabama; yeroo jedhame keessatti kaffali."
        ),
        "support_text": "☎️ <b>Deeggarsa</b>\n\n{ss}",
        "session_expired": "⏰ Yeroon carraa keessan dabreera.",
        "back_to_cars": "🔙 Konkolaataa",
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
        [InlineKeyboardButton(text=t(lang, "quick_btn"), callback_data="menu:quick")],
        [InlineKeyboardButton(text=t(lang, "buy"), callback_data="menu:buy")],
        [InlineKeyboardButton(text=t(lang, "my"), callback_data="menu:my")],
        [
            InlineKeyboardButton(text=t(lang, "how"), callback_data="menu:how"),
            InlineKeyboardButton(text=t(lang, "support"), callback_data="menu:support"),
        ],
    ])

def ticket_action_kb(lang, car_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "random_btn"), callback_data=f"tkt:rand:{car_id}"),
            InlineKeyboardButton(text=t(lang, "manual_btn"), callback_data=f"tkt:man:{car_id}"),
        ],
        [InlineKeyboardButton(text=t(lang, "home"), callback_data="menu:home")],
    ])

def pay_kb(lang, oid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "paid_btn"), callback_data=f"pay:paid:{oid}")],
        [InlineKeyboardButton(text=t(lang, "cancel_btn"), callback_data=f"pay:cancel:{oid}")],
    ])

def admin_kb(oid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"adm:ok:{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"adm:no:{oid}"),
    ]])

# ============================================================
#  BOT SETUP
# ============================================================
bot = Bot(cfg.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

class BuyFSM(StatesGroup):
    manual_number = State()
    shot = State()
    name = State()
    phone = State()

class RejectFSM(StatesGroup):
    reason = State()

async def get_lang(uid):
    u = await db.get_user(uid)
    return u['lang'] if u and u['lang'] else "am"

async def main_campaign(lang, user_name):
    cars = await db.list_cars(active_only=True)
    car = cars[0] if cars else None
    if not car:
        fallback = {
            "am": "🚗 <b>የመኪና ዕጣ እቁብ</b>\n\nአሁን የተከፈተ ዕጣ የለም። እባክዎ ቆይተው ይመለሱ።\n\n👤 ባለቤት፦ <b>ጌትነት ፍቃዱ ጂራታ</b>",
            "om": "🚗 <b>Equb carraa konkolaataa</b>\n\nAmma carraan banaa hin jiru. Maaloo yeroo biraa deebi'aa.\n\n👤 Abbaa Equb: <b>Geetinet Fikadu Jiraata</b>",
        }
        return fallback.get(lang, fallback["am"]), None
    stats = await db.car_stats(car['id'])
    desc = (car['description'] or "የመኪናው ዝርዝር በቅርቡ ይጨመራል።") if lang == "am" else (car['description'] or "Ibsi konkolaataa yeroo dhiyootti ni dabalama.")
    desc = str(desc).strip()
    if len(desc) > 500: desc = desc[:497] + "..."
    txt = t(lang, "menu", name=user_name, car_name=car['name'], description=desc,
            price=car['price'], remaining=stats["remaining"])
    image = car['image'] if car['image'] else None
    return txt, image

# ---------- /start ----------
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    u = await db.get_user(msg.from_user.id)
    lang = u['lang'] if u and u['lang'] else "am"
    await db.save_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name, lang)
    
    if not (u and u['lang']):
        await msg.answer(t("am", "welcome"), reply_markup=lang_kb())
        return
        
    txt, image = await main_campaign(lang, msg.from_user.full_name)
    kb = main_menu(lang)
    try:
        if image: await msg.answer_photo(image, caption=txt, reply_markup=kb)
        else: await msg.answer(txt, reply_markup=kb)
    except Exception as e:
        log.warning("Could not show campaign photo: %s", e)
        await msg.answer(txt, reply_markup=kb)

@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await db.save_user(cb.from_user.id, cb.from_user.username or "", cb.from_user.full_name, lang)
    txt, image = await main_campaign(lang, cb.from_user.full_name)
    try: await cb.message.delete()
    except Exception: pass
    try:
        if image: await cb.message.answer_photo(image, caption=txt, reply_markup=main_menu(lang))
        else: await cb.message.answer(txt, reply_markup=main_menu(lang))
    except Exception:
        await cb.message.answer(txt, reply_markup=main_menu(lang))
    await cb.answer()

# ---------- Menus ----------
@dp.callback_query(F.data == "menu:home")
async def menu_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    txt, image = await main_campaign(lang, cb.from_user.full_name)
    kb = main_menu(lang)
    try:
        if cb.message.photo and image: await cb.message.edit_caption(caption=txt, reply_markup=kb)
        elif cb.message.photo and not image:
            await cb.message.delete()
            await cb.message.answer(txt, reply_markup=kb)
        else: await cb.message.edit_text(txt, reply_markup=kb)
    except Exception:
        try:
            if image: await cb.message.answer_photo(image, caption=txt, reply_markup=kb)
            else: await cb.message.answer(txt, reply_markup=kb)
        except Exception: pass
    await cb.answer()

@dp.callback_query(F.data == "menu:how")
async def menu_how(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    try:
        await cb.message.edit_text(t(lang, "how_text"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "home"), callback_data="menu:home")]]))
    except Exception:
        await cb.message.answer(t(lang, "how_text"))
    await cb.answer()

@dp.callback_query(F.data == "menu:support")
async def menu_support(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    try:
        await cb.message.edit_text(t(lang, "support_text", ss=cfg.SUPPORT_USERNAME), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "home"), callback_data="menu:home")]]))
    except Exception:
        await cb.message.answer(t(lang, "support_text", ss=cfg.SUPPORT_USERNAME))
    await cb.answer()

@dp.callback_query(F.data == "menu:my")
async def menu_my(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    rows = await db.user_orders(cb.from_user.id)
    if not rows: txt = t(lang, "no_orders")
    else:
        icons = {"pending": "⏳", "approved": "✅", "rejected": "❌", "held": "🔒", "blocked": "🚫"}
        status_am = {"pending": "በማረጋገጥ ላይ", "approved": "ተጸድቋል", "rejected": "ተመልሷል", "held": "ጊዜያዊ ተይዟል", "blocked": "ታግዷል"}
        status_om = {"pending": "Mirkaneessaa jira", "approved": "Mirkanaa'eera", "rejected": "Deebi'eera", "held": "Yeroo muraasaaf qabame", "blocked": "Dhaabbateera"}
        statuses = status_om if lang == "om" else status_am
        lines = [t(lang, "orders"), ""]
        for o in rows:
            lines.append(f"{icons.get(o['status'],'•')} <b>#{o['ticket_no']}</b> · {html.escape(str(o['name'] or '-'))}\n   📌 {statuses.get(o['status'], o['status'])}")
        txt = "\n".join(lines)
    try:
        await cb.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "home"), callback_data="menu:home")]]))
    except Exception:
        await cb.message.answer(txt)
    await cb.answer()

# ---------- Buy Flow ----------
@dp.callback_query(F.data == "menu:quick")
async def menu_quick(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    cars = await db.list_cars(active_only=True)
    if not cars:
        await cb.answer("📭 አሁን የሚገኝ ዕጣ የለም።", show_alert=True); return
    car = cars[0]
    
    stats = await db.car_stats(car['id'])
    if stats["remaining"] <= 0:
        await cb.answer(t(lang, "no_available"), show_alert=True); return

    taken = await db.taken_numbers(car['id'])
    avail = [n for n in range(car['ticket_min'], car['ticket_max'] + 1) if n not in taken]
    if not avail:
        await cb.answer(t(lang, "no_available"), show_alert=True); return

    n = random.choice(avail)
    oid = await db.hold_ticket(car['id'], cb.from_user.id, n, cfg.HOLD_MINUTES)
    if not oid:
        await cb.answer("⚠️ እንደገና ይሞክሩ።", show_alert=True); return

    await state.update_data(oid=oid, ticket=n, car_id=car['id'], car_name=car['name'], price=car['price'], tmin=car['ticket_min'], tmax=car['ticket_max'])
    
    # ሁለቱንም ጽሑፎች በአንድ ላይ ማጣመር
    txt = t(lang, "ticket_held", n=n, mins=cfg.HOLD_MINUTES, price=car['price']) + "\n\n" + t(lang, "banks")
    try: await cb.message.edit_text(txt, reply_markup=pay_kb(lang, oid))
    except Exception: await cb.message.answer(txt, reply_markup=pay_kb(lang, oid))
    await cb.answer("⚡ ዕጣው ተይዟል!")

@dp.callback_query(F.data == "menu:buy")
async def menu_buy(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    cars = await db.list_cars(active_only=True)
    if not cars:
        await cb.answer("📭 አሁን የሚገኝ ዕጣ የለም።", show_alert=True); return
    car = cars[0]
    
    stats = await db.car_stats(car['id'])
    if stats["remaining"] <= 0:
        await cb.answer(t(lang, "no_available"), show_alert=True); return
        
    await state.update_data(car_id=car['id'], car_name=car['name'], tmin=car['ticket_min'], tmax=car['ticket_max'], price=car['price'])
    text = (
        f"🎟️ <b>የዕጣ ግዢ</b>\n\n"
        f"🚗 መኪና: <b>{html.escape(str(car['name']))}</b>\n"
        f"💵 የአንድ ዕጣ ዋጋ: <b>{car['price']} ብር</b>\n"
        f"🟢 የቀሩ ዕጣዎች: <b>{stats['remaining']}</b>\n\n"
        "👇 <b>የዕጣ ቁጥር ለመምረጥ ከታች አንዱን ይጫኑ።</b>\n"
        "🎲 ራስ-ሰር ምረጥ — ቦቱ ቁጥር ይመርጥልዎታል።\n"
        "✍️ ቁጥር አስገባ — የሚፈልጉትን ቁጥር ይጻፉ።"
    )
    kb = ticket_action_kb(lang, car['id'])
    try: await cb.message.edit_text(text, reply_markup=kb)
    except Exception: await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data.startswith("tkt:rand:"))
async def pick_random(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    car_id = int(cb.data.split(":")[2])
    car = await db.get_car(car_id)
    if not car: await cb.answer("❌", show_alert=True); return
    
    taken = await db.taken_numbers(car_id)
    total = car['ticket_max'] - car['ticket_min'] + 1
    if len(taken) >= total: await cb.answer(t(lang, "no_available"), show_alert=True); return
    
    for _ in range(30):
        n = random.randint(car['ticket_min'], car['ticket_max'])
        if n not in taken: break
    else:
        avail = [x for x in range(car['ticket_min'], car['ticket_max']+1) if x not in taken]
        if not avail: await cb.answer(t(lang, "no_available"), show_alert=True); return
        n = random.choice(avail)
        
    oid = await db.hold_ticket(car_id, cb.from_user.id, n, cfg.HOLD_MINUTES)
    if not oid: await cb.answer(t(lang, "taken_number", n=n), show_alert=True); return
    
    await state.update_data(oid=oid, ticket=n)
    
    txt = t(lang, "ticket_held", n=n, mins=cfg.HOLD_MINUTES, price=car['price']) + "\n\n" + t(lang, "banks")
    try: await cb.message.edit_text(txt, reply_markup=pay_kb(lang, oid))
    except Exception: await cb.message.answer(txt, reply_markup=pay_kb(lang, oid))
    await cb.answer("🎲")

@dp.callback_query(F.data.startswith("tkt:man:"))
async def manual_number(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    car_id = int(cb.data.split(":")[2])
    car = await db.get_car(car_id)
    if not car: await cb.answer("❌", show_alert=True); return
    
    await state.update_data(car_id=car_id, car_name=car['name'], tmin=car['ticket_min'], tmax=car['ticket_max'], price=car['price'])
    await state.set_state(BuyFSM.manual_number)
    await cb.message.answer(t(lang, "ask_number", tmin=car['ticket_min'], tmax=car['ticket_max']))
    await cb.answer()

@dp.message(BuyFSM.manual_number, F.text)
async def process_manual_number(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    d = await state.get_data()
    txt = msg.text.strip()
    if not txt.isdigit():
        await msg.answer(t(lang, "invalid_number", tmin=d["tmin"], tmax=d["tmax"])); return
    
    n = int(txt)
    if not (d["tmin"] <= n <= d["tmax"]):
        await msg.answer(t(lang, "invalid_number", tmin=d["tmin"], tmax=d["tmax"])); return
    
    if not await db.is_ticket_available(d["car_id"], n):
        await msg.answer(t(lang, "taken_number", n=n), reply_markup=ticket_action_kb(lang, d["car_id"]))
        await state.clear(); return
        
    oid = await db.hold_ticket(d["car_id"], msg.from_user.id, n, cfg.HOLD_MINUTES)
    if not oid:
        await msg.answer(t(lang, "taken_number", n=n))
        await state.clear(); return
        
    await state.update_data(oid=oid, ticket=n)
    
    text = t(lang, "ticket_held", n=n, mins=cfg.HOLD_MINUTES, price=d["price"]) + "\n\n" + t(lang, "banks")
    await msg.answer(text, reply_markup=pay_kb(lang, oid))

# ---------- Payment & Auto-Submit ----------
@dp.callback_query(F.data.startswith("pay:paid:"))
async def pay_paid(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    oid = int(cb.data.split(":")[2])
    o = await db.get_order(oid)
    if not o or o['user_id'] != cb.from_user.id or o['status'] != "held":
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
    if not o or o['user_id'] != cb.from_user.id or o['status'] != "held":
        await cb.answer("Order not found or no longer held", show_alert=True); return
    await db.release_order(oid, user_id=cb.from_user.id)
    await state.clear()
    try: await cb.message.edit_text(t(lang, "canceled"), reply_markup=main_menu(lang))
    except Exception: await cb.message.answer(t(lang, "canceled"))
    await cb.answer()

@dp.message(BuyFSM.shot, F.photo)
async def f_shot(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await state.update_data(shot=msg.photo[-1].file_id)

    # 💾 ፕሮፋይል ካለ → ስም/ስልክ ሳይጠይቅ ወዲያውኑ ያስረክባል (Auto-Submit)
    saved_name, saved_phone = await db.get_profile(msg.from_user.id)
    if saved_name and saved_phone:
        await state.update_data(name=saved_name, phone=saved_phone)
        await finalize_order(msg, state, lang)
        return

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
        await msg.answer("❌ " + t(lang, "ask_name")); return
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
    
    # ስልክ እንደተረጋገጠ ወዲያውኑ ያስረክባል (Auto-Submit)
    await finalize_order(msg, state, lang)

async def finalize_order(event, state: FSMContext, lang: str):
    """ያለ ማረጋገጫ ቁልፍ በቀጥታ ለአድሚን የሚልክ ፈንክሽን"""
    d = await state.get_data()
    
    changed = await db.confirm_hold(d["oid"], d.get("name", ""), d.get("phone", ""), d.get("shot"), user_id=event.from_user.id)
    if not changed:
        await event.answer(t(lang, "session_expired"))
        await state.clear(); return

    # ፕሮፋይል አስቀምጥ (ለቀጣይ ጊዜ)
    await db.save_profile(event.from_user.id, d.get("name", ""), d.get("phone", ""))
    await state.clear()

    # ለተጠቃሚው መልእክት
    await event.answer(t(lang, "sent"))
    home_text, home_image = await main_campaign(lang, event.from_user.full_name)
    if home_image:
        try: await event.answer_photo(home_image, caption=home_text, reply_markup=main_menu(lang))
        except Exception: await event.answer(home_text, reply_markup=main_menu(lang))
    else:
        await event.answer(home_text, reply_markup=main_menu(lang))

    # ለአድሚን መልእክት
    admin_text = (
        f"🔔 <b>አዲስ ጥያቄ #{d['oid']}</b>\n\n"
        f"🚗 {html.escape(str(d['car_name']))}\n"
        f"👤 {html.escape(str(d['name']))}\n"
        f"📱 {html.escape(str(d['phone']))}\n"
        f"🎟️ ዕጣ: <b>#{d['ticket']}</b>\n"
        f"💬 @{event.from_user.username or '-'} — <code>{event.from_user.id}</code>"
    )
    try:
        await bot.send_photo(cfg.ADMIN_GROUP_ID, photo=d["shot"], caption=admin_text, reply_markup=admin_kb(d['oid']))
    except Exception as e:
        log.error(f"Admin send failed: {e}")

# ---------- Telegram Admin ----------
@dp.callback_query(F.data.startswith("adm:ok:"))
async def adm_ok(cb: CallbackQuery):
    if cb.from_user.id not in cfg.ADMIN_IDS:
        await cb.answer("❌ ፈቃድ የለዎትም", show_alert=True); return
    oid = int(cb.data.split(":")[2])
    o = await db.get_order(oid)
    if not o: await cb.answer("Not found"); return
    changed = await db.update_order_status(oid, "approved", expected_status="pending", actor=f"telegram:{cb.from_user.id}")
    if not changed: await cb.answer("Already processed", show_alert=True); return
    car = await db.get_car(o['car_id'])
    try: await bot.send_message(o['user_id'], t("am", "approved", car=car['name'] if car else "-", ticket=o['ticket_no']))
    except Exception as e: log.error(e)
    try: await cb.message.edit_caption(caption=(cb.message.caption or "") + "\n\n✅ <b>ጸድቋል</b>", reply_markup=None)
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
    if not o or o['status'] != "pending": await msg.answer("Order not found or already processed"); return
    changed = await db.update_order_status(oid, "rejected", msg.text.strip(), expected_status="pending", actor=f"telegram:{msg.from_user.id}")
    if not changed: await msg.answer("Order already processed"); return
    try: await bot.send_message(o['user_id'], t("am", "rejected", reason=msg.text.strip()))
    except Exception as e: log.error(e)
    await msg.answer(f"❌ Order #{oid} ተመልሷል።")

# ============================================================
#  AUTO REMINDER
# ============================================================
async def reminder_task():
    while True:
        try:
            await asyncio.sleep(30)
            expiring = await db.get_expiring_holds()
            for o in expiring:
                lang = await get_lang(o['user_id'])
                try:
                    await bot.send_message(o['user_id'], t(lang, "reminder", ticket=o['ticket_no']))
                    await db.mark_reminder_sent(o['id'])
                except Exception:
                    await db.mark_reminder_sent(o['id'])
        except Exception as e:
            log.error(f"Reminder task error: {e}")

# ============================================================
#  ADMIN WEB PANEL (ኮዱ ሙሉ ለሙሉ እንዳለ ነው - ለአጭርነት ሲባል እዚህ አልደገመውም)
# ============================================================
def make_token():
    ts = str(int(time.time()))
    sig = hmac.new(cfg.SECRET_KEY.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"

def verify_token(tok):
    try:
        ts, sig = tok.split(".")
        exp = hmac.new(cfg.SECRET_KEY.encode(), ts.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, exp): return False
        age = time.time() - int(ts)
        if age < -30 or age > cfg.SESSION_TTL_SECONDS: return False
        return True
    except Exception: return False

def authed(req): return verify_token(req.cookies.get("auth", ""))

def auth_mw():
    @web.middleware
    async def mw(req, handler):
        if req.path.startswith("/admin") and req.path not in ("/admin/login",):
            if not authed(req): raise web.HTTPFound("/admin/login")
        return await handler(req)
    return mw

CSS = """...""" # (የAdmin CSS ኮድ እንዳለ ይቀመጣል - ቦታ ለመቆጠብ እዚህ አልጻፍኩትም፣ ከቀድሞው ኮድዎ ይውሰዱት)

def layout(title, body, active=""):
    # (የAdmin Layout ኮድ እንዳለ ይቀመጣል)
    pass 

# ... (የAdmin Web Handlers እንደ ቀድሞው ይቀጥላሉ: login_get, login_post, dash, cars_list, orders_list, etc.)

# ============================================================
#  APP SETUP (የተስተካከለው የዋና አፕሊኬሽን ክፍል)
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
    asyncio.create_task(reminder_task())
    log.info("🔔 Reminder task started")
    if cfg.USE_WEBHOOK:
        url = f"{cfg.WEBHOOK_URL}{cfg.WEBHOOK_PATH}"
        await bot.set_webhook(url, secret_token=cfg.WEBHOOK_SECRET, drop_pending_updates=True)
        log.info(f"✅ Webhook set: {url}")

async def on_shutdown(app):
    if cfg.USE_WEBHOOK:
        try: await bot.delete_webhook()
        except Exception: pass
    try: await bot.session.close()
    except Exception: pass

def main():
    cfg.validate_settings()
    db.DATABASE_URL = cfg.DATABASE_URL
    
    # 🔥 Polling mode ላይ ከመግባቱ በፊት ዌብሁክ መኖሩን አረጋግጦ ማጥፋት
    if not cfg.USE_WEBHOOK:
        async def run_poll():
            await db.init_db()
            # 👇 ይህ መስመር ስህተቱን (TelegramConflictError) ይፈታዋል
            await bot.delete_webhook(drop_pending_updates=True)
            
            asyncio.create_task(reminder_task())
            log.info("🤖 Polling mode started (Webhook deleted)")
            await dp.start_polling(bot)
        asyncio.run(run_poll())
    else:
        app = build_web()
        SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=cfg.WEBHOOK_SECRET).register(app, path=cfg.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        app.on_startup.append(on_startup)
        app.on_cleanup.append(on_shutdown)
        log.info(f"🚀 Listening on {cfg.HOST}:{cfg.PORT}")
        web.run_app(app, host=cfg.HOST, port=cfg.PORT, print=None)

if __name__ == "__main__":
    main()
