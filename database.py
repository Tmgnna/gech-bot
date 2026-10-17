"""SQLite data layer with safe ticket reservations and non-destructive car removal."""
import os
import aiosqlite
from datetime import datetime, timedelta

DB_PATH = os.getenv("DATABASE_PATH", "equb.db")
ACTIVE_TICKET_STATUSES = ("held", "pending", "approved", "blocked")
VALID_ORDER_STATUSES = {"held", "pending", "approved", "rejected", "blocked", "released"}

async def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute("PRAGMA busy_timeout=30000")
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
            lang TEXT DEFAULT 'am', joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            description TEXT, price INTEGER NOT NULL CHECK(price >= 0),
            ticket_min INTEGER NOT NULL DEFAULT 1, ticket_max INTEGER NOT NULL DEFAULT 4000,
            closing_date TEXT, active INTEGER NOT NULL DEFAULT 1,
            image TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK(ticket_min >= 0 AND ticket_max >= ticket_min)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, car_id INTEGER,
            user_id INTEGER, ticket_no INTEGER, full_name TEXT, phone TEXT,
            screenshot_id TEXT, status TEXT NOT NULL DEFAULT 'held', reason TEXT,
            held_until TIMESTAMP, reminder_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_orders_car_status ON orders(car_id,status);
        CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders(user_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_orders_hold_until ON orders(status,held_until);
        CREATE INDEX IF NOT EXISTS idx_cars_active ON cars(active);
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL DEFAULT 'system',
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
        """)
        # Versionless additive migrations: inspect columns before adding them.
        async with db.execute("PRAGMA table_info(cars)") as cur:
            car_columns = {r[1] for r in await cur.fetchall()}
        if "image" not in car_columns:
            await db.execute("ALTER TABLE cars ADD COLUMN image TEXT")
        async with db.execute("PRAGMA table_info(orders)") as cur:
            order_columns = {r[1] for r in await cur.fetchall()}
        if "reminder_sent" not in order_columns:
            await db.execute("ALTER TABLE orders ADD COLUMN reminder_sent INTEGER DEFAULT 0")
        await db.commit()
        async with db.execute("SELECT COUNT(*) FROM cars") as cur:
            if (await cur.fetchone())[0] == 0:
                await db.execute("""INSERT INTO cars(name,description,price,ticket_min,ticket_max,closing_date,active,image)
                    VALUES(?,?,?,?,?,?,1,?)""",
                    ("Toyota Corolla 2020", "የመጀመሪያ መኪና", 500, 1, 4000, "30/12/2026", ""))
                await db.commit()

async def get_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (uid,)) as c: return await c.fetchone()

async def save_user(uid, username, full_name, lang="am"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO users(user_id,username,full_name,lang) VALUES(?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,full_name=excluded.full_name""", (uid, username, full_name, lang))
        await db.commit()

async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users ORDER BY user_id") as c: return [r[0] for r in await c.fetchall()]

