import pymongo
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from config import MONGODB_URI, DATABASE_NAME

client = pymongo.MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]

def init_db():
    """MongoDB indekslarini yaratish (Sync)"""
    db.users.create_index("telegram_id", unique=True)
    db.orders.create_index("order_number", unique=True)
    db.admin_users.create_index("username", unique=True)
    db.worker_stats.create_index([("worker_id", 1), ("date", 1)], unique=True)
    
    # Check if default admin exists
    admin = db.admin_users.find_one({"username": "admin"})
    if not admin:
        db.admin_users.insert_one({
            "username": "admin",
            "password": "admin123",
            "role": "superadmin",
            "created_at": datetime.now()
        })

# ============ USER FUNKSIYALARI ============

def get_or_create_user(telegram_id, username=None, full_name=None):
    user = db.users.find_one({"telegram_id": telegram_id})
    if not user:
        new_user = {
            "telegram_id": telegram_id,
            "username": username,
            "full_name": full_name,
            "phone": None,
            "role": "user",
            "is_active": True,
            "created_at": datetime.now()
        }
        db.users.insert_one(new_user)
        user = db.users.find_one({"telegram_id": telegram_id})
    return user

def get_user_by_telegram_id(telegram_id):
    return db.users.find_one({"telegram_id": telegram_id})

def get_all_workers():
    workers = list(db.users.find({"role": "worker", "is_active": True}))
    return workers

def add_worker(telegram_id, username, full_name, phone):
    db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": {
            "username": username,
            "full_name": full_name,
            "phone": phone,
            "role": "worker",
            "is_active": True
        }},
        upsert=True
    )

def remove_worker(telegram_id):
    db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"role": "user", "is_active": False}}
    )

# ============ SERVICE FUNKSIYALARI ============

def get_all_services(active_only=True):
    query = {"is_active": True} if active_only else {}
    services = list(db.services.find(query).sort("created_at", 1))
    for s in services:
        s['id'] = str(s['_id'])
    return services

def get_service_by_id(service_id):
    try:
        service = db.services.find_one({"_id": ObjectId(service_id)})
        if service:
            service['id'] = str(service['_id'])
        return service
    except:
        return None

def add_service(name, description, price, duration, category):
    db.services.insert_one({
        "name": name,
        "description": description,
        "price": float(price),
        "duration": int(duration),
        "category": category,
        "is_active": True,
        "created_at": datetime.now()
    })

def update_service(service_id, name, description, price, duration, category, is_active):
    db.services.update_one(
        {"_id": ObjectId(service_id)},
        {"$set": {
            "name": name,
            "description": description,
            "price": float(price),
            "duration": int(duration),
            "category": category,
            "is_active": bool(is_active)
        }}
    )

def delete_service(service_id):
    db.services.delete_one({"_id": ObjectId(service_id)})

# ============ ORDER FUNKSIYALARI ============

def get_all_orders():
    orders = list(db.orders.find().sort("created_at", -1))
    for o in orders:
        o['id'] = str(o['_id'])
        if o.get('worker_id'):
            worker = db.users.find_one({"telegram_id": o['worker_id']})
            o['worker_name'] = worker['full_name'] if worker else "Noma'lum"
    return orders

def update_order_payment_status(order_id, status, receipt_url=None):
    update_data = {"payment_status": status}
    if receipt_url:
        update_data["receipt_url"] = receipt_url
    
    db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": update_data}
    )

def assign_order_to_worker(order_id, worker_id):
    db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"worker_id": worker_id, "status": "accepted", "accepted_at": datetime.now()}}
    )

# ============ STATISTIKA ============

def get_statistics():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_orders = db.orders.count_documents({"created_at": {"$gte": today}})
    
    pipeline = [
        {"$match": {"created_at": {"$gte": today}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
    ]
    today_res = list(db.orders.aggregate(pipeline))
    today_amount = today_res[0]['total'] if today_res else 0

    pending = db.orders.count_documents({"payment_status": "pending"})
    in_progress = db.orders.count_documents({"status": {"$in": ["accepted", "in_progress"]}})

    return {
        "today_orders": today_orders,
        "today_amount": today_amount,
        "monthly_orders": 0,
        "monthly_amount": 0,
        "pending_payments": pending,
        "in_progress_orders": in_progress
    }

def get_workers_ranking():
    pipeline = [
        {"$group": {
            "_id": "$worker_id", 
            "total_orders": {"$sum": 1},
            "total_amount": {"$sum": "$total_price"}
        }},
        {"$sort": {"total_amount": -1}}
    ]
    results = list(db.orders.aggregate(pipeline))
    
    ranking = []
    for res in results:
        if res['_id']:
            worker = db.users.find_one({"telegram_id": res['_id']})
            if worker:
                ranking.append({
                    "full_name": worker['full_name'],
                    "total_orders": res['total_orders'],
                    "total_amount": res['total_amount'],
                    "phone": worker.get('phone', ''),
                    "is_active": worker.get('is_active', True)
                })
    return ranking

def get_admin_user(username, password):
    return db.admin_users.find_one({"username": username, "password": password})

def get_admin_by_id(user_id):
    try:
        return db.admin_users.find_one({"_id": ObjectId(user_id)})
    except:
        return None

# ============ YANGILIKLAR VA E'LONLAR ============

def get_all_news(limit=10):
    news = list(db.news.find().sort("created_at", -1).limit(limit))
    for item in news:
        item['id'] = str(item['_id'])
    return news

def add_news(title, content, author="Admin"):
    return db.news.insert_one({
        "title": title,
        "content": content,
        "author": author,
        "created_at": datetime.now()
    })

def delete_news(news_id):
    try:
        db.news.delete_one({"_id": ObjectId(news_id)})
        return True
    except:
        return False
