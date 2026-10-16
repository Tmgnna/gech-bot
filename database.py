import aiosqlite

DB_PATH = "equb.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            lang TEXT DEFAULT 'am'
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER,
            user_id INTEGER,
            ticket_no INTEGER,
            full_name TEXT,
            phone TEXT,
            tx_ref TEXT,
            screenshot_id TEXT,
            status TEXT DEFAULT 'pending',
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_ticket_approved
        ON orders(car_id, ticket_no) WHERE status='approved';
        """)
        await db.commit()

        async with db.execute("SELECT COUNT(*) FROM cars") as c:
            if (await c.fetchone())[0] == 0:
                await db.execute("""
                    INSERT INTO cars(name, description, price,
                    ticket_min, ticket_max, closing_date, active)
                    VALUES(?,?,?,?,?,?,1)
                """, ("Toyota Corolla 2020", "የመጀመሪያ መኪና",
                      500, 1, 4000, "30/12/2026"))
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

async def set_lang(uid, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, uid))
        await db.commit()

# ---------- CARS ----------
async def list_cars(active_only=True):
    async with aiosqlite.connect(DB_PATH) as db:
        q = "SELECT id,name,description,price,ticket_min,ticket_max,closing_date,active FROM cars"
        if active_only:
            q += " WHERE active=1"
        q += " ORDER BY id DESC"
        async with db.execute(q) as c:
            return await c.fetchall()

async def get_car(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM cars WHERE id=?", (car_id,)) as c:
            return await c.fetchone()

async def add_car(name, desc, price, tmin, tmax, closing):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO cars(name,description,price,ticket_min,ticket_max,closing_date,active)
            VALUES(?,?,?,?,?,?,1)
        """, (name, desc, price, tmin, tmax, closing))
        await db.commit()
        return cur.lastrowid

async def update_car(car_id, name, desc, price, tmin, tmax, closing, active):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE cars SET name=?,description=?,price=?,ticket_min=?,ticket_max=?,
            closing_date=?,active=? WHERE id=?
        """, (name, desc, price, tmin, tmax, closing, active, car_id))
        await db.commit()

async def delete_car(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cars WHERE id=?", (car_id,))
        await db.commit()

# ---------- ORDERS ----------
async def create_order(car_id, uid, ticket_no, name, phone, tx, screenshot):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO orders(car_id,user_id,ticket_no,full_name,phone,tx_ref,screenshot_id)
            VALUES(?,?,?,?,?,?,?)
        """, (car_id, uid, ticket_no, name, phone, tx, screenshot))
        await db.commit()
        return cur.lastrowid

async def is_ticket_taken(car_id, ticket_no):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT 1 FROM orders WHERE car_id=? AND ticket_no=?
            AND status IN ('approved','pending')
        """, (car_id, ticket_no)) as c:
            return await c.fetchone() is not None

async def get_order(oid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM orders WHERE id=?", (oid,)) as c:
            return await c.fetchone()

async def update_order_status(oid, status, reason=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status=?, reason=? WHERE id=?",
            (status, reason, oid))
        await db.commit()

async def user_orders(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT o.id, o.ticket_no, o.status, c.name FROM orders o
            LEFT JOIN cars c ON c.id=o.car_id
            WHERE o.user_id=? ORDER BY o.id DESC
        """, (uid,)) as c:
            return await c.fetchall()

async def list_orders(car_id=None, status=None, limit=200):
    q = """SELECT o.id,o.car_id,o.user_id,o.ticket_no,o.full_name,o.phone,
           o.tx_ref,o.screenshot_id,o.status,o.reason,o.created_at,c.name
           FROM orders o LEFT JOIN cars c ON c.id=o.car_id WHERE 1=1"""
    params = []
    if car_id:
        q += " AND o.car_id=?"; params.append(car_id)
    if status:
        q += " AND o.status=?"; params.append(status)
    q += " ORDER BY o.id DESC LIMIT ?"; params.append(limit)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(q, params) as c:
            return await c.fetchall()

async def car_stats(car_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ticket_min,ticket_max FROM cars WHERE id=?", (car_id,)
        ) as c:
            row = await c.fetchone()
        if not row:
            return {"total":0,"taken":0,"remaining":0,
                    "approved":0,"pending":0,"rejected":0}
        tmin, tmax = row
        async with db.execute("""
            SELECT status, COUNT(*) FROM orders WHERE car_id=? GROUP BY status
        """, (car_id,)) as c:
            rows = await c.fetchall()
        counts = {s: n for s, n in rows}
        approved = counts.get("approved", 0)
        pending = counts.get("pending", 0)
        rejected = counts.get("rejected", 0)
        total = tmax - tmin + 1
        taken = approved + pending
        return {
            "total": total, "taken": taken, "remaining": total - taken,
            "approved": approved, "pending": pending, "rejected": rejected
        }

async def global_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM cars WHERE active=1") as c:
            cars = (await c.fetchone())[0]
        async with db.execute(
            "SELECT status,COUNT(*) FROM orders GROUP BY status"
        ) as c:
            rows = await c.fetchall()
        counts = {s: n for s, n in rows}
        return {
            "users": users, "cars": cars,
            "pending": counts.get("pending", 0),
            "approved": counts.get("approved", 0),
            "rejected": counts.get("rejected", 0),
        }
