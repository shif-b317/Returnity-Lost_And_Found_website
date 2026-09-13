import os
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, abort
)

from config import Config
from database import (
    query_db, execute_db, log_audit, create_notification, init_admin_user
)
from verification import evaluate_claim, find_potential_matches

# Initialize Flask Application
app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.EVIDENCE_FOLDER, exist_ok=True)

# ----------------------------------------------------------
# Helper Functions & Decorators
# ----------------------------------------------------------

def allowed_file(filename, allowed_extensions):
    """Check if the filename has an authorized extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_extensions

def save_uploaded_file(file_storage, destination_folder, allowed_extensions):
    """Save an uploaded file with a secure unique filename and return the relative path."""
    if not file_storage or file_storage.filename == "":
        return None

    if not allowed_file(file_storage.filename, allowed_extensions):
        return None

    original_name = secure_filename(file_storage.filename)
    ext = original_name.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex[:16]}_{int(datetime.now().timestamp())}.{ext}"
    target_path = Path(destination_folder) / unique_filename
    file_storage.save(target_path)
    return unique_filename

def login_required(f):
    """Decorator requiring authenticated user session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator requiring authenticated administrator session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Administrator authentication required.", "warning")
            return redirect(url_for("admin_login"))
        if session.get("user_role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global_context():
    """Inject globally available template variables."""
    unread_notifications = 0
    if "user_id" in session:
        notif_row = query_db(
            "SELECT COUNT(*) AS total FROM notifications WHERE user_id = %s AND is_read = 0",
            (session["user_id"],),
            one=True
        )
        if notif_row:
            unread_notifications = notif_row["total"]
    return {
        "unread_notifications_count": unread_notifications,
        "current_year": datetime.now().year
    }

# ----------------------------------------------------------
# Public Routes
# ----------------------------------------------------------

@app.route("/")
def index():
    """Homepage: provides overview, search quick bar, and recent active listings."""
    categories = query_db("SELECT * FROM categories ORDER BY name ASC")

    # Fetch recent active items across lost and found
    sql = """
        (SELECT id, 'lost' AS item_type, item_name, description, date_lost AS event_date,
                location_lost AS location, safe_image_path, status, created_at, category_id
         FROM lost_items
         WHERE status IN ('Active', 'Claim Pending', 'Under Verification')
         ORDER BY created_at DESC LIMIT 4)
        UNION ALL
        (SELECT id, 'found' AS item_type, item_name, description, date_found AS event_date,
                location_found AS location, safe_image_path, status, created_at, category_id
         FROM found_items
         WHERE status IN ('Active', 'Claim Pending', 'Under Verification')
         ORDER BY created_at DESC LIMIT 4)
        ORDER BY created_at DESC
        LIMIT 6
    """
    recent_items = query_db(sql)

    # Attach category names to recent items
    cat_map = {c["id"]: c["name"] for c in categories}
    for item in recent_items:
        item["category_name"] = cat_map.get(item["category_id"], "General")

    return render_template(
        "index.html",
        categories=categories,
        recent_items=recent_items,
        active_page="home"
    )

@app.route("/about")
def about():
    """About page: explains dual information division and verification workflow."""
    return render_template("about.html", active_page="about")

@app.route("/terms")
def terms():
    """Terms and Conditions page."""
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    """Privacy Policy page."""
    return render_template("privacy.html")

@app.route("/search")
def search():
    """Search and filter through active lost and found reports."""
    query = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()
    item_type = request.args.get("type", "").strip()
    location = request.args.get("location", "").strip()

    categories = query_db("SELECT * FROM categories ORDER BY name ASC")
    cat_map = {c["id"]: c["name"] for c in categories}

    conditions_lost = ["status IN ('Active', 'Claim Pending', 'Under Verification')"]
    params_lost = []

    conditions_found = ["status IN ('Active', 'Claim Pending', 'Under Verification')"]
    params_found = []

    if query:
        conditions_lost.append("(item_name LIKE %s OR description LIKE %s)")
        params_lost.extend([f"%{query}%", f"%{query}%"])
        conditions_found.append("(item_name LIKE %s OR description LIKE %s)")
        params_found.extend([f"%{query}%", f"%{query}%"])

    if category_id:
        conditions_lost.append("category_id = %s")
        params_lost.append(category_id)
        conditions_found.append("category_id = %s")
        params_found.append(category_id)

    if location:
        conditions_lost.append("location_lost LIKE %s")
        params_lost.append(f"%{location}%")
        conditions_found.append("location_found LIKE %s")
        params_found.append(f"%{location}%")

    items = []

    if item_type != "found":
        sql_lost = f"""
            SELECT id, 'lost' AS item_type, item_name, description, date_lost AS event_date,
                   location_lost AS location, safe_image_path, status, created_at, category_id
            FROM lost_items
            WHERE {' AND '.join(conditions_lost)}
            ORDER BY created_at DESC
        """
        lost_rows = query_db(sql_lost, params_lost)
        items.extend(lost_rows)

    if item_type != "lost":
        sql_found = f"""
            SELECT id, 'found' AS item_type, item_name, description, date_found AS event_date,
                   location_found AS location, safe_image_path, status, created_at, category_id
            FROM found_items
            WHERE {' AND '.join(conditions_found)}
            ORDER BY created_at DESC
        """
        found_rows = query_db(sql_found, params_found)
        items.extend(found_rows)

    # Sort all items by created_at descending
    items.sort(key=lambda x: x["created_at"], reverse=True)

    for itm in items:
        itm["category_name"] = cat_map.get(itm["category_id"], "General")

    return render_template(
        "search.html",
        items=items,
        total_results=len(items),
        categories=categories,
        query=query,
        selected_category=category_id,
        selected_type=item_type,
        selected_location=location,
        active_page="search"
    )

@app.route("/item/<item_type>/<int:item_id>")
def item_details(item_type, item_id):
    """View public information of a specific item and evaluate potential cross-matches."""
    if item_type not in ("lost", "found"):
        abort(404)

    if item_type == "lost":
        sql = """
            SELECT l.id, l.user_id, l.category_id, l.item_name, l.description, l.date_lost AS event_date,
                   l.approximate_time, l.location_lost AS location, l.safe_image_path, l.additional_info,
                   l.status, l.created_at, c.name AS category_name
            FROM lost_items l
            JOIN categories c ON l.category_id = c.id
            WHERE l.id = %s
        """
    else:
        sql = """
            SELECT f.id, f.user_id, f.category_id, f.item_name, f.description, f.date_found AS event_date,
                   f.approximate_time, f.location_found AS location, f.safe_image_path, f.additional_info,
                   f.custody_location, f.status, f.created_at, c.name AS category_name
            FROM found_items f
            JOIN categories c ON f.category_id = c.id
            WHERE f.id = %s
        """

    item = query_db(sql, (item_id,), one=True)
    if not item:
        abort(404)

    is_owner = False
    user_has_claimed = False
    if "user_id" in session:
        user_id = session["user_id"]
        if item["user_id"] == user_id:
            is_owner = True

        claim_check = query_db(
            "SELECT id FROM claims WHERE item_type = %s AND item_id = %s AND claimant_id = %s AND status != 'Rejected'",
            (item_type, item_id, user_id),
            one=True
        )
        if claim_check:
            user_has_claimed = True

    # Rule-based matching engine for suggestions
    potential_matches = find_potential_matches(item_type, item, limit=3)

    return render_template(
        "item_details.html",
        item=item,
        item_type=item_type,
        is_owner=is_owner,
        user_has_claimed=user_has_claimed,
        potential_matches=potential_matches
    )

# ----------------------------------------------------------
# Authentication Routes
# ----------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user account with Werkzeug password hashing."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not email or not password:
            flash("Please complete all required fields.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters in length.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Password confirmation does not match.", "danger")
            return render_template("register.html")

        existing_user = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
        if existing_user:
            flash("An account with this email address already exists. Please sign in.", "warning")
            return redirect(url_for("login"))

        password_hash = generate_password_hash(password, method="scrypt")
        res = execute_db(
            """
            INSERT INTO users (full_name, email, phone, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, 'user', 1)
            """,
            (full_name, email, phone, password_hash)
        )

        user_id = res["last_id"]
        session["user_id"] = user_id
        session["user_name"] = full_name
        session["user_email"] = email
        session["user_role"] = "user"

        log_audit(user_id=user_id, action="USER_REGISTRATION", notes=f"New user registered: {email}")
        create_notification(user_id, "Welcome to RETURNITY", "Your account has been successfully created. You may now log reports and submit claims.")

        flash("Registration successful. Welcome to RETURNITY!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html", active_page="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    """User login authentication."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email address or password. Please try again.", "danger")
            return render_template("login.html", active_page="login")

        if not user.get("is_active"):
            flash("This account has been deactivated. Please contact support.", "danger")
            return render_template("login.html", active_page="login")

        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]

        log_audit(user_id=user["id"], action="USER_LOGIN", notes="User logged in successfully")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    return render_template("login.html", active_page="login")

