import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "equb.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            lang TEXT DEFAULT 'am',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            ticket_min INTEGER DEFAULT 1,
            ticket_max INTEGER DEFAULT 4000,
            closing_date TEXT,
            active INTEGER DEFAULT 1,
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER,
            user_id INTEGER,
            ticket_no INTEGER,
            full_name TEXT,
            phone TEXT,
            screenshot_id TEXT,
            status TEXT DEFAULT 'held',
            reason TEXT,
            held_until TIMESTAMP,
            reminder_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.commit()
        
        # Migrations (add columns if missing)
        try:
            await db.execute("ALTER TABLE cars ADD COLUMN image TEXT")
            await db.commit()
        except Exception: pass
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN reminder_sent INTEGER DEFAULT 0")
            await db.commit()
        except Exception: pass

        async with db.execute("SELECT COUNT(*) FROM cars") as c:
            if (await c.fetchone())[0] == 0:
                await db.execute("""
                    INSERT INTO cars(name, description, price,
                    ticket_min, ticket_max, closing_date, active, image)
                    VALUES(?,?,?,?,?,?,1,?)
                """, ("Toyota Corolla 2020", "የመጀመሪያ መኪና",
                      500, 1, 4000, "30/12/2026", ""))
                await db.commit()

# ---------- USERS ----------
async def get_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (uid,)) as c:
            return await c.fetchone()

