from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import sys
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory and root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from database import (
        client, init_db, get_all_services, add_service, update_service, delete_service,
        get_all_workers, add_worker, remove_worker,
        get_all_orders, get_statistics, get_workers_ranking,
        assign_order_to_worker, update_order_payment_status, get_user_by_telegram_id,
        get_all_news, add_news, delete_news, get_admin_user, get_admin_by_id
    )
    init_db()  # Initialize indexes and default admin
    logger.info("Successfully imported database functions and initialized DB")
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Handle error or exit
    sys.exit(1)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "turon_secret_key_2026")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class Admin(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user = get_admin_by_id(user_id)
    if user:
        return Admin(str(user['_id']), user['username'], user.get('role', 'admin'))
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_admin_user(username, password)
        if user:
            admin = Admin(str(user['_id']), user['username'], user.get('role', 'admin'))
            login_user(admin)
            return redirect(url_for("dashboard"))
        else:
            flash("Login yoki parol xato!")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    stats = get_statistics()
    workers_ranking = get_workers_ranking()
    recent_orders = get_all_orders()[:5]
    latest_news = get_all_news(limit=3)
    return render_template("dashboard.html", 
                          stats=stats, 
                          workers_ranking=workers_ranking,
                          recent_orders=recent_orders,
                          latest_news=latest_news)

@app.route("/services")
@login_required
def services():
    services = get_all_services(active_only=False)
    return render_template("services.html", services=services)

@app.route("/workers")
@login_required
def workers():
    workers_list = get_workers_ranking() # This has balance and rating
    return render_template("workers.html", workers=workers_list)

@app.route("/orders")
@login_required
def orders():
    all_orders = get_all_orders()
    workers_list = get_all_workers()
    return render_template("orders.html", orders=all_orders, workers=workers_list)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        open_time = request.form.get("open_time", "09:00")
        close_time = request.form.get("close_time", "18:00")
        work_days = request.form.get("work_days", "Dushanba - Shanba")
        new_settings = {
            "phone": request.form.get("phone"),
            "address": request.form.get("address"),
            "open_time": open_time,
            "close_time": close_time,
            "work_days": work_days,
            "work_hours": f"{open_time} - {close_time}",
            "card_number": request.form.get("card_number"),
            "card_owner": request.form.get("card_owner")
        }
        update_settings(new_settings)
        flash("Sozlamalar muvaffaqiyatli saqlandi!")
        return redirect(url_for("settings"))
    
    current_settings = get_settings()
    return render_template("settings.html", settings=current_settings)

@app.route("/news", methods=["GET", "POST"])
@login_required
def news_manage():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        image_url = request.form.get("image_url") # Direct URL or simple text for now
        
        if title and content:
            add_news(title, content, current_user.username, image_url)
            flash("Yangilik muvaffaqiyatli qo'shildi va botga yuborildi!")
        return redirect(url_for("news_manage"))
    all_news = get_all_news()
    return render_template("news.html", news=all_news)

@app.route("/news/delete/<news_id>")
@login_required
def news_delete(news_id):
    if delete_news(news_id):
        flash("Yangilik o'chirildi.")
    else:
        flash("Xatolik yuz berdi.")
    return redirect(url_for("news_manage"))

@app.route("/statistics")
@login_required
def statistics():
    stats = get_statistics()
    workers_ranking = get_workers_ranking()
    return render_template("statistics.html", stats=stats, workers_ranking=workers_ranking)

@app.route("/confirm_pay/<order_id>")
@login_required
def confirm_pay_route(order_id):
    update_order_payment_status(order_id, "confirmed")
    flash("To‘lov tasdiqlandi!")
    return redirect(url_for("orders"))

@app.route("/cancel_pay/<order_id>")
@login_required
def cancel_pay_route(order_id):
    update_order_payment_status(order_id, "cancelled")
    flash("To‘lov bekor qilindi!")
    return redirect(url_for("orders"))

@app.route("/orders/assign", methods=["POST"])
@login_required
def assign_worker():
    order_id = request.form.get("order_id")
    worker_id = request.form.get("worker_id")
    
    if order_id and worker_id:
        assign_order_to_worker(order_id, int(worker_id))
        
        # Notify the worker via Bot API
        import requests
        bot_token = os.getenv("BOT_TOKEN")
        if bot_token:
            from database import get_order_by_id
            order = get_order_by_id(order_id)
            msg_text = (
                f"🚨 <b>Sizga yangi buyurtma biriktirildi!</b>\n\n"
                f"📦 #{order['order_number']}\n"
                f"👤 Mijoz: {order['user_name']}\n"
                f"💰 Summa: {order['total_price']:,} so'm\n\n"
                f"Batafsil ma'lumot bot menyusida."
            )
            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data={
                "chat_id": worker_id,
                "text": msg_text,
                "parse_mode": "HTML"
            })
            
        flash(f"Xodim muvaffaqiyatli biriktirildi!")
    else:
        flash("Xatolik: Hodim yoki buyurtma tanlanmagan.")
        
    return redirect(url_for("orders"))

@app.route("/receipts/<path:filename>")
def get_receipt(filename):
    receipt_dir = os.path.join(BASE_DIR, "receipts")
    if not os.path.exists(receipt_dir):
        os.makedirs(receipt_dir)
    return send_from_directory(receipt_dir, filename)

@app.route("/voice_notes/<path:filename>")
def get_voice(filename):
    voice_dir = os.path.join(BASE_DIR, "voice_notes")
    if not os.path.exists(voice_dir):
        os.makedirs(voice_dir)
    return send_from_directory(voice_dir, filename)

@app.route("/order_photos/<path:filename>")
def get_order_photo(filename):
    photo_dir = os.path.join(BASE_DIR, "order_photos")
    if not os.path.exists(photo_dir):
        os.makedirs(photo_dir)
    return send_from_directory(photo_dir, filename)

@app.route("/order_docs/<path:filename>")
def get_order_doc(filename):
    doc_dir = os.path.join(BASE_DIR, "order_docs")
    if not os.path.exists(doc_dir):
        os.makedirs(doc_dir)
    return send_from_directory(doc_dir, filename)

@app.route("/api/ping")
def ping():
    try:
        # Simple ping to check if DB is alive
        client.admin.command('ping')
        return jsonify({"status": "healthy", "db": "connected"}), 200
    except Exception as e:
        logger.error(f"Healthcheck failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 200 # Return 200 so Railway doesn't kill it immediately if it's just a transient DB error

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