@app.route("/logout")
def logout():
    """Clear session and log out."""
    if "user_id" in session:
        log_audit(user_id=session["user_id"], action="USER_LOGOUT", notes="User logged out")
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("index"))

# ----------------------------------------------------------
# Item Reporting Routes
# ----------------------------------------------------------

@app.route("/report-lost", methods=["GET", "POST"])
@login_required
def report_lost():
    """Report a lost item with distinct public and private verification fields."""
    categories = query_db("SELECT * FROM categories ORDER BY name ASC")

    if request.method == "POST":
        item_name = request.form.get("item_name", "").strip()
        category_id = request.form.get("category_id", "").strip()
        date_lost = request.form.get("date_lost", "").strip()
        approximate_time = request.form.get("approximate_time", "").strip()
        location_lost = request.form.get("location_lost", "").strip()
        description = request.form.get("description", "").strip()
        additional_info = request.form.get("additional_info", "").strip()

        # Private verification fields
        private_identifying_detail = request.form.get("private_identifying_detail", "").strip()
        private_distinctive_characteristic = request.form.get("private_distinctive_characteristic", "").strip()
        private_contents = request.form.get("private_contents", "").strip()
        private_serial_or_id = request.form.get("private_serial_or_id", "").strip()
        private_exact_location = request.form.get("private_exact_location", "").strip()

        if not item_name or not category_id or not date_lost or not location_lost or not description or not private_identifying_detail:
            flash("Please fill in all mandatory public and private verification fields.", "danger")
            return render_template("lost.html", categories=categories, active_page="lost")

        # Handle optional image upload
        safe_image_path = None
        if "safe_image" in request.files:
            uploaded_img = request.files["safe_image"]
            if uploaded_img and uploaded_img.filename:
                safe_image_path = save_uploaded_file(
                    uploaded_img, Config.UPLOAD_FOLDER, Config.ALLOWED_IMAGE_EXTENSIONS
                )

        res = execute_db(
            """
            INSERT INTO lost_items (
                user_id, category_id, item_name, description, date_lost,
                approximate_time, location_lost, safe_image_path, additional_info,
                private_identifying_detail, private_distinctive_characteristic,
                private_contents, private_serial_or_id, private_exact_location, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active')
            """,
            (
                session["user_id"], category_id, item_name, description, date_lost,
                approximate_time, location_lost, safe_image_path, additional_info,
                private_identifying_detail, private_distinctive_characteristic,
                private_contents, private_serial_or_id, private_exact_location
            )
        )

        lost_id = res["last_id"]
        log_audit(
            item_type="lost", item_id=lost_id, user_id=session["user_id"],
            action="REPORT_LOST_ITEM", notes=f"Lost item reported: {item_name}"
        )

        flash("Lost item report logged successfully. Your private details have been encrypted.", "success")
        return redirect(url_for("item_details", item_type="lost", item_id=lost_id))

    return render_template("lost.html", categories=categories, active_page="lost")