async def get_users_by_car(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT user_id FROM orders WHERE car_id=? AND user_id IS NOT NULL AND status IN ('pending','approved','held')", (car_id,)) as c: return [r[0] for r in await c.fetchall()]

async def list_cars(active_only=True):
    q = "SELECT id,name,description,price,ticket_min,ticket_max,closing_date,active,image FROM cars"
    if active_only: q += " WHERE active=1"
    q += " ORDER BY id DESC"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(q) as c: return await c.fetchall()

async def get_car(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM cars WHERE id=?", (car_id,)) as c: return await c.fetchone()

async def add_car(name, desc, price, tmin, tmax, closing, image=""):
    if not name.strip() or int(price) < 0 or int(tmin) < 0 or int(tmax) < int(tmin): raise ValueError("Invalid car details")
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        cur = await db.execute("INSERT INTO cars(name,description,price,ticket_min,ticket_max,closing_date,active,image) VALUES(?,?,?,?,?,?,1,?)", (name.strip(), desc, int(price), int(tmin), int(tmax), closing, image))
        await db.commit(); return cur.lastrowid

async def update_car(car_id, name, desc, price, tmin, tmax, closing, active, image=""):
    if not name.strip() or int(price) < 0 or int(tmin) < 0 or int(tmax) < int(tmin): raise ValueError("Invalid car details")
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        await db.execute("UPDATE cars SET name=?,description=?,price=?,ticket_min=?,ticket_max=?,closing_date=?,active=?,image=? WHERE id=?", (name.strip(), desc, int(price), int(tmin), int(tmax), closing, int(bool(active)), image, car_id)); await db.commit()

async def delete_car(car_id):
    """Soft-delete: preserve historical orders and prevent new purchases."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE cars SET active=0 WHERE id=?", (car_id,))
        await db.execute("INSERT INTO audit_logs(actor,action,entity_type,entity_id,details) VALUES('web_admin','car_deactivated','car',?,'Car marked inactive; history preserved')", (car_id,))
        await db.commit()

async def _cleanup_expired(db):
    now = datetime.now().isoformat()
    await db.execute("UPDATE orders SET status='released',held_until=NULL WHERE status='held' AND held_until IS NOT NULL AND held_until < ?", (now,))

async def taken_numbers(car_id):
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        await _cleanup_expired(db)
        async with db.execute("SELECT ticket_no FROM orders WHERE car_id=? AND status IN ('held','pending','approved','blocked')", (car_id,)) as c: result = {r[0] for r in await c.fetchall()}
        await db.commit(); return result

async def is_ticket_available(car_id, ticket_no):
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        await _cleanup_expired(db)
        async with db.execute("SELECT ticket_min,ticket_max,active FROM cars WHERE id=?", (car_id,)) as c: car = await c.fetchone()
        if not car or not car[2] or ticket_no < car[0] or ticket_no > car[1]: await db.commit(); return False
        async with db.execute("SELECT 1 FROM orders WHERE car_id=? AND ticket_no=? AND status IN ('held','pending','approved','blocked') LIMIT 1", (car_id, ticket_no)) as c: exists = await c.fetchone()
        await db.commit(); return exists is None

async def hold_ticket(car_id, user_id, ticket_no, minutes=15):
    """Reserve a ticket under BEGIN IMMEDIATE so concurrent requests cannot double-book."""
    until = (datetime.now() + timedelta(minutes=max(1, int(minutes)))).isoformat()
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        await db.execute("PRAGMA busy_timeout=30000")
        await db.execute("BEGIN IMMEDIATE")
        try:
            await _cleanup_expired(db)
            async with db.execute("SELECT ticket_min,ticket_max,active FROM cars WHERE id=?", (car_id,)) as c: car = await c.fetchone()
            if not car or not car[2] or ticket_no < car[0] or ticket_no > car[1]:
                await db.rollback(); return None
            async with db.execute("SELECT 1 FROM orders WHERE car_id=? AND ticket_no=? AND status IN ('held','pending','approved','blocked') LIMIT 1", (car_id, ticket_no)) as c: exists = await c.fetchone()
            if exists:
                await db.rollback(); return None
            cur = await db.execute("INSERT INTO orders(car_id,user_id,ticket_no,status,held_until) VALUES(?,?,?,'held',?)", (car_id, user_id, ticket_no, until))
            await db.commit(); return cur.lastrowid
        except Exception:
            await db.rollback(); raise

async def release_order(oid, user_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id is None:
            cur = await db.execute("UPDATE orders SET status='released',held_until=NULL WHERE id=? AND status IN ('held','blocked')", (oid,))
            actor = "web_admin"
        else:
            cur = await db.execute("UPDATE orders SET status='released',held_until=NULL WHERE id=? AND user_id=? AND status='held'", (oid, user_id))
            actor = f"telegram_user:{user_id}"
        if cur.rowcount:
            await db.execute("INSERT INTO audit_logs(actor,action,entity_type,entity_id,details) VALUES(?, 'order_released','order',?,'Ticket released')", (actor, oid))
        await db.commit(); return cur.rowcount > 0

async def block_range(car_id, n_from, n_to, reason=""):
    if n_from > n_to: raise ValueError("Range start must be <= range end")
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        await db.execute("BEGIN IMMEDIATE"); inserted = 0
        try:
            await _cleanup_expired(db)
            async with db.execute("SELECT ticket_min,ticket_max,active FROM cars WHERE id=?", (car_id,)) as c: car = await c.fetchone()
            if not car or not car[2] or n_from < car[0] or n_to > car[1]: await db.rollback(); return 0
            for n in range(n_from, n_to + 1):
                async with db.execute("SELECT 1 FROM orders WHERE car_id=? AND ticket_no=? AND status IN ('held','pending','approved','blocked') LIMIT 1", (car_id, n)) as c:
                    if await c.fetchone(): continue
                await db.execute("INSERT INTO orders(car_id,user_id,ticket_no,status,reason) VALUES(?,NULL,?,'blocked',?)", (car_id, n, reason)); inserted += 1
            await db.commit(); return inserted
        except Exception: await db.rollback(); raise

async def confirm_hold(oid, full_name, phone, screenshot_id, user_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id is None:
            cur = await db.execute("UPDATE orders SET full_name=?,phone=?,screenshot_id=?,status='pending',held_until=NULL WHERE id=? AND status='held'", (full_name, phone, screenshot_id, oid))
        else:
            cur = await db.execute("UPDATE orders SET full_name=?,phone=?,screenshot_id=?,status='pending',held_until=NULL WHERE id=? AND user_id=? AND status='held'", (full_name, phone, screenshot_id, oid, user_id))
        await db.commit(); return cur.rowcount > 0

async def get_order(oid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM orders WHERE id=?", (oid,)) as c: return await c.fetchone()

async def update_order_status(oid, status, reason=None, expected_status=None, actor="system"):
    if status not in VALID_ORDER_STATUSES: raise ValueError("Invalid order status")
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT status FROM orders WHERE id=?", (oid,)) as c: old = await c.fetchone()
        if expected_status:
            cur = await db.execute("UPDATE orders SET status=?,reason=?,held_until=NULL WHERE id=? AND status=?", (status, reason, oid, expected_status))
        else:
            cur = await db.execute("UPDATE orders SET status=?,reason=?,held_until=NULL WHERE id=?", (status, reason, oid))
        if cur.rowcount and old and old[0] != status:
            details = f"status:{old[0]}->{status}" + (f"; reason:{reason[:250]}" if reason else "")
            await db.execute("INSERT INTO audit_logs(actor,action,entity_type,entity_id,details) VALUES(?, 'order_status_changed','order',?,?)", (actor, oid, details))
        await db.commit(); return cur.rowcount > 0

async def user_orders(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute("SELECT o.id,o.ticket_no,o.status,c.name FROM orders o LEFT JOIN cars c ON c.id=o.car_id WHERE o.user_id=? AND o.status NOT IN ('released') ORDER BY o.id DESC", (uid,)) as c: rows = await c.fetchall()
        await db.commit(); return rows

async def list_orders(car_id=None, status=None, limit=200):
    q = "SELECT o.id,o.car_id,o.user_id,o.ticket_no,o.full_name,o.phone,o.screenshot_id,o.status,o.reason,o.created_at,c.name FROM orders o LEFT JOIN cars c ON c.id=o.car_id WHERE 1=1"; params=[]
    if car_id is not None: q += " AND o.car_id=?"; params.append(car_id)
    if status: q += " AND o.status=?"; params.append(status)
    else: q += " AND o.status NOT IN ('released')"
    q += " ORDER BY o.id DESC LIMIT ?"; params.append(max(1,min(int(limit),1000)))
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute(q, params) as c: rows = await c.fetchall()
        await db.commit(); return rows

async def car_stats(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute("SELECT ticket_min,ticket_max FROM cars WHERE id=?", (car_id,)) as c: car = await c.fetchone()
        if not car: await db.commit(); return {"total":0,"taken":0,"remaining":0,"approved":0,"pending":0,"held":0,"blocked":0}
        async with db.execute("SELECT status,COUNT(*) FROM orders WHERE car_id=? AND status IN ('held','pending','approved','blocked') GROUP BY status", (car_id,)) as c: rows = await c.fetchall()
        await db.commit(); counts=dict(rows); total=car[1]-car[0]+1
        taken=sum(counts.get(s,0) for s in ACTIVE_TICKET_STATUSES)
        return {"total":total,"taken":taken,"remaining":max(0,total-taken),"approved":counts.get('approved',0),"pending":counts.get('pending',0),"held":counts.get('held',0),"blocked":counts.get('blocked',0)}

async def list_audit_logs(limit=200):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id,actor,action,entity_type,entity_id,details,created_at FROM audit_logs ORDER BY id DESC LIMIT ?", (max(1, min(int(limit), 1000)),)) as c:
            return await c.fetchall()

async def global_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        await _cleanup_expired(db)
        async with db.execute("SELECT COUNT(*) FROM users") as c: users=(await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM cars WHERE active=1") as c: cars=(await c.fetchone())[0]
        async with db.execute("SELECT status,COUNT(*) FROM orders WHERE status IN ('held','pending','approved','blocked') GROUP BY status") as c: rows=await c.fetchall()
        async with db.execute("SELECT COALESCE(SUM(c.price),0) FROM orders o JOIN cars c ON c.id=o.car_id WHERE o.status='approved'") as c: revenue=(await c.fetchone())[0]
        await db.commit(); counts=dict(rows)
        return {"users":users,"cars":cars,"pending":counts.get('pending',0),"approved":counts.get('approved',0),"held":counts.get('held',0),"blocked":counts.get('blocked',0),"approved_revenue":revenue}

async def get_expiring_holds():
    async with aiosqlite.connect(DB_PATH) as db:
        threshold=(datetime.now()+timedelta(minutes=1)).isoformat()
        async with db.execute("SELECT id,user_id,ticket_no,held_until FROM orders WHERE status='held' AND reminder_sent=0 AND held_until<=?", (threshold,)) as c: return await c.fetchall()

async def mark_reminder_sent(oid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET reminder_sent=1 WHERE id=?", (oid,)); await db.commit()
