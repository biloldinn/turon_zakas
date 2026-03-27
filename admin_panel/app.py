from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import os
import sys

# BASE_DIR should be turon_bot/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from bot.database import (
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
    db_path = os.path.join(BASE_DIR, "turon_bot.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return Admin(user[0], user[1], user[3])
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        db_path = os.path.join(BASE_DIR, "turon_bot.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            admin = Admin(user[0], user[1], user[3])
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
    return render_template("dashboard.html", stats=stats, workers_ranking=workers_ranking)

@app.route("/services")
@login_required
def services():
    services = get_all_services(active_only=False)
    return render_template("services.html", services=services)

@app.route("/add_service", methods=["POST"])
@login_required
def add_service_route():
    name = request.form["name"]
    description = request.form["description"]
    price = float(request.form["price"])
    duration = int(request.form["duration"])
    category = request.form["category"]
    
    add_service(name, description, price, duration, category)
    flash("Xizmat qo‘shildi!")
    return redirect(url_for("services"))

@app.route("/update_service/<int:service_id>", methods=["POST"])
@login_required
def update_service_route(service_id):
    name = request.form["name"]
    description = request.form["description"]
    price = float(request.form["price"])
    duration = int(request.form["duration"])
    category = request.form["category"]
    is_active = 1 if "is_active" in request.form else 0
    
    update_service(service_id, name, description, price, duration, category, is_active)
    flash("Xizmat yangilandi!")
    return redirect(url_for("services"))

@app.route("/delete_service/<int:service_id>")
@login_required
def delete_service_route(service_id):
    delete_service(service_id)
    flash("Xizmat o‘chirildi!")
    return redirect(url_for("services"))

@app.route("/workers")
@login_required
def workers():
    workers = get_all_workers()
    return render_template("workers.html", workers=workers)

@app.route("/add_worker", methods=["POST"])
@login_required
def add_worker_route():
    telegram_id = int(request.form["telegram_id"])
    username = request.form["username"]
    full_name = request.form["full_name"]
    phone = request.form["phone"]
    
    add_worker(telegram_id, username, full_name, phone)
    flash("Hodim qo‘shildi!")
    return redirect(url_for("workers"))

@app.route("/remove_worker/<int:telegram_id>")
@login_required
def remove_worker_route(telegram_id):
    remove_worker(telegram_id)
    flash("Hodim o‘chirildi!")
    return redirect(url_for("workers"))

@app.route("/orders")
@login_required
def orders():
    all_orders = get_all_orders()
    workers = get_all_workers()
    return render_template("orders.html", orders=all_orders, workers=workers)

@app.route("/assign_order/<int:order_id>", methods=["POST"])
@login_required
def assign_order_route(order_id):
    worker_id = int(request.form["worker_id"])
    assign_order_to_worker(order_id, worker_id)
    flash("Buyurtma hodimga biriktirildi!")
    return redirect(url_for("orders"))

@app.route("/confirm_pay/<int:order_id>")
@login_required
def confirm_pay_route(order_id):
    update_order_payment_status(order_id, "confirmed")
    flash("To‘lov tasdiqlandi!")
    return redirect(url_for("orders"))

@app.route("/statistics")
@login_required
def statistics():
    stats = get_statistics()
    workers_ranking = get_workers_ranking()
    return render_template("statistics.html", stats=stats, workers_ranking=workers_ranking)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