@app.route("/report-found", methods=["GET", "POST"])
@login_required
def report_found():
    """Report a found item discovered by a community member."""
    categories = query_db("SELECT * FROM categories ORDER BY name ASC")

    if request.method == "POST":
        item_name = request.form.get("item_name", "").strip()
        category_id = request.form.get("category_id", "").strip()
        date_found = request.form.get("date_found", "").strip()
        approximate_time = request.form.get("approximate_time", "").strip()
        location_found = request.form.get("location_found", "").strip()
        description = request.form.get("description", "").strip()
        additional_info = request.form.get("additional_info", "").strip()
        custody_location = request.form.get("custody_location", "").strip()
        private_finder_notes = request.form.get("private_finder_notes", "").strip()

        if not item_name or not category_id or not date_found or not location_found or not description:
            flash("Please complete all required fields.", "danger")
            return render_template("found.html", categories=categories, active_page="found")

        safe_image_path = None
        if "safe_image" in request.files:
            uploaded_img = request.files["safe_image"]
            if uploaded_img and uploaded_img.filename:
                safe_image_path = save_uploaded_file(
                    uploaded_img, Config.UPLOAD_FOLDER, Config.ALLOWED_IMAGE_EXTENSIONS
                )

        res = execute_db(
            """
            INSERT INTO found_items (
                user_id, category_id, item_name, description, date_found,
                approximate_time, location_found, safe_image_path, additional_info,
                custody_location, private_finder_notes, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active')
            """,
            (
                session["user_id"], category_id, item_name, description, date_found,
                approximate_time, location_found, safe_image_path, additional_info,
                custody_location, private_finder_notes
            )
        )

        found_id = res["last_id"]
        log_audit(
            item_type="found", item_id=found_id, user_id=session["user_id"],
            action="REPORT_FOUND_ITEM", notes=f"Found item reported: {item_name}"
        )

        flash("Found item report successfully created. Thank you for your care.", "success")
        return redirect(url_for("item_details", item_type="found", item_id=found_id))

    return render_template("found.html", categories=categories, active_page="found")

# ----------------------------------------------------------
# Claim Verification Submissions
# ----------------------------------------------------------

@app.route("/claim/<item_type>/<int:item_id>", methods=["GET", "POST"])
@login_required
def submit_claim(item_type, item_id):
    """File an ownership verification claim against an active listing."""
    if item_type not in ("lost", "found"):
        abort(404)

    table = "lost_items" if item_type == "lost" else "found_items"
    item = query_db(f"SELECT * FROM {table} WHERE id = %s", (item_id,), one=True)
    if not item:
        abort(404)

    # Prevent owner from claiming their own reported item
    if item["user_id"] == session["user_id"]:
        flash("You cannot file an ownership claim on an item that you reported.", "warning")
        return redirect(url_for("item_details", item_type=item_type, item_id=item_id))

    # Prevent duplicate active claims by same user on same item
    existing_claim = query_db(
        "SELECT id, status FROM claims WHERE item_type = %s AND item_id = %s AND claimant_id = %s AND status NOT IN ('Rejected', 'Closed')",
        (item_type, item_id, session["user_id"]),
        one=True
    )
    if existing_claim:
        flash("You already have an active claim under review for this item.", "info")
        return redirect(url_for("my_claims"))

    if request.method == "POST":
        q_identify = request.form.get("q_identify", "").strip()
        q_location = request.form.get("q_location", "").strip()
        q_time = request.form.get("q_time", "").strip()
        q_private_features = request.form.get("q_private_features", "").strip()
        q_scratches = request.form.get("q_scratches", "").strip()
        q_accessories = request.form.get("q_accessories", "").strip()
        q_additional = request.form.get("q_additional", "").strip()

        if not q_identify or not q_location or not q_time or not q_private_features:
            flash("Please respond to all mandatory verification questions.", "danger")
            return render_template("claim.html", item=item, item_type=item_type)

        # Create initial claim entry
        claim_res = execute_db(
            """
            INSERT INTO claims (item_type, item_id, claimant_id, status)
            VALUES (%s, %s, %s, 'Pending Verification')
            """,
            (item_type, item_id, session["user_id"])
        )
        claim_id = claim_res["last_id"]

        # Store structured question answers
        questions = [
            ("q_identify", "1. How did you identify this item?", q_identify),
            ("q_location", "2. Where did you lose/misplace the item?", q_location),
            ("q_time", "3. Approximately when did you lose it?", q_time),
            ("q_private_features", "4. Describe distinctive features not visible publicly", q_private_features),
            ("q_scratches", "5. Describe scratches, marks, stickers or customizations", q_scratches),
            ("q_accessories", "6. Describe unique accessories associated with the item", q_accessories),
            ("q_additional", "7. Corroborating ownership information", q_additional),
        ]

        for q_key, q_text, ans_text in questions:
            execute_db(
                """
                INSERT INTO claim_answers (claim_id, question_key, question_text, answer_text)
                VALUES (%s, %s, %s, %s)
                """,
                (claim_id, q_key, q_text, ans_text)
            )

        # Handle optional ownership evidence upload
        has_evidence = False
        if "evidence_file" in request.files:
            ev_file = request.files["evidence_file"]
            if ev_file and ev_file.filename:
                ev_path = save_uploaded_file(ev_file, Config.EVIDENCE_FOLDER, Config.ALLOWED_EVIDENCE_EXTENSIONS)
                if ev_path:
                    has_evidence = True
                    ev_desc = request.form.get("evidence_description", "").strip()
                    file_ext = ev_file.filename.rsplit(".", 1)[1].lower() if "." in ev_file.filename else "unknown"
                    execute_db(
                        """
                        INSERT INTO ownership_evidence (claim_id, file_path, original_filename, file_type, description)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (claim_id, ev_path, secure_filename(ev_file.filename), file_ext, ev_desc)
                    )

        # Evaluate claim using rule-based decision support system
        answers_dict = {
            "location_lost": q_location,
            "time_lost": q_time,
            "private_features": q_private_features,
            "scratches_marks": q_scratches,
            "accessories": q_accessories,
            "additional_info": q_additional
        }

        eval_result = evaluate_claim(
            claim_id, item_type, item_id, session["user_id"], answers_dict, has_evidence
        )

        # Update item status to 'Claim Pending' if currently 'Active'
        if item.get("status") == "Active":
            execute_db(f"UPDATE {table} SET status = 'Claim Pending' WHERE id = %s", (item_id,))

        log_audit(
            claim_id=claim_id, item_type=item_type, item_id=item_id, user_id=session["user_id"],
            action="SUBMIT_CLAIM", notes=f"Claim submitted. Initial Score: {eval_result['score']}"
        )

        create_notification(
            session["user_id"],
            "Verification Claim Received",
            f"Your ownership claim for '{item['item_name']}' is now in queue for administrative review.",
            link=url_for("my_claims")
        )

        flash(
            "Claim submitted successfully. Your answers have been recorded for administrative verification.",
            "success"
        )
        return redirect(url_for("my_claims"))

    return render_template("claim.html", item=item, item_type=item_type)

@app.route("/claim/respond/<int:claim_id>", methods=["GET", "POST"])
@login_required
def claim_respond(claim_id):
    """Claimant responds to administrator request for supplementary information."""
    claim = query_db(
        """
        SELECT c.*,
               CASE WHEN c.item_type = 'lost' THEN l.item_name ELSE f.item_name END AS item_name
        FROM claims c
        LEFT JOIN lost_items l ON c.item_type = 'lost' AND c.item_id = l.id
        LEFT JOIN found_items f ON c.item_type = 'found' AND c.item_id = f.id
        WHERE c.id = %s AND c.claimant_id = %s
        """,
        (claim_id, session["user_id"]),
        one=True
    )

    if not claim:
        abort(404)

    if request.method == "POST":
        additional_info = request.form.get("additional_info", "").strip()
        if not additional_info:
            flash("Please provide clarification in the response box.", "danger")
            return render_template("claim_respond.html", claim=claim)

        # Handle optional supplementary evidence upload
        if "evidence_file" in request.files:
            ev_file = request.files["evidence_file"]
            if ev_file and ev_file.filename:
                ev_path = save_uploaded_file(ev_file, Config.EVIDENCE_FOLDER, Config.ALLOWED_EVIDENCE_EXTENSIONS)
                if ev_path:
                    file_ext = ev_file.filename.rsplit(".", 1)[1].lower() if "." in ev_file.filename else "unknown"
                    execute_db(
                        """
                        INSERT INTO ownership_evidence (claim_id, file_path, original_filename, file_type, description)
                        VALUES (%s, %s, %s, %s, 'Supplementary evidence submitted upon request')
                        """,
                        (claim_id, ev_path, secure_filename(ev_file.filename), file_ext)
                    )

        # Update claim record: move back to Under Admin Review
        execute_db(
            """
            UPDATE claims
            SET additional_info_provided = %s, status = 'Under Admin Review', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (additional_info, claim_id)
        )

        log_audit(
            claim_id=claim_id, item_type=claim["item_type"], item_id=claim["item_id"],
            user_id=session["user_id"], action="SUBMIT_ADDITIONAL_INFO",
            notes="Claimant provided requested additional verification information."
        )

        flash("Information transmitted to administrator for updated assessment.", "success")
        return redirect(url_for("my_claims"))

    return render_template("claim_respond.html", claim=claim)

