# ============================================================
#  CAR EQUB BOT + ADMIN WEB PANEL
#  Run: python app.py
# ============================================================
import asyncio, hmac, hashlib, time, logging, re
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
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import config as cfg
import database as db

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("equb")

# ============================================================
#  TEXTS
# ============================================================
T = {
    "am": {
        "welcome": "እንኳን ደህና መጡ! 🎉\nእባክዎ ቋንቋ ይምረጡ፦",
        "menu": "ሰላም {name} 👋\nከታች ካሉት ይምረጡ፦",
        "cars": "🚗 መኪናዎች",
        "my": "📋 የእኔ ዕጣዎች",
        "how": "📖 እንዴት እንደሚሰራ",
        "support": "☎️ ድጋፍ",
        "back": "🔙 ተመለስ",
        "cont": "✅ ቀጥል",
        "paid": "📤 ክፍያ ፈጸምኩ",
        "pick_car": "🚗 የሚፈልጉትን መኪና ይምረጡ፦",
        "car_info": (
            "🚗 <b>{name}</b>\n{desc}\n\n"
            "🎟️ ዋጋ: <b>{price} ብር</b>\n"
            "📅 የመዝጊያ ቀን: {closing}\n"
            "🎯 ጠቅላላ ዕጣ: {tmin}–{tmax}\n"
            "🟢 ቀሪ: {remaining}\n"
            "🔴 የተያዙ: {taken}"
        ),
        "banks": (
            "💳 ክፍያ የሚፈጽሙበት አካውንት፦\n\n"
            "🏦 CBE: <code>1000805382159</code>\n"
            "🏦 BOA: <code>267410666</code>\n"
            "🏦 Awash: <code>013201812592600</code>\n"
            "👤 ባለቤት: ጌታቸዉ ፍቃዱ ጅራታ\n\n"
            "⚠️ ክፍያ ከፈጸሙ በኋላ ስክሪንሾት ያስፈልጋል።"
        ),
        "ask_shot": "📸 የክፍያ ስክሪንሾት ይላኩ፦",
        "ask_tx": "🔢 የግብይት ማጣቀሻ (FT...) ያስገቡ፦",
        "ask_ticket": "🎟️ የዕጣ ቁጥር ({tmin}–{tmax}) ያስገቡ፦",
        "ask_name": "👤 ሙሉ ስምዎን ያስገቡ፦",
        "ask_phone": "📱 ስልክ ቁጥር (09xxxxxxxx)፦",
        "confirm": (
            "📋 ያረጋግጡ፦\n\n🚗 {car}\n🎟️ ዕጣ: {ticket}\n"
            "👤 {name}\n📱 {phone}\n🔢 {tx}"
        ),
        "ok_btn": "✅ አረጋግጥ",
        "no_btn": "❌ ሰርዝ",
        "canceled": "❌ ተሰርዟል።",
        "taken": "❌ ተይዟል። ሌላ ይምረጡ፦",
        "bad_phone": "❌ ስልክ ትክክል አይደለም። እንደ 0912345678 ያስገቡ፦",
        "bad_ticket": "❌ ቁጥሩ {tmin}–{tmax} መሆን አለበት። እንደገና፦",
        "sent": "✅ ጥያቄዎ ለአድሚን ተልኳል። ይጠብቁ።",
        "approved": "🎉 ተረጋግጧል!\n🚗 {car}\n🎟️ ዕጣ: {ticket}",
        "rejected": "❌ ተመልሷል።\nምክንያት: {reason}",
        "no_orders": "📭 እስካሁን ዕጣ የለዎትም።",
        "orders": "🎟️ የእርስዎ ዕጣዎች፦\n",
        "how_text": (
            "📖 <b>እንዴት እንደሚሰራ</b>\n\n"
            "1️⃣ መኪና ይምረጡ\n2️⃣ ከባንክ ክፍያ ይፈጽሙ\n"
            "3️⃣ ስክሪንሾት + TX ያስገቡ\n4️⃣ ዕጣ ቁጥር ይምረጡ\n"
            "5️⃣ ስምና ስልክ ያስገቡ\n6️⃣ አድሚን ያረጋግጣል"
        ),
        "support_text": "☎️ ድጋፍ: {s}",
    },
    "om": {
        "welcome": "Baga nagaan dhuftan! 🎉\nMaaloo afaan filadhaa:",
        "menu": "Akkam {name} 👋\nFiladhaa:",
        "cars": "🚗 Konkolaataa",
        "my": "📋 Carraa koo",
        "how": "📖 Akkamitti hojjeta",
        "support": "☎️ Deeggarsa",
        "back": "🔙 Deebi'i",
        "cont": "✅ Itti fufi",
        "paid": "📤 Kaffaltii raawwadhe",
        "pick_car": "🚗 Konkolaataa filadhaa:",
        "car_info": (
            "🚗 <b>{name}</b>\n{desc}\n\n"
            "🎟️ Gatii: <b>{price} Birr</b>\n"
            "📅 Guyyaa cufiinsaa: {closing}\n"
            "🎯 Carraa: {tmin}–{tmax}\n"
            "🟢 Hafe: {remaining}\n🔴 Qabame: {taken}"
        ),
        "banks": (
            "💳 Herrega kaffaltii:\n\n🏦 CBE: <code>1000805382159</code>\n"
            "🏦 BOA: <code>267410666</code>\n"
            "🏦 Awash: <code>013201812592600</code>\n"
            "👤 Geetachoo Fikaduu Jiraataa\n\n⚠️ Screenshot barbaachisa."
        ),
        "ask_shot": "📸 Suuraa kaffaltii ergi:",
        "ask_tx": "🔢 Raga kaffaltii (FT...) galchi:",
        "ask_ticket": "🎟️ Lakkoofsa carraa ({tmin}–{tmax}) galchi:",
        "ask_name": "👤 Maqaa guutuu galchi:",
        "ask_phone": "📱 Bilbila (09xxxxxxxx) galchi:",
        "confirm": "📋 Mirkaneessi:\n\n🚗 {car}\n🎟️ {ticket}\n👤 {name}\n📱 {phone}\n🔢 {tx}",
        "ok_btn": "✅ Mirkaneessi",
        "no_btn": "❌ Haqi",
        "canceled": "❌ Haqameera.",
        "taken": "❌ Qabameera. Kan biraa filadhu:",
        "bad_phone": "❌ Bilbila sirrii miti. Akka 0912345678:",
        "bad_ticket": "❌ {tmin}–{tmax} gidduu ta'uu qaba. Irra deebi'i:",
        "sent": "✅ Adminitti ergameera. Eegaa.",
        "approved": "🎉 Mirkanaa'e!\n🚗 {car}\n🎟️ {ticket}",
        "rejected": "❌ Deebi'eera.\nSababa: {reason}",
        "no_orders": "📭 Carraa hin qabdan.",
        "orders": "🎟️ Carraa keessan:\n",
        "how_text": (
            "📖 <b>Akkamitti hojjeta</b>\n\n1️⃣ Konkolaataa filadhu\n"
            "2️⃣ Kaffaltii raawwadhu\n3️⃣ Screenshot + TX galchi\n"
            "4️⃣ Carraa filadhu\n5️⃣ Maqaa fi bilbila galchi\n6️⃣ Admin mirkaneessa"
        ),
        "support_text": "☎️ Deeggarsa: {s}",
    },
}