async def save_user(uid, username, full_name, lang="am"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users(user_id, username, full_name, lang) VALUES(?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username, full_name=excluded.full_name
        """, (uid, username, full_name, lang))
        await db.commit()

async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as c:
            return [row[0] for row in await c.fetchall()]

async def get_users_by_car(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT DISTINCT user_id FROM orders
            WHERE car_id=? AND status IN ('pending','approved','held')
        """, (car_id,)) as c:
            return [row[0] for row in await c.fetchall()]

# ---------- CARS ----------
async def list_cars(active_only=True):
    async with aiosqlite.connect(DB_PATH) as db:
        q = "SELECT id,name,description,price,ticket_min,ticket_max,closing_date,active,image FROM cars"
        if active_only:
            q += " WHERE active=1"
        q += " ORDER BY id DESC"
        async with db.execute(q) as c:
            return await c.fetchall()

async def get_car(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM cars WHERE id=?", (car_id,)) as c:
            return await c.fetchone()

async def add_car(name, desc, price, tmin, tmax, closing, image=""):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO cars(name,description,price,ticket_min,ticket_max,closing_date,active,image)
            VALUES(?,?,?,?,?,?,1,?)
        """, (name, desc, price, tmin, tmax, closing, image))
        await db.commit()
        return cur.lastrowid

async def update_car(car_id, name, desc, price, tmin, tmax, closing, active, image=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE cars SET name=?,description=?,price=?,ticket_min=?,ticket_max=?,
            closing_date=?,active=?,image=? WHERE id=?
        """, (name, desc, price, tmin, tmax, closing, active, image, car_id))
        await db.commit()

async def delete_car(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cars WHERE id=?", (car_id,))
        await db.execute("DELETE FROM orders WHERE car_id=?", (car_id,))
        await db.commit()

# ---------- TICKETS ----------
async def _cleanup_expired(db):
    now = datetime.now().isoformat()
    await db.execute("""
        UPDATE orders SET status='released'
        WHERE status='held' AND held_until IS NOT NULL AND held_until < ?
    """, (now,))
    await db.commit()

async def taken_numbers(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute("""
            SELECT ticket_no FROM orders
            WHERE car_id=? AND status IN ('held','pending','approved','blocked')
        """, (car_id,)) as c:
            return {row[0] for row in await c.fetchall()}

async def is_ticket_available(car_id, ticket_no):
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute("""
            SELECT 1 FROM orders
            WHERE car_id=? AND ticket_no=?
            AND status IN ('held','pending','approved','blocked')
            LIMIT 1
        """, (car_id, ticket_no)) as c:
            return (await c.fetchone()) is None

async def hold_ticket(car_id, user_id, ticket_no, minutes=15):
    if not await is_ticket_available(car_id, ticket_no):
        return None
    until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO orders(car_id,user_id,ticket_no,status,held_until)
            VALUES(?,?,?, 'held', ?)
        """, (car_id, user_id, ticket_no, until))
        await db.commit()
        return cur.lastrowid

async def release_order(oid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status='released', held_until=NULL WHERE id=?",
            (oid,))
        await db.commit()

async def block_range(car_id, n_from, n_to, reason=""):
    async with aiosqlite.connect(DB_PATH) as db:
        inserted = 0
        for n in range(n_from, n_to + 1):
            async with db.execute("""
                SELECT 1 FROM orders WHERE car_id=? AND ticket_no=?
                AND status IN ('held','pending','approved','blocked') LIMIT 1
            """, (car_id, n)) as c:
                if await c.fetchone():
                    continue
            await db.execute("""
                INSERT INTO orders(car_id,user_id,ticket_no,status,reason)
                VALUES(?,NULL,?, 'blocked', ?)
            """, (car_id, n, reason))
            inserted += 1
        await db.commit()
        return inserted

async def confirm_hold(oid, full_name, phone, screenshot_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET full_name=?, phone=?, screenshot_id=?,
            status='pending', held_until=NULL
            WHERE id=? AND status='held'
        """, (full_name, phone, screenshot_id, oid))
        await db.commit()

async def get_order(oid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM orders WHERE id=?", (oid,)) as c:
            return await c.fetchone()

async def update_order_status(oid, status, reason=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status=?, reason=?, held_until=NULL WHERE id=?",
            (status, reason, oid))
        await db.commit()

async def user_orders(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute("""
            SELECT o.id, o.ticket_no, o.status, c.name FROM orders o
            LEFT JOIN cars c ON c.id=o.car_id
            WHERE o.user_id=? AND o.status NOT IN ('released')
            ORDER BY o.id DESC
        """, (uid,)) as c:
            return await c.fetchall()

async def list_orders(car_id=None, status=None, limit=200):
    q = """SELECT o.id,o.car_id,o.user_id,o.ticket_no,o.full_name,o.phone,
           o.screenshot_id,o.status,o.reason,o.created_at,c.name
           FROM orders o LEFT JOIN cars c ON c.id=o.car_id WHERE 1=1"""
    params = []
    if car_id:
        q += " AND o.car_id=?"; params.append(car_id)
    if status:
        q += " AND o.status=?"; params.append(status)
    else:
        q += " AND o.status NOT IN ('released')"
    q += " ORDER BY o.id DESC LIMIT ?"; params.append(limit)
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute(q, params) as c:
            return await c.fetchall()

async def car_stats(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute(
            "SELECT ticket_min,ticket_max FROM cars WHERE id=?", (car_id,)
        ) as c:
            row = await c.fetchone()
        if not row:
            return {"total":0,"taken":0,"remaining":0,
                    "approved":0,"pending":0,"held":0,"blocked":0}
        tmin, tmax = row
        async with db.execute("""
            SELECT status, COUNT(*) FROM orders
            WHERE car_id=? AND status NOT IN ('released')
            GROUP BY status
        """, (car_id,)) as c:
            rows = await c.fetchall()
        counts = {s: n for s, n in rows}
        approved = counts.get("approved", 0)
        pending = counts.get("pending", 0)
        held = counts.get("held", 0)
        blocked = counts.get("blocked", 0)
        total = tmax - tmin + 1
        taken = approved + pending + held + blocked
        return {
            "total": total, "taken": taken, "remaining": total - taken,
            "approved": approved, "pending": pending,
            "held": held, "blocked": blocked
        }

async def global_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM cars WHERE active=1") as c:
            cars = (await c.fetchone())[0]
        async with db.execute("""
            SELECT status,COUNT(*) FROM orders
            WHERE status NOT IN ('released') GROUP BY status
        """) as c:
            rows = await c.fetchall()
        counts = {s: n for s, n in rows}
        return {
            "users": users, "cars": cars,
            "pending": counts.get("pending", 0),
            "approved": counts.get("approved", 0),
            "held": counts.get("held", 0),
            "blocked": counts.get("blocked", 0),
        }

# ---------- REMINDERS (Feature 8) ----------
async def get_expiring_holds():
    """የሚያልቁ የተያዙ ቲኬቶች (ከ1 ደቂቃ በታች) ያመጣል"""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now()
        threshold = (now + timedelta(minutes=1)).isoformat()
        async with db.execute("""
            SELECT id, user_id, ticket_no, held_until FROM orders
            WHERE status='held' AND reminder_sent=0
            AND held_until <= ?
        """, (threshold,)) as c:
            return await c.fetchall()

async def mark_reminder_sent(oid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET reminder_sent=1 WHERE id=?", (oid,))
        await db.commit()
