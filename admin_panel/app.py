from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import sys

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BASE_DIR should be turon_bot/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

logger.info("Admin Panel starting with BASE_DIR: %s", BASE_DIR)

from database import (
    get_all_services, add_service, update_service, delete_service,
    get_all_workers, add_worker, remove_worker,
    get_all_orders, get_statistics, get_workers_ranking,
    assign_order_to_worker, update_order_payment_status, get_user_by_telegram_id
)

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
    from bot.database import get_admin_by_id
    user = get_admin_by_id(user_id)
    if user:
        return Admin(str(user['_id']), user['username'], user.get('role', 'admin'))
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        from bot.database import get_admin_user
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
    recent_orders = get_all_orders()[:5] # OXIRGI 5TA BUYURTMA
    return render_template("dashboard.html", 
                         stats=stats, 
                         workers_ranking=workers_ranking,
                         recent_orders=recent_orders)

@app.route("/services")
@login_required
def services():
    services = get_all_services(active_only=False)
    return render_template("services.html", services=services)

@app.route("/workers")
@login_required
def workers():
    workers = get_all_workers()
    # Har bir hodim uchun reytingdan statistika olish (ixtiyoriy, lekin asosiysi hamma chiqadi)
    return render_template("workers.html", workers=workers)

@app.route("/orders")
@login_required
def orders():
    all_orders = get_all_orders()
    workers = get_all_workers()
    return render_template("orders.html", orders=all_orders, workers=workers)

@app.route("/statistics")
@login_required
def statistics():
    stats = get_statistics()
    workers_ranking = get_workers_ranking()
    return render_template("statistics.html", stats=stats, workers_ranking=workers_ranking)

@app.route("/confirm_pay/<int:order_id>")
@login_required
def confirm_pay_route(order_id):
    update_order_payment_status(order_id, "confirmed")
    flash("To‘lov tasdiqlandi!")
    return redirect(url_for("orders"))

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
# ... 
@app.route("/receipts/<path:filename>")
def get_receipt(filename):
    # run/receipts/ papkasidan olishi kerak
    receipt_dir = os.path.join(BASE_DIR, "run", "receipts")
    return send_from_directory(receipt_dir, filename)

@app.route("/voice_notes/<path:filename>")
def get_voice(filename):
    # run/voice_notes/ papkasidan olishi kerak
    voice_dir = os.path.join(BASE_DIR, "run", "voice_notes")
    return send_from_directory(voice_dir, filename)

@app.route("/api/ping")
def ping():
    try:
        from database import client
        client.admin.command('ping')
        return jsonify({
            "status": "online",
            "message": "pong",
            "db": "connected",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error("Healthcheck failed: %s", str(e))
        return jsonify({
            "status": "degraded",
            "message": "Database connection error",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("--- TURON ADMIN PANEL STARTING ---")
    logger.info("Listening on port: %s", port)
    app.run(host="0.0.0.0", port=port, debug=False)
