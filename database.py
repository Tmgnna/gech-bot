"""PostgreSQL data layer with connection pooling and safe reservations."""
import os
import asyncpg
from datetime import datetime, timedelta

# የ Supabase Connection String (ከ .env ይመጣል)
DATABASE_URL = os.getenv("DATABASE_URL", "")
ACTIVE_TICKET_STATUSES = ("held", "pending", "approved", "blocked")
VALID_ORDER_STATUSES = {"held", "pending", "approved", "rejected", "blocked", "released"}

# Global connection pool
pool = None

async def init_db():
    global pool
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in environment variables")
    
    # Supabase pooler (port 6543) ስለሆነ statement_cache_size=0 ማድረግ ግዴታ ነው
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10, statement_cache_size=0)
    
    async with pool.acquire() as conn:
        # ሰንጠረዦችን መፍጠር (PostgreSQL Syntax)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY, username TEXT, full_name TEXT,
            lang TEXT DEFAULT 'am', joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            saved_name TEXT, saved_phone TEXT
        );
        CREATE TABLE IF NOT EXISTS cars (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL,
            description TEXT, price INTEGER NOT NULL CHECK(price >= 0),
            ticket_min INTEGER NOT NULL DEFAULT 1, ticket_max INTEGER NOT NULL DEFAULT 4000,
            closing_date TEXT, active INTEGER NOT NULL DEFAULT 1,
            image TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK(ticket_min >= 0 AND ticket_max >= ticket_min)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY, car_id INTEGER,
            user_id BIGINT, ticket_no INTEGER, full_name TEXT, phone TEXT,
            screenshot_id TEXT, status TEXT NOT NULL DEFAULT 'held', reason TEXT,
            held_until TIMESTAMP, reminder_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_orders_car_status ON orders(car_id,status);
        CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders(user_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_orders_hold_until ON orders(status,held_until);
        CREATE INDEX IF NOT EXISTS idx_cars_active ON cars(active);
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            actor TEXT NOT NULL DEFAULT 'system',
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
        """)
        
        # የመጀመሪያ መኪና መፍጠር
        count = await conn.fetchval("SELECT COUNT(*) FROM cars")
        if count == 0:
            await conn.execute("""INSERT INTO cars(name,description,price,ticket_min,ticket_max,closing_date,active,image)
                VALUES($1,$2,$3,$4,$5,$6,1,$7)""",
                "Toyota Corolla 2020", "የመጀመሪያ መኪና", 500, 1, 4000, "30/12/2026", "")

async def get_user(uid):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", uid)

async def save_user(uid, username, full_name, lang="am"):
    async with pool.acquire() as conn:
        await conn.execute("""INSERT INTO users(user_id,username,full_name,lang) VALUES($1,$2,$3,$4)
            ON CONFLICT(user_id) DO UPDATE SET username=EXCLUDED.username,full_name=EXCLUDED.full_name""", 
            uid, username, full_name, lang)

async def save_profile(uid, name, phone):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET saved_name=$1, saved_phone=$2 WHERE user_id=$3",
            name.strip(), phone.strip(), uid)

async def get_profile(uid):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT saved_name, saved_phone FROM users WHERE user_id=$1", uid)
        return (row['saved_name'], row['saved_phone']) if row else (None, None)

async def get_all_user_ids():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users ORDER BY user_id")
        return [r['user_id'] for r in rows]

async def get_users_by_car(car_id):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT user_id FROM orders WHERE car_id=$1 AND user_id IS NOT NULL AND status IN ('pending','approved','held')", car_id)
        return [r['user_id'] for r in rows]

async def list_cars(active_only=True):
    q = "SELECT id,name,description,price,ticket_min,ticket_max,closing_date,active,image FROM cars"
    if active_only: q += " WHERE active=1"
    q += " ORDER BY id DESC"
    async with pool.acquire() as conn:
        return await conn.fetch(q)

async def get_car(car_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM cars WHERE id=$1", car_id)

async def add_car(name, desc, price, tmin, tmax, closing, image=""):
    if not name.strip() or int(price) < 0 or int(tmin) < 0 or int(tmax) < int(tmin): 
        raise ValueError("Invalid car details")
    async with pool.acquire() as conn:
        return await conn.fetchval("""INSERT INTO cars(name,description,price,ticket_min,ticket_max,closing_date,active,image) 
            VALUES($1,$2,$3,$4,$5,$6,1,$7) RETURNING id""", name.strip(), desc, int(price), int(tmin), int(tmax), closing, image)

async def update_car(car_id, name, desc, price, tmin, tmax, closing, active, image=""):
    if not name.strip() or int(price) < 0 or int(tmin) < 0 or int(tmax) < int(tmin): 
        raise ValueError("Invalid car details")
    async with pool.acquire() as conn:
        await conn.execute("""UPDATE cars SET name=$1,description=$2,price=$3,ticket_min=$4,ticket_max=$5,
            closing_date=$6,active=$7,image=$8 WHERE id=$9""", 
            name.strip(), desc, int(price), int(tmin), int(tmax), closing, int(bool(active)), image, car_id)

async def delete_car(car_id):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE cars SET active=0 WHERE id=$1", car_id)
        await conn.execute("""INSERT INTO audit_logs(actor,action,entity_type,entity_id,details) 
            VALUES('web_admin','car_deactivated','car',$1,'Car marked inactive; history preserved')""", car_id)

async def _cleanup_expired(conn):
    now = datetime.now()
    await conn.execute("UPDATE orders SET status='released',held_until=NULL WHERE status='held' AND held_until IS NOT NULL AND held_until < $1", now)

async def taken_numbers(car_id):
    async with pool.acquire() as conn:
        await _cleanup_expired(conn)
        rows = await conn.fetch("SELECT ticket_no FROM orders WHERE car_id=$1 AND status IN ('held','pending','approved','blocked')", car_id)
        return {r['ticket_no'] for r in rows}

async def is_ticket_available(car_id, ticket_no):
    async with pool.acquire() as conn:
        await _cleanup_expired(conn)
        car = await conn.fetchrow("SELECT ticket_min,ticket_max,active FROM cars WHERE id=$1", car_id)
        if not car or not car['active'] or ticket_no < car['ticket_min'] or ticket_no > car['ticket_max']:
            return False
        exists = await conn.fetchval("SELECT 1 FROM orders WHERE car_id=$1 AND ticket_no=$2 AND status IN ('held','pending','approved','blocked') LIMIT 1", car_id, ticket_no)
        return exists is None

async def hold_ticket(car_id, user_id, ticket_no, minutes=15):
    until = datetime.now() + timedelta(minutes=max(1, int(minutes)))
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _cleanup_expired(conn)
            car = await conn.fetchrow("SELECT ticket_min,ticket_max,active FROM cars WHERE id=$1 FOR UPDATE", car_id)
            if not car or not car['active'] or ticket_no < car['ticket_min'] or ticket_no > car['ticket_max']:
                return None
            exists = await conn.fetchval("SELECT 1 FROM orders WHERE car_id=$1 AND ticket_no=$2 AND status IN ('held','pending','approved','blocked') LIMIT 1", car_id, ticket_no)
            if exists:
                return None
            oid = await conn.fetchval("""INSERT INTO orders(car_id,user_id,ticket_no,status,held_until) 
                VALUES($1,$2,$3,'held',$4) RETURNING id""", car_id, user_id, ticket_no, until)
            return oid

async def release_order(oid, user_id=None):
    async with pool.acquire() as conn:
        if user_id is None:
            rowcount = await conn.execute("UPDATE orders SET status='released',held_until=NULL WHERE id=$1 AND status IN ('held','blocked')", oid)
            actor = "web_admin"
        else:
            rowcount = await conn.execute("UPDATE orders SET status='released',held_until=NULL WHERE id=$1 AND user_id=$2 AND status='held'", oid, user_id)
            actor = f"telegram_user:{user_id}"
        
        if "UPDATE 1" in rowcount:
            await conn.execute("INSERT INTO audit_logs(actor,action,entity_type,entity_id,details) VALUES($1,'order_released','order',$2,'Ticket released')", actor, oid)
            return True
        return False

async def block_range(car_id, n_from, n_to, reason=""):
    if n_from > n_to: raise ValueError("Range start must be <= range end")
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _cleanup_expired(conn)
            car = await conn.fetchrow("SELECT ticket_min,ticket_max,active FROM cars WHERE id=$1", car_id)
            if not car or not car['active'] or n_from < car['ticket_min'] or n_to > car['ticket_max']:
                return 0
            inserted = 0
            for n in range(n_from, n_to + 1):
                exists = await conn.fetchval("SELECT 1 FROM orders WHERE car_id=$1 AND ticket_no=$2 AND status IN ('held','pending','approved','blocked') LIMIT 1", car_id, n)
                if not exists:
                    await conn.execute("INSERT INTO orders(car_id,user_id,ticket_no,status,reason) VALUES($1,NULL,$2,'blocked',$3)", car_id, n, reason)
                    inserted += 1
            return inserted

async def confirm_hold(oid, full_name, phone, screenshot_id, user_id=None):
    async with pool.acquire() as conn:
        if user_id is None:
            rowcount = await conn.execute("UPDATE orders SET full_name=$1,phone=$2,screenshot_id=$3,status='pending',held_until=NULL WHERE id=$4 AND status='held'", full_name, phone, screenshot_id, oid)
        else:
            rowcount = await conn.execute("UPDATE orders SET full_name=$1,phone=$2,screenshot_id=$3,status='pending',held_until=NULL WHERE id=$4 AND user_id=$5 AND status='held'", full_name, phone, screenshot_id, oid, user_id)
        return "UPDATE 1" in rowcount

async def get_order(oid):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM orders WHERE id=$1", oid)

async def update_order_status(oid, status, reason=None, expected_status=None, actor="system"):
    if status not in VALID_ORDER_STATUSES: raise ValueError("Invalid order status")
    async with pool.acquire() as conn:
        old = await conn.fetchrow("SELECT status FROM orders WHERE id=$1", oid)
        if expected_status:
            rowcount = await conn.execute("UPDATE orders SET status=$1,reason=$2,held_until=NULL WHERE id=$3 AND status=$4", status, reason, oid, expected_status)
        else:
            rowcount = await conn.execute("UPDATE orders SET status=$1,reason=$2,held_until=NULL WHERE id=$3", status, reason, oid)
        
        if "UPDATE 1" in rowcount and old and old['status'] != status:
            details = f"status:{old['status']}->{status}" + (f"; reason:{reason[:250]}" if reason else "")
            await conn.execute("INSERT INTO audit_logs(actor,action,entity_type,entity_id,details) VALUES($1,'order_status_changed','order',$2,$3)", actor, oid, details)
        return "UPDATE 1" in rowcount

async def user_orders(uid):
    async with pool.acquire() as conn:
        await _cleanup_expired(conn)
        return await conn.fetch("""SELECT o.id,o.ticket_no,o.status,c.name FROM orders o 
            LEFT JOIN cars c ON c.id=o.car_id WHERE o.user_id=$1 AND o.status NOT IN ('released') ORDER BY o.id DESC""", uid)

async def list_orders(car_id=None, status=None, limit=200):
    q = """SELECT o.id,o.car_id,o.user_id,o.ticket_no,o.full_name,o.phone,
         o.screenshot_id,o.status,o.reason,o.created_at,c.name 
         FROM orders o LEFT JOIN cars c ON c.id=o.car_id WHERE 1=1"""
    params = []
    idx = 1
    if car_id is not None:
        q += f" AND o.car_id=${idx}"; params.append(car_id); idx += 1
    if status:
        q += f" AND o.status=${idx}"; params.append(status); idx += 1
    else:
        q += " AND o.status NOT IN ('released')"
    q += f" ORDER BY o.id DESC LIMIT ${idx}"
    params.append(max(1, min(int(limit), 1000)))
    
    async with pool.acquire() as conn:
        await _cleanup_expired(conn)
        return await conn.fetch(q, *params)

async def car_stats(car_id):
    async with pool.acquire() as conn:
        await _cleanup_expired(conn)
        car = await conn.fetchrow("SELECT ticket_min,ticket_max FROM cars WHERE id=$1", car_id)
        if not car:
            return {"total": 0, "taken": 0, "remaining": 0, "approved": 0, "pending": 0, "held": 0, "blocked": 0}
        
        rows = await conn.fetch("SELECT status,COUNT(*) as c FROM orders WHERE car_id=$1 AND status IN ('held','pending','approved','blocked') GROUP BY status", car_id)
        counts = {r['status']: r['c'] for r in rows}
        total = car['ticket_max'] - car['ticket_min'] + 1
        taken = sum(counts.get(s, 0) for s in ACTIVE_TICKET_STATUSES)
        return {"total": total, "taken": taken, "remaining": max(0, total - taken),
                "approved": counts.get('approved', 0), "pending": counts.get('pending', 0),
                "held": counts.get('held', 0), "blocked": counts.get('blocked', 0)}

async def list_audit_logs(limit=200):
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT id,actor,action,entity_type,entity_id,details,created_at FROM audit_logs ORDER BY id DESC LIMIT $1", max(1, min(int(limit), 1000)))

async def global_stats():
    async with pool.acquire() as conn:
        await _cleanup_expired(conn)
        users = await conn.fetchval("SELECT COUNT(*) FROM users")
        cars = await conn.fetchval("SELECT COUNT(*) FROM cars WHERE active=1")
        rows = await conn.fetch("SELECT status,COUNT(*) as c FROM orders WHERE status IN ('held','pending','approved','blocked') GROUP BY status")
        revenue = await conn.fetchval("SELECT COALESCE(SUM(c.price),0) FROM orders o JOIN cars c ON c.id=o.car_id WHERE o.status='approved'")
        
        counts = {r['status']: r['c'] for r in rows}
        return {"users": users, "cars": cars,
                "pending": counts.get('pending', 0), "approved": counts.get('approved', 0),
                "held": counts.get('held', 0), "blocked": counts.get('blocked', 0),
                "approved_revenue": revenue}

async def get_expiring_holds():
    async with pool.acquire() as conn:
        threshold = datetime.now() + timedelta(minutes=1)
        return await conn.fetch("SELECT id,user_id,ticket_no,held_until FROM orders WHERE status='held' AND reminder_sent=0 AND held_until<=$1", threshold)

async def mark_reminder_sent(oid):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE orders SET reminder_sent=1 WHERE id=$1", oid)