def t(lang, key, **kw):
    txt = T.get(lang, T["am"]).get(key, "")
    return txt.format(**kw) if kw else txt

# ============================================================
#  KEYBOARDS
# ============================================================
def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇪🇹 አማርኛ", callback_data="lang:am"),
        InlineKeyboardButton(text="🇪🇹 Afaan Oromoo", callback_data="lang:om"),
    ]])

def main_menu(lang):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t(lang, "cars")), KeyboardButton(text=t(lang, "my"))],
        [KeyboardButton(text=t(lang, "how")), KeyboardButton(text=t(lang, "support"))],
    ], resize_keyboard=True)

def cars_kb(cars):
    rows = []
    for c in cars:
        rows.append([InlineKeyboardButton(
            text=f"🚗 {c[1]} — {c[3]} ብር", callback_data=f"car:{c[0]}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def car_action_kb(lang, car_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cont"), callback_data=f"buy:{car_id}")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:back")],
    ])

def paid_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "paid"), callback_data="buy:paid")],
    ])

def confirm_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "ok_btn"), callback_data="buy:ok"),
         InlineKeyboardButton(text=t(lang, "no_btn"), callback_data="buy:no")],
    ])

def admin_kb(oid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"adm:ok:{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"adm:no:{oid}"),
    ]])