# ----------------------------------------------------------
# User Dashboard & Profile
# ----------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    """User personal dashboard with live database values."""
    user_id = session["user_id"]
    user = query_db("SELECT * FROM users WHERE id = %s", (user_id,), one=True)

    # Real statistics
    lost_count = query_db("SELECT COUNT(*) AS c FROM lost_items WHERE user_id = %s", (user_id,), one=True)["c"]
    found_count = query_db("SELECT COUNT(*) AS c FROM found_items WHERE user_id = %s", (user_id,), one=True)["c"]
    pending_claims = query_db(
        "SELECT COUNT(*) AS c FROM claims WHERE claimant_id = %s AND status IN ('Pending Verification', 'Under Admin Review', 'Additional Information Required')",
        (user_id,), one=True
    )["c"]
    approved_claims = query_db(
        "SELECT COUNT(*) AS c FROM claims WHERE claimant_id = %s AND status = 'Approved'",
        (user_id,), one=True
    )["c"]

    # Notifications
    notifications = query_db(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )

    # Mark notifications as read
    execute_db("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (user_id,))

    # Recent reports
    recent_reports = query_db(
        """
        (SELECT l.id, 'lost' AS item_type, l.item_name, l.date_lost AS event_date, l.status, l.created_at, c.name AS category_name
         FROM lost_items l JOIN categories c ON l.category_id = c.id WHERE l.user_id = %s)
        UNION ALL
        (SELECT f.id, 'found' AS item_type, f.item_name, f.date_found AS event_date, f.status, f.created_at, c.name AS category_name
         FROM found_items f JOIN categories c ON f.category_id = c.id WHERE f.user_id = %s)
        ORDER BY created_at DESC LIMIT 5
        """,
        (user_id, user_id)
    )

    # Recent claims
    recent_claims = query_db(
        """
        SELECT c.id, c.item_type, c.item_id, c.status, c.created_at,
               CASE WHEN c.item_type = 'lost' THEN l.item_name ELSE f.item_name END AS item_name
        FROM claims c
        LEFT JOIN lost_items l ON c.item_type = 'lost' AND c.item_id = l.id
        LEFT JOIN found_items f ON c.item_type = 'found' AND c.item_id = f.id
        WHERE c.claimant_id = %s
        ORDER BY c.created_at DESC LIMIT 5
        """,
        (user_id,)
    )

    stats = {
        "my_lost_count": lost_count,
        "my_found_count": found_count,
        "my_claims_pending": pending_claims,
        "my_claims_approved": approved_claims
    }

    return render_template(
        "dashboard.html",
        user=user,
        stats=stats,
        notifications=notifications,
        recent_reports=recent_reports,
        recent_claims=recent_claims,
        active_page="dashboard"
    )

@app.route("/my-reports")
@login_required
def my_reports():
    """List all reports created by the current user."""
    user_id = session["user_id"]
    lost_items = query_db(
        """
        SELECT l.*, c.name AS category_name
        FROM lost_items l
        JOIN categories c ON l.category_id = c.id
        WHERE l.user_id = %s
        ORDER BY l.created_at DESC
        """,
        (user_id,)
    )
    found_items = query_db(
        """
        SELECT f.*, c.name AS category_name
        FROM found_items f
        JOIN categories c ON f.category_id = c.id
        WHERE f.user_id = %s
        ORDER BY f.created_at DESC
        """,
        (user_id,)
    )
    return render_template(
        "my_reports.html",
        lost_items=lost_items,
        found_items=found_items,
        active_page="my_reports"
    )

@app.route("/report/edit/<item_type>/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_report(item_type, item_id):
    """Edit report parameters (ensuring strict ownership check)."""
    if item_type not in ("lost", "found"):
        abort(404)

    table = "lost_items" if item_type == "lost" else "found_items"
    date_col = "date_lost" if item_type == "lost" else "date_found"
    loc_col = "location_lost" if item_type == "lost" else "location_found"

    item = query_db(
        f"SELECT *, {date_col} AS event_date, {loc_col} AS location FROM {table} WHERE id = %s",
        (item_id,),
        one=True
    )

    if not item:
        abort(404)

    # Authorization: only creator or administrator can edit
    if item["user_id"] != session["user_id"] and session.get("user_role") != "admin":
        abort(403)

    categories = query_db("SELECT * FROM categories ORDER BY name ASC")

    if request.method == "POST":
        item_name = request.form.get("item_name", "").strip()
        category_id = request.form.get("category_id", "").strip()
        event_date = request.form.get("event_date", "").strip()
        approximate_time = request.form.get("approximate_time", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", item["status"])

        safe_image_path = item["safe_image_path"]
        if "safe_image" in request.files:
            uploaded_img = request.files["safe_image"]
            if uploaded_img and uploaded_img.filename:
                new_path = save_uploaded_file(uploaded_img, Config.UPLOAD_FOLDER, Config.ALLOWED_IMAGE_EXTENSIONS)
                if new_path:
                    safe_image_path = new_path

        if item_type == "lost":
            priv_detail = request.form.get("private_identifying_detail", "").strip()
            priv_distinct = request.form.get("private_distinctive_characteristic", "").strip()
            priv_contents = request.form.get("private_contents", "").strip()
            priv_serial = request.form.get("private_serial_or_id", "").strip()

            execute_db(
                """
                UPDATE lost_items
                SET item_name = %s, category_id = %s, date_lost = %s, approximate_time = %s,
                    location_lost = %s, description = %s, safe_image_path = %s, status = %s,
                    private_identifying_detail = %s, private_distinctive_characteristic = %s,
                    private_contents = %s, private_serial_or_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    item_name, category_id, event_date, approximate_time,
                    location, description, safe_image_path, status,
                    priv_detail, priv_distinct, priv_contents, priv_serial, item_id
                )
            )
        else:
            custody = request.form.get("custody_location", "").strip()
            execute_db(
                """
                UPDATE found_items
                SET item_name = %s, category_id = %s, date_found = %s, approximate_time = %s,
                    location_found = %s, description = %s, safe_image_path = %s, status = %s,
                    custody_location = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    item_name, category_id, event_date, approximate_time,
                    location, description, safe_image_path, status, custody, item_id
                )
            )

        log_audit(
            item_type=item_type, item_id=item_id, user_id=session["user_id"],
            action="UPDATE_REPORT", notes=f"Updated report #{item_type.upper()}-{item_id}"
        )

        flash("Report updated successfully.", "success")
        return redirect(url_for("my_reports"))

    return render_template("edit_report.html", item=item, item_type=item_type, categories=categories)

@app.route("/report/delete/<item_type>/<int:item_id>", methods=["POST"])
@login_required
def delete_report(item_type, item_id):
    """Delete own report (ensuring authorization)."""
    if item_type not in ("lost", "found"):
        abort(404)

    table = "lost_items" if item_type == "lost" else "found_items"
    item = query_db(f"SELECT * FROM {table} WHERE id = %s", (item_id,), one=True)
    if not item:
        abort(404)

    if item["user_id"] != session["user_id"] and session.get("user_role") != "admin":
        abort(403)

    execute_db(f"DELETE FROM {table} WHERE id = %s", (item_id,))
    log_audit(
        item_type=item_type, item_id=item_id, user_id=session["user_id"],
        action="DELETE_REPORT", notes=f"Deleted report #{item_type.upper()}-{item_id}"
    )

    flash("Report deleted from database.", "info")
    return redirect(url_for("my_reports"))

@app.route("/my-claims")
@login_required
def my_claims():
    """List all claims submitted by the current user."""
    user_id = session["user_id"]
    claims = query_db(
        """
        SELECT c.*,
               CASE WHEN c.item_type = 'lost' THEN l.item_name ELSE f.item_name END AS item_name
        FROM claims c
        LEFT JOIN lost_items l ON c.item_type = 'lost' AND c.item_id = l.id
        LEFT JOIN found_items f ON c.item_type = 'found' AND c.item_id = f.id
        WHERE c.claimant_id = %s
        ORDER BY c.created_at DESC
        """,
        (user_id,)
    )
    return render_template("my_claims.html", claims=claims, active_page="my_claims")

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile management and password update."""
    user_id = session["user_id"]
    user = query_db("SELECT * FROM users WHERE id = %s", (user_id,), one=True)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile":
            full_name = request.form.get("full_name", "").strip()
            phone = request.form.get("phone", "").strip()

            if not full_name:
                flash("Full name cannot be left blank.", "danger")
            else:
                execute_db(
                    "UPDATE users SET full_name = %s, phone = %s WHERE id = %s",
                    (full_name, phone, user_id)
                )
                session["user_name"] = full_name
                flash("Profile details updated successfully.", "success")
                return redirect(url_for("profile"))

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_new_pw = request.form.get("confirm_new_password", "")

            if not check_password_hash(user["password_hash"], current_pw):
                flash("Current password is incorrect.", "danger")
            elif len(new_pw) < 6:
                flash("New password must contain at least 6 characters.", "danger")
            elif new_pw != confirm_new_pw:
                flash("New password confirmation does not match.", "danger")
            else:
                new_hash = generate_password_hash(new_pw, method="scrypt")
                execute_db("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
                log_audit(user_id=user_id, action="PASSWORD_CHANGE", notes="User changed account password")
                flash("Password changed successfully.", "success")
                return redirect(url_for("profile"))

    return render_template("profile.html", user=user, active_page="profile")

# ----------------------------------------------------------
# Protected File Serving
# ----------------------------------------------------------

@app.route("/uploads/items/<path:filename>")
def uploaded_item_file(filename):
    """Serve public item photographs."""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

@app.route("/evidence/<path:filename>")
@login_required
def view_protected_evidence(filename):
    """
    Serve sensitive ownership evidence documents.
    Protected by server-side authorization: only administrators
    or the claimant who uploaded the document may access it.
    """
    evidence_row = query_db(
        """
        SELECT e.*, c.claimant_id
        FROM ownership_evidence e
        JOIN claims c ON e.claim_id = c.id
        WHERE e.file_path = %s
        """,
        (filename,),
        one=True
    )

    if not evidence_row:
        abort(404)

    is_admin = session.get("user_role") == "admin"
    is_claimant = session.get("user_id") == evidence_row["claimant_id"]

    if not is_admin and not is_claimant:
        log_audit(
            user_id=session.get("user_id"),
            action="UNAUTHORIZED_EVIDENCE_ACCESS_ATTEMPT",
            notes=f"Attempted access to evidence: {filename}"
        )
        abort(403)

    return send_from_directory(Config.EVIDENCE_FOLDER, filename)

# ----------------------------------------------------------
# Administrator Portal Routes
# ----------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Dedicated administrator portal authentication."""
    if "user_id" in session and session.get("user_role") == "admin":
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = query_db("SELECT * FROM users WHERE email = %s AND role = 'admin'", (email,), one=True)
        if not user or not check_password_hash(user["password_hash"], password):
            log_audit(action="FAILED_ADMIN_LOGIN_ATTEMPT", notes=f"Failed admin login for: {email}")
            flash("Invalid administrator credentials.", "danger")
            return render_template("admin/login.html")

        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]
        session["user_role"] = "admin"

        log_audit(user_id=user["id"], action="ADMIN_LOGIN", notes="Administrator authenticated to console")
        flash(f"Welcome back, Administrator {user['full_name']}.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/login.html")

@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Administrator console overview displaying live database metrics only."""
    total_users = query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'user'", one=True)["c"]
    total_lost = query_db("SELECT COUNT(*) AS c FROM lost_items", one=True)["c"]
    total_found = query_db("SELECT COUNT(*) AS c FROM found_items", one=True)["c"]
    pending_claims = query_db(
        "SELECT COUNT(*) AS c FROM claims WHERE status IN ('Pending Verification', 'Under Admin Review', 'Additional Information Required')",
        one=True
    )["c"]
    needs_review_count = query_db(
        "SELECT COUNT(*) AS c FROM claims WHERE suspicious_flag = 1 OR confidence_level IN ('Needs Review', 'Low Confidence')",
        one=True
    )["c"]
    returned_items = query_db(
        "SELECT COUNT(*) AS c FROM claims WHERE status = 'Approved'",
        one=True
    )["c"]

    stats = {
        "total_users": total_users,
        "total_lost": total_lost,
        "total_found": total_found,
        "pending_claims": pending_claims,
        "needs_review_count": needs_review_count,
        "returned_items": returned_items
    }

    # Verification Queue
    queue_claims = query_db(
        """
        SELECT c.*, u.full_name AS claimant_name, u.email AS claimant_email,
               CASE WHEN c.item_type = 'lost' THEN l.item_name ELSE f.item_name END AS item_name
        FROM claims c
        JOIN users u ON c.claimant_id = u.id
        LEFT JOIN lost_items l ON c.item_type = 'lost' AND c.item_id = l.id
        LEFT JOIN found_items f ON c.item_type = 'found' AND c.item_id = f.id
        WHERE c.status IN ('Pending Verification', 'Under Admin Review', 'Additional Information Required')
        ORDER BY c.suspicious_flag DESC, c.verification_score DESC
        LIMIT 10
        """
    )

    # Recent Audit Logs
    recent_logs = query_db(
        """
        SELECT a.*, u.full_name AS user_name
        FROM claim_audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
        LIMIT 8
        """
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        pending_claims=queue_claims,
        recent_logs=recent_logs,
        active_admin="dashboard"
    )

@app.route("/admin/claims")
@admin_required
def admin_claims():
    """All claims view with status and confidence level filtering."""
    status_filter = request.args.get("status", "").strip()
    risk_filter = request.args.get("risk", "").strip()

    conditions = []
    params = []

    if status_filter:
        conditions.append("c.status = %s")
        params.append(status_filter)

    if risk_filter:
        conditions.append("c.confidence_level = %s")
        params.append(risk_filter)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT c.*, u.full_name AS claimant_name, u.email AS claimant_email,
               CASE WHEN c.item_type = 'lost' THEN l.item_name ELSE f.item_name END AS item_name
        FROM claims c
        JOIN users u ON c.claimant_id = u.id
        LEFT JOIN lost_items l ON c.item_type = 'lost' AND c.item_id = l.id
        LEFT JOIN found_items f ON c.item_type = 'found' AND c.item_id = f.id
        {where_clause}
        ORDER BY c.created_at DESC
    """
    claims = query_db(sql, params)

    return render_template(
        "admin/claims.html",
        claims=claims,
        selected_status=status_filter,
        selected_risk=risk_filter,
        active_admin="claims"
    )

@app.route("/admin/claim/<int:claim_id>")
@admin_required
def admin_claim_review(claim_id):
    """Detailed claim review with breakdown, answers, and private item markers."""
    claim = query_db("SELECT * FROM claims WHERE id = %s", (claim_id,), one=True)
    if not claim:
        abort(404)

    claimant = query_db("SELECT * FROM users WHERE id = %s", (claim["claimant_id"],), one=True)
    table = "lost_items" if claim["item_type"] == "lost" else "found_items"
    item = query_db(f"SELECT * FROM {table} WHERE id = %s", (claim["item_id"],), one=True)

    claim_answers = query_db("SELECT * FROM claim_answers WHERE claim_id = %s ORDER BY id ASC", (claim_id,))
    evidence_files = query_db("SELECT * FROM ownership_evidence WHERE claim_id = %s ORDER BY id ASC", (claim_id,))
    verification_res = query_db("SELECT * FROM verification_results WHERE claim_id = %s", (claim_id,), one=True)

    import json
    score_breakdown = []
    flags = []
    if verification_res:
        try:
            score_breakdown = json.loads(verification_res["score_breakdown"])
        except Exception:
            score_breakdown = []
        try:
            flags = json.loads(verification_res["flags"]) if verification_res["flags"] else []
        except Exception:
            flags = []

    # Claimant history summary
    total_claims = query_db("SELECT COUNT(*) AS c FROM claims WHERE claimant_id = %s", (claimant["id"],), one=True)["c"]
    rejected_claims = query_db(
        "SELECT COUNT(*) AS c FROM claims WHERE claimant_id = %s AND status = 'Rejected'",
        (claimant["id"],), one=True
    )["c"]

    claimant_history = {
        "total_claims": total_claims,
        "rejected_claims": rejected_claims
    }

    return render_template(
        "admin/claim_review.html",
        claim=claim,
        claimant=claimant,
        item=item,
        claim_answers=claim_answers,
        evidence_files=evidence_files,
        score_breakdown=score_breakdown,
        flags=flags,
        claimant_history=claimant_history,
        active_admin="claims"
    )

@app.route("/admin/claim/<int:claim_id>/action", methods=["POST"])
@admin_required
def admin_claim_action(claim_id):
    """Execute administrative decision: approve, reject, or request information."""
    action = request.form.get("action")
    admin_notes = request.form.get("admin_notes", "").strip()

    claim = query_db("SELECT * FROM claims WHERE id = %s", (claim_id,), one=True)
    if not claim:
        abort(404)

    item_type = claim["item_type"]
    item_id = claim["item_id"]
    claimant_id = claim["claimant_id"]
    table = "lost_items" if item_type == "lost" else "found_items"

    if action == "approve":
        # 1. Update claim status
        execute_db(
            """
            UPDATE claims
            SET status = 'Approved', admin_notes = %s, reviewed_by = %s,
                reviewed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (admin_notes, session["user_id"], claim_id)
        )

        # 2. Update item status to 'Claimed' / 'Returned'
        target_status = "Claimed" if item_type == "found" else "Returned"
        execute_db(f"UPDATE {table} SET status = %s WHERE id = %s", (target_status, item_id))

        # 3. Reject or close other competing claims on this item
        execute_db(
            """
            UPDATE claims
            SET status = 'Closed', admin_notes = 'Closed: competing claim was verified by administration.'
            WHERE item_type = %s AND item_id = %s AND id != %s AND status != 'Approved'
            """,
            (item_type, item_id, claim_id)
        )

        # 4. Notify claimant
        create_notification(
            claimant_id,
            "Ownership Claim Approved",
            f"Your ownership verification claim for item #{item_type.upper()}-{item_id} has been approved by administration. Check instructions for recovery.",
            link=url_for("my_claims")
        )

        log_audit(
            claim_id=claim_id, item_type=item_type, item_id=item_id, user_id=session["user_id"],
            action="APPROVE_CLAIM", notes=f"Claim approved. Item updated to {target_status}. Notes: {admin_notes}"
        )
        flash("Claim has been marked Approved and item status updated to Claimed.", "success")

    elif action == "reject":
        execute_db(
            """
            UPDATE claims
            SET status = 'Rejected', admin_notes = %s, reviewed_by = %s,
                reviewed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (admin_notes, session["user_id"], claim_id)
        )

        # If no other active claims remain, restore item status to 'Active'
        other_active = query_db(
            "SELECT COUNT(*) AS c FROM claims WHERE item_type = %s AND item_id = %s AND status IN ('Pending Verification', 'Under Admin Review')",
            (item_type, item_id),
            one=True
        )["c"]

        if other_active == 0:
            execute_db(f"UPDATE {table} SET status = 'Active' WHERE id = %s AND status = 'Claim Pending'", (item_id,))

        create_notification(
            claimant_id,
            "Claim Decision: Not Verified",
            f"Your ownership claim for item #{item_type.upper()}-{item_id} was reviewed and could not be verified at this time.",
            link=url_for("my_claims")
        )

        log_audit(
            claim_id=claim_id, item_type=item_type, item_id=item_id, user_id=session["user_id"],
            action="REJECT_CLAIM", notes=f"Claim rejected. Notes: {admin_notes}"
        )
        flash("Claim has been marked Rejected.", "info")

    elif action == "request_info":
        execute_db(
            """
            UPDATE claims
            SET status = 'Additional Information Required', additional_info_requested = %s,
                admin_notes = %s, reviewed_by = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (admin_notes, admin_notes, session["user_id"], claim_id)
        )

        create_notification(
            claimant_id,
            "Additional Verification Information Requested",
            f"The administrator has requested further details for your claim on item #{item_type.upper()}-{item_id}. Please review and respond.",
            link=url_for("claim_respond", claim_id=claim_id)
        )

        log_audit(
            claim_id=claim_id, item_type=item_type, item_id=item_id, user_id=session["user_id"],
            action="REQUEST_ADDITIONAL_INFO", notes=f"Requested info: {admin_notes}"
        )
        flash("Request for additional information transmitted to claimant.", "warning")

    elif action == "under_review":
        execute_db(
            """
            UPDATE claims
            SET status = 'Under Admin Review', admin_notes = %s, reviewed_by = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (admin_notes, session["user_id"], claim_id)
        )

        log_audit(
            claim_id=claim_id, item_type=item_type, item_id=item_id, user_id=session["user_id"],
            action="SET_UNDER_REVIEW", notes=f"Flagged for ongoing review. Notes: {admin_notes}"
        )
        flash("Claim status updated to Under Admin Review.", "info")

    return redirect(url_for("admin_claim_review", claim_id=claim_id))

@app.route("/admin/users")
@admin_required
def admin_users():
    """List and manage user accounts."""
    users = query_db("SELECT * FROM users ORDER BY created_at DESC")
    return render_template("admin/users.html", users=users, active_admin="users")

@app.route("/admin/user/<int:user_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(user_id):
    """Toggle user active state (suspend / reactivate)."""
    user = query_db("SELECT * FROM users WHERE id = %s", (user_id,), one=True)
    if not user:
        abort(404)

    new_state = 0 if user["is_active"] else 1
    execute_db("UPDATE users SET is_active = %s WHERE id = %s", (new_state, user_id))

    action_name = "SUSPEND_USER" if new_state == 0 else "REACTIVATE_USER"
    log_audit(user_id=session["user_id"], action=action_name, notes=f"User #{user_id} active status set to {new_state}")

    flash(f"User {user['full_name']} has been {'suspended' if new_state == 0 else 'reactivated'}.", "info")
    return redirect(url_for("admin_users"))

@app.route("/admin/reports")
@admin_required
def admin_reports():
    """All reports listing with management actions."""
    reports = query_db(
        """
        (SELECT l.id, 'lost' AS item_type, l.item_name, l.date_lost AS event_date, l.status, l.created_at,
                c.name AS category_name, u.full_name AS reporter_name
         FROM lost_items l
         JOIN categories c ON l.category_id = c.id
         JOIN users u ON l.user_id = u.id)
        UNION ALL
        (SELECT f.id, 'found' AS item_type, f.item_name, f.date_found AS event_date, f.status, f.created_at,
                c.name AS category_name, u.full_name AS reporter_name
         FROM found_items f
         JOIN categories c ON f.category_id = c.id
         JOIN users u ON f.user_id = u.id)
        ORDER BY created_at DESC
        """
    )
    return render_template("admin/reports.html", reports=reports, active_admin="reports")

@app.route("/admin/reports/lost")
@admin_required
def admin_lost_items():
    """Detailed view of lost items with full private verification data visible to admin."""
    lost_items = query_db(
        """
        SELECT l.*, c.name AS category_name, u.full_name AS reporter_name, u.email AS reporter_email
        FROM lost_items l
        JOIN categories c ON l.category_id = c.id
        JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC
        """
    )
    return render_template("admin/lost_items.html", lost_items=lost_items, active_admin="lost")

@app.route("/admin/reports/found")
@admin_required
def admin_found_items():
    """Detailed view of found items with custody locations."""
    found_items = query_db(
        """
        SELECT f.*, c.name AS category_name, u.full_name AS reporter_name, u.email AS reporter_email
        FROM found_items f
        JOIN categories c ON f.category_id = c.id
        JOIN users u ON f.user_id = u.id
        ORDER BY f.created_at DESC
        """
    )
    return render_template("admin/found_items.html", found_items=found_items, active_admin="found")

@app.route("/admin/report/<item_type>/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_delete_report(item_type, item_id):
    """Administrator removal of inappropriate or spam report."""
    if item_type not in ("lost", "found"):
        abort(404)
    table = "lost_items" if item_type == "lost" else "found_items"
    execute_db(f"DELETE FROM {table} WHERE id = %s", (item_id,))
    log_audit(
        item_type=item_type, item_id=item_id, user_id=session["user_id"],
        action="ADMIN_DELETE_REPORT", notes=f"Admin removed report #{item_type.upper()}-{item_id}"
    )
    flash(f"Report #{item_type.upper()}-{item_id} removed from system.", "info")
    return redirect(request.referrer or url_for("admin_reports"))

@app.route("/admin/audit-logs")
@admin_required
def admin_audit_logs():
    """Inspect complete historical security and action audit logs."""
    logs = query_db(
        """
        SELECT a.*, u.full_name AS user_name, u.email AS user_email
        FROM claim_audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
        LIMIT 200
        """
    )
    return render_template("admin/audit_logs.html", logs=logs, active_admin="audit")

@app.route("/admin/settings")
@admin_required
def admin_settings():
    """System settings and category management."""
    categories = query_db(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM lost_items WHERE category_id = c.id) +
               (SELECT COUNT(*) FROM found_items WHERE category_id = c.id) AS item_count
        FROM categories c
        ORDER BY c.name ASC
        """
    )
    return render_template("admin/settings.html", categories=categories, active_admin="settings")

@app.route("/admin/categories/add", methods=["POST"])
@admin_required
def admin_add_category():
    """Add a new category classification."""
    name = request.form.get("name", "").strip()
    desc = request.form.get("description", "").strip()
    if name:
        try:
            execute_db("INSERT INTO categories (name, description) VALUES (%s, %s)", (name, desc))
            flash(f"Category '{name}' added successfully.", "success")
        except Exception:
            flash(f"Category '{name}' already exists.", "danger")
    return redirect(url_for("admin_settings"))

# ----------------------------------------------------------
# Custom Error Handlers
# ----------------------------------------------------------

@app.errorhandler(403)
def forbidden_error(e):
    return render_template("403.html"), 403

@app.errorhandler(404)
def not_found_error(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html"), 500

# ----------------------------------------------------------
# Application Entrypoint
# ----------------------------------------------------------

if __name__ == "__main__":
    init_admin_user()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=Config.FLASK_DEBUG)
