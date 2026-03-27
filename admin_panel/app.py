from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
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
    return render_template("dashboard.html", stats=stats, workers_ranking=workers_ranking)

@app.route("/services")
@login_required
def services():
    services = get_all_services(active_only=False)
    return render_template("services.html", services=services)

@app.route("/workers")
@login_required
def workers():
    workers = get_workers_ranking() # Ranking contains stats too
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

@app.route("/api/ping")
def ping():
    return jsonify({"status": "ok", "message": "pong"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