# ============================================================
#  BOT
# ============================================================
bot = Bot(cfg.BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

class BuyFSM(StatesGroup):
    shot = State(); tx = State(); ticket = State()
    name = State(); phone = State(); confirm = State()

class RejectFSM(StatesGroup):
    reason = State()

async def get_lang(uid):
    u = await db.get_user(uid)
    return u[3] if u and u[3] else "am"

@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    u = await db.get_user(msg.from_user.id)
    if u and u[3]:
        await msg.answer(t(u[3], "menu", name=msg.from_user.full_name),
                         reply_markup=main_menu(u[3]))
        return
    await msg.answer(
        "እንኳን ደህና መጡ! / Baga nagaan dhuftan!\n"
        "ቋንቋ ይምረጡ / Afaan filadhaa:",
        reply_markup=lang_kb())

@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await db.save_user(cb.from_user.id, cb.from_user.username or "",
                       cb.from_user.full_name, lang)
    await cb.message.delete()
    await cb.message.answer(t(lang, "menu", name=cb.from_user.full_name),
                            reply_markup=main_menu(lang))
    await cb.answer()

@dp.callback_query(F.data == "menu:back")
async def menu_back(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    await state.clear()
    await cb.message.delete()
    await cb.message.answer(t(lang, "menu", name=cb.from_user.full_name),
                            reply_markup=main_menu(lang))
    await cb.answer()

@dp.message(F.text.in_(["🚗 መኪናዎች", "🚗 Konkolaataa"]))
async def show_cars(msg: Message):
    lang = await get_lang(msg.from_user.id)
    cars = await db.list_cars(active_only=True)
    if not cars:
        await msg.answer("📭 ምንም ንቁ መኪና የለም።")
        return
    await msg.answer(t(lang, "pick_car"), reply_markup=cars_kb(cars))

@dp.message(F.text.in_(["📋 የእኔ ዕጣዎች", "📋 Carraa koo"]))
async def my_orders(msg: Message):
    lang = await get_lang(msg.from_user.id)
    rows = await db.user_orders(msg.from_user.id)
    if not rows:
        await msg.answer(t(lang, "no_orders")); return
    icons = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
    lines = [t(lang, "orders")]
    for oid, tno, st, car in rows:
        lines.append(f"{icons.get(st,'•')} #{oid} — 🚗 {car or '-'} — 🎟️ {tno}")
    await msg.answer("\n".join(lines))

@dp.message(F.text.in_(["📖 እንዴት እንደሚሰራ", "📖 Akkamitti hojjeta"]))
async def how(msg: Message):
    await msg.answer(t(await get_lang(msg.from_user.id), "how_text"))

@dp.message(F.text.in_(["☎️ ድጋፍ", "☎️ Deeggarsa"]))
async def support(msg: Message):
    await msg.answer(t(await get_lang(msg.from_user.id),
                       "support_text", s=cfg.SUPPORT_USERNAME))

@dp.callback_query(F.data.startswith("car:"))
async def show_car(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    car_id = int(cb.data.split(":")[1])
    car = await db.get_car(car_id)
    if not car:
        await cb.answer("Car not found"); return
    stats = await db.car_stats(car_id)
    text = t(lang, "car_info",
             name=car[1], desc=car[2] or "-", price=car[3],
             closing=car[6] or "-", tmin=car[4], tmax=car[5],
             remaining=stats["remaining"], taken=stats["taken"])
    await cb.message.edit_text(text, reply_markup=car_action_kb(lang, car_id))
    await cb.answer()

@dp.callback_query(F.data.startswith("buy:"))
async def buy_cont(cb: CallbackQuery, state: FSMContext):
    val = cb.data.split(":")[1]
    lang = await get_lang(cb.from_user.id)
    if val == "paid":
        await state.set_state(BuyFSM.shot)
        await cb.message.answer(t(lang, "ask_shot"))
        await cb.answer(); return
    try:
        car_id = int(val)
    except ValueError:
        await cb.answer(); return
    car = await db.get_car(car_id)
    if not car or not car[7]:
        await cb.answer("❌ ይህ መኪና ንቁ አይደለም", show_alert=True); return
    await state.update_data(car_id=car_id, car_name=car[1],
                            tmin=car[4], tmax=car[5])
    await cb.message.edit_text(t(lang, "banks"), reply_markup=paid_kb(lang))
    await cb.answer()

@dp.message(BuyFSM.shot, F.photo)
async def f_shot(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await state.update_data(shot=msg.photo[-1].file_id)
    await state.set_state(BuyFSM.tx)
    await msg.answer(t(lang, "ask_tx"))

@dp.message(BuyFSM.shot)
async def f_shot_bad(msg: Message):
    await msg.answer(t(await get_lang(msg.from_user.id), "ask_shot"))

@dp.message(BuyFSM.tx, F.text)
async def f_tx(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await state.update_data(tx=msg.text.strip())
    d = await state.get_data()
    await state.set_state(BuyFSM.ticket)
    await msg.answer(t(lang, "ask_ticket", tmin=d["tmin"], tmax=d["tmax"]))

@dp.message(BuyFSM.ticket, F.text)
async def f_ticket(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    d = await state.get_data()
    if not msg.text.isdigit():
        await msg.answer(t(lang, "bad_ticket", tmin=d["tmin"], tmax=d["tmax"])); return
    n = int(msg.text)
    if not (d["tmin"] <= n <= d["tmax"]):
        await msg.answer(t(lang, "bad_ticket", tmin=d["tmin"], tmax=d["tmax"])); return
    if await db.is_ticket_taken(d["car_id"], n):
        await msg.answer(t(lang, "taken")); return
    await state.update_data(ticket=n)
    await state.set_state(BuyFSM.name)
    await msg.answer(t(lang, "ask_name"))

@dp.message(BuyFSM.name, F.text)
async def f_name(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await state.update_data(name=msg.text.strip())
    await state.set_state(BuyFSM.phone)
    await msg.answer(t(lang, "ask_phone"))

@dp.message(BuyFSM.phone, F.text)
async def f_phone(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    p = msg.text.strip().replace(" ", "")
    if not re.match(r"^(\+2519|09)\d{8}$", p):
        await msg.answer(t(lang, "bad_phone")); return
    await state.update_data(phone=p)
    d = await state.get_data()
    await state.set_state(BuyFSM.confirm)
    text = t(lang, "confirm", car=d["car_name"], ticket=d["ticket"],
             name=d["name"], phone=d["phone"], tx=d["tx"])
    await msg.answer_photo(d["shot"], caption=text, reply_markup=confirm_kb(lang))

@dp.callback_query(F.data == "buy:no", BuyFSM.confirm)
async def f_cancel(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    await state.clear()
    await cb.message.edit_caption(caption=t(lang, "canceled"))
    await cb.answer()

@dp.callback_query(F.data == "buy:ok", BuyFSM.confirm)
async def f_ok(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    d = await state.get_data()
    await state.clear()

    oid = await db.create_order(d["car_id"], cb.from_user.id, d["ticket"],
                                d["name"], d["phone"], d["tx"], d["shot"])
    await cb.message.edit_caption(caption=t(lang, "sent"))

    admin_text = (
        f"🔔 <b>አዲስ ጥያቄ #{oid}</b>\n"
        f"🚗 {d['car_name']}\n"
        f"👤 {d['name']} (@{cb.from_user.username or '-'}) — "
        f"ID: <code>{cb.from_user.id}</code>\n"
        f"🎟️ ዕጣ: {d['ticket']}\n📱 {d['phone']}\n🔢 <code>{d['tx']}</code>"
    )
    try:
        await bot.send_photo(cfg.ADMIN_GROUP_ID, photo=d["shot"],
                             caption=admin_text, reply_markup=admin_kb(oid))
    except Exception as e:
        log.error(f"Admin send failed: {e}")
    await cb.answer()

@dp.callback_query(F.data.startswith("adm:ok:"))
async def adm_ok(cb: CallbackQuery):
    if cb.from_user.id not in cfg.ADMIN_IDS:
        await cb.answer("❌ ፈቃድ የለዎትም", show_alert=True); return
    oid = int(cb.data.split(":")[2])
    o = await db.get_order(oid)
    if not o: await cb.answer("Not found"); return
    await db.update_order_status(oid, "approved")
    car = await db.get_car(o[1])
    try:
        await bot.send_message(o[2], t("am", "approved",
                             car=car[1] if car else "-", ticket=o[4]))
    except Exception as e:
        log.error(e)
    try:
        await cb.message.edit_caption(
            caption=(cb.message.caption or "") + "\n\n✅ ጸድቋል",
            reply_markup=None)
    except Exception: pass
    await cb.answer("Approved ✅")

@dp.callback_query(F.data.startswith("adm:no:"))
async def adm_no(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in cfg.ADMIN_IDS:
        await cb.answer("❌ ፈቃድ የለዎትም", show_alert=True); return
    oid = int(cb.data.split(":")[2])
    await state.update_data(rej_oid=oid)
    await state.set_state(RejectFSM.reason)
    await cb.message.reply("የመመለሻ ምክንያት ይጻፉ / Sababa deebii barreessi:")
    await cb.answer()

@dp.message(RejectFSM.reason, F.text)
async def adm_rej_reason(msg: Message, state: FSMContext):
    d = await state.get_data()
    oid = d.get("rej_oid"); await state.clear()
    o = await db.get_order(oid)
    if not o: await msg.answer("Order not found"); return
    await db.update_order_status(oid, "rejected", msg.text.strip())
    try:
        await bot.send_message(o[2], t("am", "rejected", reason=msg.text.strip()))
    except Exception as e: log.error(e)
    await msg.answer(f"❌ Order #{oid} ተመልሷል።")

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
        if time.time() - int(ts) > 7 * 86400: return False
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
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#0f1419;color:#e7e9ea;line-height:1.5}
a{color:#1d9bf0;text-decoration:none}
a:hover{text-decoration:underline}
.nav{background:#16191d;border-bottom:1px solid #2f3336;padding:14px 24px;
display:flex;justify-content:space-between;align-items:center}
.nav h1{font-size:18px;color:#1d9bf0}
.nav .links a{margin-left:20px;color:#e7e9ea;font-weight:500}
.wrap{max-width:1200px;margin:24px auto;padding:0 20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:14px;margin-bottom:24px}
.stat{background:#16191d;border:1px solid #2f3336;border-radius:12px;padding:16px}
.stat .lbl{font-size:12px;color:#71767b;text-transform:uppercase;
letter-spacing:.5px}
.stat .val{font-size:26px;font-weight:700;margin-top:6px;color:#1d9bf0}
.card{background:#16191d;border:1px solid #2f3336;border-radius:12px;
padding:20px;margin-bottom:20px}
.card h2{font-size:16px;margin-bottom:14px;color:#e7e9ea}
table{width:100%;border-collapse:collapse}
th,td{padding:10px 12px;text-align:left;font-size:13px;
border-bottom:1px solid #2f3336}
th{color:#71767b;font-weight:600;text-transform:uppercase;font-size:11px}
tr:hover{background:#1a1d22}
.btn{display:inline-block;padding:8px 16px;border-radius:20px;border:none;
font-size:13px;font-weight:600;cursor:pointer;background:#1d9bf0;color:#fff}
.btn:hover{background:#1a8cd8;text-decoration:none}
.btn.r{background:#f4212e}.btn.r:hover{background:#d61b28}
.btn.g{background:#00ba7c}.btn.g:hover{background:#00a06b}
.btn.s{padding:5px 12px;font-size:12px}
input,textarea,select{width:100%;padding:10px 12px;border-radius:8px;
background:#0f1419;border:1px solid #2f3336;color:#e7e9ea;font-size:14px;
font-family:inherit;margin-bottom:12px}
input:focus,textarea:focus,select:focus{outline:none;border-color:#1d9bf0}
label{display:block;font-size:12px;color:#71767b;margin-bottom:6px;
font-weight:600}
.badge{padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600}
.badge.pending{background:#5c4a00;color:#ffd400}
.badge.approved{background:#003d24;color:#00ba7c}
.badge.rejected{background:#3d0008;color:#f4212e}
.login{max-width:380px;margin:80px auto;background:#16191d;padding:32px;
border-radius:16px;border:1px solid #2f3336}
.login h1{text-align:center;margin-bottom:24px;color:#1d9bf0}
.actions{display:flex;gap:6px}
.filters{display:flex;gap:10px;align-items:center;margin-bottom:16px;
flex-wrap:wrap}
.filters select,.filters input{margin-bottom:0;width:auto;min-width:160px}
.filters .btn{margin-bottom:0}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.form-grid .full{grid-column:1/-1}
@media(max-width:600px){.form-grid{grid-template-columns:1fr}}
</style>
"""

def layout(title, body, active=""):
    def link(href, text, key):
        cls = 'style="color:#1d9bf0"' if key == active else ""
        return f'<a href="{href}" {cls}>{text}</a>'
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>{CSS}</head><body>
<div class="nav">
  <h1>🚗 Car Equb Admin</h1>
  <div class="links">
    {link('/admin','Dashboard','dash')}
    {link('/admin/cars','Cars','cars')}
    {link('/admin/orders','Orders','orders')}
    <a href="/admin/logout" style="color:#f4212e">Logout</a>
  </div>
</div>
<div class="wrap">{body}</div>
</body></html>"""

async def login_get(req):
    err = req.query.get("err", "")
    msg = ('<p style="color:#f4212e;text-align:center;margin-bottom:14px">'
           '❌ የተሳሳተ የይለፍ ቃል</p>') if err else ""
    return web.Response(text=f"""<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login</title>{CSS}</head><body>
<div class="login"><h1>🚗 Admin Login</h1>{msg}
<form method="POST" action="/admin/login">
<label>Password</label>
<input type="password" name="pw" required autofocus>
<button class="btn" style="width:100%">Login</button>
</form></div></body></html>""", content_type="text/html")

async def login_post(req):
    data = await req.post()
    if data.get("pw") == cfg.ADMIN_PASSWORD:
        r = web.HTTPFound("/admin")
        r.set_cookie("auth", make_token(), max_age=7*86400,
                     httponly=True, samesite="Lax")
        raise r
    raise web.HTTPFound("/admin/login?err=1")

async def logout(req):
    r = web.HTTPFound("/admin/login")
    r.del_cookie("auth")
    raise r

async def dash(req):
    g = await db.global_stats()
    cars = await db.list_cars(active_only=False)
    car_rows = ""
    for c in cars:
        s = await db.car_stats(c[0])
        car_rows += f"""<tr>
        <td>#{c[0]}</td><td>{c[1]}</td><td>{c[3]} ብር</td>
        <td>{c[4]}–{c[5]}</td>
        <td>{s['approved']} ✅ / {s['pending']} ⏳</td>
        <td>{s['remaining']} 🟢 / {s['total']}</td>
        <td>{'✅' if c[7] else '❌'}</td></tr>"""
    body = f"""
    <div class="grid">
      <div class="stat"><div class="lbl">Users</div>
      <div class="val">{g['users']}</div></div>
      <div class="stat"><div class="lbl">Active Cars</div>
      <div class="val">{g['cars']}</div></div>
      <div class="stat"><div class="lbl">Pending</div>
      <div class="val">{g['pending']}</div></div>
      <div class="stat"><div class="lbl">Approved</div>
      <div class="val">{g['approved']}</div></div>
      <div class="stat"><div class="lbl">Rejected</div>
      <div class="val">{g['rejected']}</div></div>
    </div>
    <div class="card"><h2>🚗 Cars Overview</h2>
    <table><thead><tr><th>ID</th><th>Name</th><th>Price</th>
    <th>Tickets</th><th>Approved/Pending</th><th>Remaining</th>
    <th>Active</th></tr></thead><tbody>{car_rows}</tbody></table></div>"""
    return web.Response(text=layout("Dashboard", body, "dash"),
                        content_type="text/html")

async def cars_list(req):
    cars = await db.list_cars(active_only=False)
    rows = ""
    for c in cars:
        s = await db.car_stats(c[0])
        rows += f"""<tr>
        <td>#{c[0]}</td><td>{c[1]}</td><td>{c[3]} ብር</td>
        <td>{c[4]}–{c[5]}</td><td>{c[6] or '-'}</td>
        <td>{s['taken']}/{s['total']}</td>
        <td>{'✅' if c[7] else '❌'}</td>
        <td class="actions">
          <a class="btn s" href="/admin/cars/{c[0]}">Edit</a>
          <form method="POST" action="/admin/cars/{c[0]}/del"
          style="display:inline" onsubmit="return confirm('Delete?')">
          <button class="btn s r">Del</button></form>
        </td></tr>"""
    body = f"""
    <div class="card"><h2>➕ Add New Car</h2>
    <form method="POST" action="/admin/cars/add">
      <div class="form-grid">
        <div><label>Name</label><input name="name" required></div>
        <div><label>Price (ብር)</label>
        <input name="price" type="number" required value="500"></div>
        <div><label>Ticket Min</label>
        <input name="tmin" type="number" value="1"></div>
        <div><label>Ticket Max</label>
        <input name="tmax" type="number" value="4000"></div>
        <div><label>Closing Date</label>
        <input name="closing" placeholder="30/12/2026"></div>
        <div class="full"><label>Description</label>
        <textarea name="desc" rows="2"></textarea></div>
      </div>
      <button class="btn">➕ Add Car</button>
    </form></div>
    <div class="card"><h2>🚗 All Cars</h2>
    <table><thead><tr><th>ID</th><th>Name</th><th>Price</th>
    <th>Range</th><th>Closing</th><th>Taken</th><th>Active</th><th>Actions</th>
    </tr></thead><tbody>{rows}</tbody></table></div>"""
    return web.Response(text=layout("Cars", body, "cars"),
                        content_type="text/html")

async def car_add(req):
    d = await req.post()
    await db.add_car(
        d.get("name", "").strip(), d.get("desc", "").strip(),
        int(d.get("price", 500) or 500),
        int(d.get("tmin", 1) or 1),
        int(d.get("tmax", 4000) or 4000),
        d.get("closing", "").strip())
    raise web.HTTPFound("/admin/cars")

async def car_edit_get(req):
    cid = int(req.match_info["id"])
    c = await db.get_car(cid)
    if not c: raise web.HTTPFound("/admin/cars")
    body = f"""
    <div class="card"><h2>✏️ Edit Car #{cid}</h2>
    <form method="POST" action="/admin/cars/{cid}">
      <div class="form-grid">
        <div><label>Name</label>
        <input name="name" value="{c[1]}" required></div>
        <div><label>Price</label>
        <input name="price" type="number" value="{c[3]}"></div>
        <div><label>Ticket Min</label>
        <input name="tmin" type="number" value="{c[4]}"></div>
        <div><label>Ticket Max</label>
        <input name="tmax" type="number" value="{c[5]}"></div>
        <div><label>Closing</label>
        <input name="closing" value="{c[6] or ''}"></div>
        <div><label>Active</label>
          <select name="active">
            <option value="1" {'selected' if c[7] else ''}>Yes</option>
            <option value="0" {'' if c[7] else 'selected'}>No</option>
          </select></div>
        <div class="full"><label>Description</label>
        <textarea name="desc" rows="2">{c[2] or ''}</textarea></div>
      </div>
      <button class="btn">💾 Save</button>
      <a href="/admin/cars" class="btn"
      style="background:#2f3336">Cancel</a>
    </form></div>"""
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
        int(d.get("active", 1)))
    raise web.HTTPFound("/admin/cars")

async def car_del(req):
    cid = int(req.match_info["id"])
    await db.delete_car(cid)
    raise web.HTTPFound("/admin/cars")

async def orders_list(req):
    car_id = req.query.get("car_id", "")
    status = req.query.get("status", "")
    car_filter = int(car_id) if car_id.isdigit() else None
    status_filter = status if status in ("pending", "approved", "rejected") else None

    cars = await db.list_cars(active_only=False)
    car_opts = '<option value="">All Cars</option>'
    for c in cars:
        sel = "selected" if car_filter == c[0] else ""
        car_opts += f'<option value="{c[0]}" {sel}>#{c[0]} {c[1]}</option>'
    st_opts = '<option value="">All Status</option>'
    for s in ("pending", "approved", "rejected"):
        sel = "selected" if status_filter == s else ""
        st_opts += f'<option value="{s}" {sel}>{s.title()}</option>'

    orders = await db.list_orders(car_id=car_filter, status=status_filter, limit=300)
    rows = ""
    for o in orders:
        oid, cid, uid, tno, name, phone, tx, shot, st, reason, created, carname = o
        actions = ""
        if st == "pending":
            actions = f"""
            <form method="POST" action="/admin/orders/{oid}/ok"
            style="display:inline">
              <button class="btn s g">✅</button></form>
            <form method="POST" action="/admin/orders/{oid}/no"
             style="display:inline"
             onsubmit="var r=prompt('Reason:');this.reason.value=r||'';
             return r!==null">
              <input type="hidden" name="reason">
              <button class="btn s r">❌</button></form>
            """
        rows += f"""<tr>
          <td>#{oid}</td>
          <td>{carname or '-'}</td>
          <td><a href="https://t.me/user?id={uid}" target="_blank">{name}</a><br>
              <small style="color:#71767b">{uid}</small></td>
          <td>{tno}</td><td>{phone}</td>
          <td><code>{tx}</code></td>
          <td>{'📸' if shot else '-'}</td>
          <td><span class="badge {st}">{st}</span>
              {f'<br><small>{reason}</small>' if reason else ''}</td>
          <td>{created[:16]}</td>
          <td class="actions">{actions}</td>
        </tr>"""

    body = f"""
    <div class="card">
      <form class="filters" method="GET">
        <select name="car_id">{car_opts}</select>
        <select name="status">{st_opts}</select>
        <button class="btn">Filter</button>
        <a class="btn" style="background:#2f3336" href="/admin/orders">Reset</a>
      </form>
      <table><thead><tr><th>ID</th><th>Car</th><th>User</th><th>Ticket</th>
      <th>Phone</th><th>TX</th><th>Shot</th><th>Status</th><th>Date</th>
      <th>Actions</th></tr></thead><tbody>{rows or
      '<tr><td colspan="10" style="text-align:center;color:#71767b;padding:20px">No orders</td></tr>'}</tbody></table>
    </div>"""
    return web.Response(text=layout("Orders", body, "orders"),
                        content_type="text/html")

async def order_ok(req):
    oid = int(req.match_info["id"])
    o = await db.get_order(oid)
    if o and o[8] != "approved":
        await db.update_order_status(oid, "approved")
        car = await db.get_car(o[1])
        try:
            await bot.send_message(o[2], t("am", "approved",
                car=car[1] if car else "-", ticket=o[4]))
        except Exception as e: log.error(e)
    raise web.HTTPFound(req.headers.get("Referer", "/admin/orders"))

async def order_no(req):
    oid = int(req.match_info["id"])
    d = await req.post()
    reason = (d.get("reason") or "").strip() or "ያልተገለጸ"
    o = await db.get_order(oid)
    if o:
        await db.update_order_status(oid, "rejected", reason)
        try:
            await bot.send_message(o[2], t("am", "rejected", reason=reason))
        except Exception as e: log.error(e)
    raise web.HTTPFound(req.headers.get("Referer", "/admin/orders"))

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
    return app

async def on_startup():
    await db.init_db()
    if cfg.USE_WEBHOOK:
        url = f"{cfg.WEBHOOK_URL}{cfg.WEBHOOK_PATH}"
        await bot.set_webhook(url, secret_token=cfg.WEBHOOK_SECRET,
                              drop_pending_updates=True)
        log.info(f"✅ Webhook set: {url}")
    else:
        log.info("⚠️ WEBHOOK_URL አልተዋቀረም — polling mode")

async def on_shutdown():
    if cfg.USE_WEBHOOK:
        try: await bot.delete_webhook()
        except Exception: pass

def main():
    if not cfg.BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN is missing")

    app = build_web()

    if cfg.USE_WEBHOOK:
        SimpleRequestHandler(dispatcher=dp, bot=bot,
                             secret_token=cfg.WEBHOOK_SECRET
                             ).register(app, path=cfg.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        app.on_startup.append(lambda _: on_startup())
        app.on_cleanup.append(lambda _: on_shutdown())
        log.info(f"🚀 Listening on {cfg.HOST}:{cfg.PORT} (webhook)")
        web.run_app(app, host=cfg.HOST, port=cfg.PORT, print=None)
    else:
        async def run_poll():
            await db.init_db()
            log.info("🤖 Polling mode started")
            await dp.start_polling(bot)
        asyncio.run(run_poll())

if __name__ == "__main__":
    main()
