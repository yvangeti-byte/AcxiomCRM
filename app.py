from datetime import datetime, date
import re

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    abort
)

from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from flask_bcrypt import Bcrypt


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "acxiomcrm-development-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///acxiomcrm.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


# ============================================================
# CONSTANTS
# ============================================================

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
MIN_PASSWORD_LENGTH = 8


# ============================================================
# MODELS
# ============================================================

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(50),
        nullable=False,
        default="Sales Executive"
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    failed_login_attempts = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    locked_until = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    customers = db.relationship(
        "Customer",
        foreign_keys="Customer.assigned_to_id",
        backref="assigned_to",
        lazy=True
    )

    leads = db.relationship(
        "Lead",
        foreign_keys="Lead.owner_id",
        backref="owner",
        lazy=True
    )

    opportunities = db.relationship(
        "Opportunity",
        foreign_keys="Opportunity.owner_id",
        backref="owner",
        lazy=True
    )

    followups = db.relationship(
        "FollowUp",
        foreign_keys="FollowUp.user_id",
        backref="user",
        lazy=True
    )

    activities = db.relationship(
        "Activity",
        foreign_keys="Activity.user_id",
        backref="user",
        lazy=True
    )


class Customer(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        nullable=False,
        unique=True
    )

    phone = db.Column(
        db.String(20),
        nullable=False,
        unique=True
    )

    address = db.Column(
        db.String(255)
    )

    status = db.Column(
        db.String(50),
        default="Active"
    )

    assigned_to_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    notes = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Lead(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        nullable=False,
        unique=True
    )

    phone = db.Column(
        db.String(20),
        nullable=False,
        unique=True
    )

    source = db.Column(
        db.String(100)
    )

    status = db.Column(
        db.String(50),
        default="New"
    )

    priority = db.Column(
        db.String(50),
        default="Medium"
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    notes = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Opportunity(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(150),
        nullable=False
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=False
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    stage = db.Column(
        db.String(50),
        default="Qualification"
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    probability = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    expected_close = db.Column(
        db.Date,
        nullable=True
    )

    source = db.Column(
        db.String(100)
    )

    notes = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    customer = db.relationship(
        "Customer",
        backref="opportunities"
    )


class FollowUp(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=True
    )

    lead_id = db.Column(
        db.Integer,
        db.ForeignKey("lead.id"),
        nullable=True
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    subject = db.Column(
        db.String(200),
        nullable=False
    )

    type = db.Column(
        db.String(50),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        default="Planned"
    )

    notes = db.Column(
        db.Text
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    customer = db.relationship(
        "Customer",
        backref="followups"
    )

    lead = db.relationship(
        "Lead",
        backref="followups"
    )


class Activity(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=True
    )

    lead_id = db.Column(
        db.Integer,
        db.ForeignKey("lead.id"),
        nullable=True
    )

    type = db.Column(
        db.String(50),
        nullable=False
    )

    subject = db.Column(
        db.String(200),
        nullable=False
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    notes = db.Column(
        db.Text
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    customer = db.relationship(
        "Customer",
        backref="activities"
    )

    lead = db.relationship(
        "Lead",
        backref="activities"
    )


class AuditLog(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    action = db.Column(
        db.String(100),
        nullable=False
    )

    module = db.Column(
        db.String(100),
        nullable=False
    )

    record_id = db.Column(
        db.Integer,
        nullable=True
    )

    result = db.Column(
        db.String(50),
        nullable=False
    )

    details = db.Column(
        db.Text
    )

    user = db.relationship(
        "User",
        backref="audit_logs"
    )


# ============================================================
# LOGIN MANAGER
# ============================================================

@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )


# ============================================================
# AUDIT HELPER
# ============================================================

def create_audit(
    action,
    module,
    result="SUCCESS",
    record_id=None,
    details=None,
    user_id=None
):

    if user_id is None:

        if current_user.is_authenticated:
            user_id = current_user.id

    audit = AuditLog(
        user_id=user_id,
        action=action,
        module=module,
        record_id=record_id,
        result=result,
        details=details
    )

    db.session.add(audit)

    return audit


# ============================================================
# AUTHORIZATION
# ============================================================

def admin_required():

    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    if current_user.role != "Admin":
        abort(403)

    return None


def role_required(*roles):

    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    if current_user.role not in roles:
        abort(403)

    return None


# ============================================================
# VALIDATION HELPERS
# ============================================================

def valid_email(email):

    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

    return bool(
        re.match(
            pattern,
            email
        )
    )


def valid_phone(phone):

    return bool(
        re.fullmatch(
            r"\d{10,15}",
            phone
        )
    )


def valid_password(password):

    if len(password) < MIN_PASSWORD_LENGTH:
        return False

    return True


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not email or not password:

            flash(
                "All required fields must be filled.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if not valid_email(email):

            flash(
                "Please enter a valid email address.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if not valid_password(password):

            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "An account with this email already exists.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        password_hash = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            role="Sales Executive",
            is_active=True
        )

        db.session.add(user)

        db.session.flush()

        create_audit(
            action="REGISTER",
            module="Authentication",
            result="SUCCESS",
            record_id=user.id,
            details=f"User registered: {email}",
            user_id=user.id
        )

        db.session.commit()

        flash(
            "Registration successful. Please log in.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            email=email
        ).first()

        # ----------------------------------------------------
        # Invalid user
        # ----------------------------------------------------

        if not user:

            create_audit(
                action="LOGIN_FAILURE",
                module="Authentication",
                result="FAILURE",
                details=f"Unknown login email: {email}"
            )

            db.session.commit()

            flash(
                "Invalid email or password.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        # ----------------------------------------------------
        # Inactive account
        # ----------------------------------------------------

        if not user.is_active:

            create_audit(
                action="LOGIN_FAILURE",
                module="Authentication",
                result="FAILURE",
                record_id=user.id,
                details="Inactive account"
            )

            db.session.commit()

            flash(
                "Your account is inactive.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        # ----------------------------------------------------
        # Account lockout check
        # ----------------------------------------------------

        if user.locked_until:

            if datetime.utcnow() < user.locked_until:

                create_audit(
                    action="LOGIN_FAILURE",
                    module="Authentication",
                    result="LOCKED",
                    record_id=user.id,
                    details="Account temporarily locked"
                )

                db.session.commit()

                flash(
                    "Account temporarily locked. Please try again later.",
                    "danger"
                )

                return redirect(
                    url_for("login")
                )

            else:

                user.locked_until = None
                user.failed_login_attempts = 0

                db.session.commit()

        # ----------------------------------------------------
        # Password verification
        # ----------------------------------------------------

        if not bcrypt.check_password_hash(
            user.password_hash,
            password
        ):

            user.failed_login_attempts += 1

            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:

                from datetime import timedelta

                user.locked_until = (
                    datetime.utcnow()
                    + timedelta(
                        minutes=LOCKOUT_MINUTES
                    )
                )

                create_audit(
                    action="ACCOUNT_LOCKED",
                    module="Authentication",
                    result="LOCKED",
                    record_id=user.id,
                    details=(
                        f"Account locked after "
                        f"{MAX_LOGIN_ATTEMPTS} failed attempts."
                    )
                )

            else:

                create_audit(
                    action="LOGIN_FAILURE",
                    module="Authentication",
                    result="FAILURE",
                    record_id=user.id,
                    details=(
                        f"Failed login attempt "
                        f"{user.failed_login_attempts}"
                    )
                )

            db.session.commit()

            flash(
                "Invalid email or password.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        # ----------------------------------------------------
        # Successful login
        # ----------------------------------------------------

        user.failed_login_attempts = 0
        user.locked_until = None

        login_user(user)

        create_audit(
            action="LOGIN_SUCCESS",
            module="Authentication",
            result="SUCCESS",
            record_id=user.id,
            details="Successful user login"
        )

        db.session.commit()

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
@login_required
def logout():

    user_id = current_user.id

    create_audit(
        action="LOGOUT",
        module="Authentication",
        result="SUCCESS",
        record_id=user_id,
        details="User logged out"
    )

    db.session.commit()

    logout_user()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    customer_count = Customer.query.count()

    lead_count = Lead.query.count()

    opportunity_count = Opportunity.query.count()

    followup_count = FollowUp.query.count()

    activity_count = Activity.query.count()

    won_opportunities = Opportunity.query.filter_by(
        stage="Won"
    ).count()

    lost_opportunities = Opportunity.query.filter_by(
        stage="Lost"
    ).count()

    pipeline_value = sum(
        (opportunity.amount or 0)
        for opportunity in Opportunity.query.all()
    )

    weighted_pipeline = sum(
        (opportunity.amount or 0)
        * (opportunity.probability or 0)
        / 100
        for opportunity in Opportunity.query.all()
    )

    return render_template(
        "dashboard.html",
        customer_count=customer_count,
        lead_count=lead_count,
        opportunity_count=opportunity_count,
        followup_count=followup_count,
        activity_count=activity_count,
        won_opportunities=won_opportunities,
        lost_opportunities=lost_opportunities,
        pipeline_value=pipeline_value,
        weighted_pipeline=weighted_pipeline
    )


# ============================================================
# CUSTOMERS
# ============================================================

@app.route("/customers")
@login_required
def customers():

    search = request.args.get(
        "search",
        ""
    ).strip()

    query = Customer.query

    if search:

        search_pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Customer.name.ilike(search_pattern),
                Customer.email.ilike(search_pattern),
                Customer.phone.ilike(search_pattern)
            )
        )

    customers_list = query.order_by(
        Customer.id.desc()
    ).all()

    return render_template(
        "customers.html",
        customers=customers_list,
        search=search
    )


@app.route(
    "/customers/create",
    methods=["GET", "POST"]
)
@login_required
def create_customer():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Active"
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        if not name or not email or not phone:

            flash(
                "Name, email, and phone are required.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=None,
                edit_mode=False
            )

        if not valid_email(email):

            flash(
                "Invalid email address.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=None,
                edit_mode=False
            )

        if not valid_phone(phone):

            flash(
                "Phone number must contain 10 to 15 digits.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=None,
                edit_mode=False
            )

        if Customer.query.filter_by(
            email=email
        ).first():

            flash(
                "A customer with this email already exists.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=None,
                edit_mode=False
            )

        if Customer.query.filter_by(
            phone=phone
        ).first():

            flash(
                "A customer with this phone number already exists.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=None,
                edit_mode=False
            )

        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            address=address,
            status=status,
            assigned_to_id=current_user.id,
            notes=notes
        )

        db.session.add(customer)

        db.session.flush()

        create_audit(
            action="CREATE",
            module="Customer",
            result="SUCCESS",
            record_id=customer.id,
            details=f"Customer created: {customer.name}"
        )

        db.session.commit()

        flash(
            "Customer created successfully.",
            "success"
        )

        return redirect(
            url_for("customers")
        )

    return render_template(
        "customer_form.html",
        customer=None,
        edit_mode=False
    )


@app.route(
    "/customers/edit/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def edit_customer(id):

    customer = db.session.get(
        Customer,
        id
    )

    if not customer:
        abort(404)

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Active"
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        if not name or not email or not phone:

            flash(
                "Name, email, and phone are required.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=customer,
                edit_mode=True
            )

        if not valid_email(email):

            flash(
                "Invalid email address.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=customer,
                edit_mode=True
            )

        if not valid_phone(phone):

            flash(
                "Phone number must contain 10 to 15 digits.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=customer,
                edit_mode=True
            )

        duplicate_email = Customer.query.filter(
            Customer.email == email,
            Customer.id != customer.id
        ).first()

        if duplicate_email:

            flash(
                "Another customer already uses this email.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=customer,
                edit_mode=True
            )

        duplicate_phone = Customer.query.filter(
            Customer.phone == phone,
            Customer.id != customer.id
        ).first()

        if duplicate_phone:

            flash(
                "Another customer already uses this phone number.",
                "danger"
            )

            return render_template(
                "customer_form.html",
                customer=customer,
                edit_mode=True
            )

        customer.name = name
        customer.email = email
        customer.phone = phone
        customer.address = address
        customer.status = status
        customer.notes = notes

        create_audit(
            action="UPDATE",
            module="Customer",
            result="SUCCESS",
            record_id=customer.id,
            details=f"Customer updated: {customer.name}"
        )

        db.session.commit()

        flash(
            "Customer updated successfully.",
            "success"
        )

        return redirect(
            url_for("customers")
        )

    return render_template(
        "customer_form.html",
        customer=customer,
        edit_mode=True
    )


@app.route(
    "/customers/delete/<int:id>",
    methods=["POST"]
)
@login_required
def delete_customer(id):

    customer = db.session.get(
        Customer,
        id
    )

    if not customer:
        abort(404)

    customer_name = customer.name

    create_audit(
        action="DELETE",
        module="Customer",
        result="SUCCESS",
        record_id=customer.id,
        details=f"Customer deleted: {customer_name}"
    )

    db.session.delete(customer)

    db.session.commit()

    flash(
        "Customer deleted successfully.",
        "success"
    )

    return redirect(
        url_for("customers")
    )


# ============================================================
# LEADS
# ============================================================

@app.route("/leads")
@login_required
def leads():

    search = request.args.get(
        "search",
        ""
    ).strip()

    query = Lead.query

    if search:

        search_pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Lead.name.ilike(search_pattern),
                Lead.email.ilike(search_pattern),
                Lead.phone.ilike(search_pattern),
                Lead.source.ilike(search_pattern)
            )
        )

    leads_list = query.order_by(
        Lead.id.desc()
    ).all()

    return render_template(
        "leads.html",
        leads=leads_list,
        search=search
    )


@app.route(
    "/leads/create",
    methods=["GET", "POST"]
)
@login_required
def create_lead():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        source = request.form.get(
            "source",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "New"
        ).strip()

        priority = request.form.get(
            "priority",
            "Medium"
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        if not name or not email or not phone:

            flash(
                "Name, email, and phone are required.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=None,
                edit_mode=False
            )

        if not valid_email(email):

            flash(
                "Invalid email address.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=None,
                edit_mode=False
            )

        if not valid_phone(phone):

            flash(
                "Phone number must contain 10 to 15 digits.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=None,
                edit_mode=False
            )

        if Lead.query.filter_by(
            email=email
        ).first():

            flash(
                "A lead with this email already exists.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=None,
                edit_mode=False
            )

        if Lead.query.filter_by(
            phone=phone
        ).first():

            flash(
                "A lead with this phone number already exists.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=None,
                edit_mode=False
            )

        allowed_statuses = [
            "New",
            "Contacted",
            "Qualified",
            "Unqualified",
            "Converted",
            "Lost"
        ]

        allowed_priorities = [
            "Low",
            "Medium",
            "High"
        ]

        if status not in allowed_statuses:

            flash(
                "Invalid lead status.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=None,
                edit_mode=False
            )

        if priority not in allowed_priorities:

            flash(
                "Invalid lead priority.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=None,
                edit_mode=False
            )

        lead = Lead(
            name=name,
            email=email,
            phone=phone,
            source=source,
            status=status,
            priority=priority,
            owner_id=current_user.id,
            notes=notes
        )

        db.session.add(lead)

        db.session.flush()

        create_audit(
            action="CREATE",
            module="Lead",
            result="SUCCESS",
            record_id=lead.id,
            details=f"Lead created: {lead.name}"
        )

        db.session.commit()

        flash(
            "Lead created successfully.",
            "success"
        )

        return redirect(
            url_for("leads")
        )

    return render_template(
        "lead_form.html",
        lead=None,
        edit_mode=False
    )


@app.route(
    "/leads/edit/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def edit_lead(id):

    lead = db.session.get(
        Lead,
        id
    )

    if not lead:
        abort(404)

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        source = request.form.get(
            "source",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "New"
        ).strip()

        priority = request.form.get(
            "priority",
            "Medium"
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        allowed_statuses = [
            "New",
            "Contacted",
            "Qualified",
            "Unqualified",
            "Converted",
            "Lost"
        ]

        allowed_priorities = [
            "Low",
            "Medium",
            "High"
        ]

        if not name or not email or not phone:

            flash(
                "Name, email, and phone are required.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=lead,
                edit_mode=True
            )

        if not valid_email(email):

            flash(
                "Invalid email address.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=lead,
                edit_mode=True
            )

        if not valid_phone(phone):

            flash(
                "Phone number must contain 10 to 15 digits.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=lead,
                edit_mode=True
            )

        if status not in allowed_statuses:

            flash(
                "Invalid lead status.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=lead,
                edit_mode=True
            )

        if priority not in allowed_priorities:

            flash(
                "Invalid lead priority.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=lead,
                edit_mode=True
            )

        duplicate_email = Lead.query.filter(
            Lead.email == email,
            Lead.id != lead.id
        ).first()

        if duplicate_email:

            flash(
                "Another lead already uses this email.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=lead,
                edit_mode=True
            )

        duplicate_phone = Lead.query.filter(
            Lead.phone == phone,
            Lead.id != lead.id
        ).first()

        if duplicate_phone:

            flash(
                "Another lead already uses this phone number.",
                "danger"
            )

            return render_template(
                "lead_form.html",
                lead=lead,
                edit_mode=True
            )

        old_status = lead.status

        lead.name = name
        lead.email = email
        lead.phone = phone
        lead.source = source
        lead.status = status
        lead.priority = priority
        lead.notes = notes

        create_audit(
            action="UPDATE",
            module="Lead",
            result="SUCCESS",
            record_id=lead.id,
            details=f"Lead updated: {lead.name}"
        )

        if old_status != status:

            create_audit(
                action="STATUS_CHANGE",
                module="Lead",
                result="SUCCESS",
                record_id=lead.id,
                details=(
                    f"Lead status changed from "
                    f"{old_status} to {status}"
                )
            )

        db.session.commit()

        flash(
            "Lead updated successfully.",
            "success"
        )

        return redirect(
            url_for("leads")
        )

    return render_template(
        "lead_form.html",
        lead=lead,
        edit_mode=True
    )


@app.route(
    "/leads/delete/<int:id>",
    methods=["POST"]
)
@login_required
def delete_lead(id):

    lead = db.session.get(
        Lead,
        id
    )

    if not lead:
        abort(404)

    lead_name = lead.name

    create_audit(
        action="DELETE",
        module="Lead",
        result="SUCCESS",
        record_id=lead.id,
        details=f"Lead deleted: {lead_name}"
    )

    db.session.delete(lead)

    db.session.commit()

    flash(
        "Lead deleted successfully.",
        "success"
    )

    return redirect(
        url_for("leads")
    )


# ============================================================
# OPPORTUNITIES
# ============================================================

@app.route("/opportunities")
@login_required
def opportunities():

    search = request.args.get(
        "search",
        ""
    ).strip()

    query = Opportunity.query

    if search:

        search_pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Opportunity.name.ilike(search_pattern),
                Opportunity.source.ilike(search_pattern)
            )
        )

    opportunities_list = query.order_by(
        Opportunity.id.desc()
    ).all()

    return render_template(
        "opportunities.html",
        opportunities=opportunities_list,
        search=search
    )


@app.route(
    "/opportunities/create",
    methods=["GET", "POST"]
)
@login_required
def create_opportunity():

    customers_list = Customer.query.order_by(
        Customer.name
    ).all()

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        customer_id = request.form.get(
            "customer_id"
        )

        stage = request.form.get(
            "stage",
            "Qualification"
        ).strip()

        amount_text = request.form.get(
            "amount",
            ""
        ).strip()

        probability_text = request.form.get(
            "probability",
            ""
        ).strip()

        expected_close_text = request.form.get(
            "expected_close",
            ""
        ).strip()

        source = request.form.get(
            "source",
            ""
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        try:
            amount = float(amount_text)
            probability = float(probability_text)
        except ValueError:

            flash(
                "Amount and probability must be valid numbers.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=None,
                customers=customers_list,
                edit_mode=False
            )

        if not name or not customer_id:

            flash(
                "Opportunity name and customer are required.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=None,
                customers=customers_list,
                edit_mode=False
            )

        if amount <= 0:

            flash(
                "Opportunity amount must be greater than 0.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=None,
                customers=customers_list,
                edit_mode=False
            )

        if probability < 0 or probability > 100:

            flash(
                "Probability must be between 0 and 100.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=None,
                customers=customers_list,
                edit_mode=False
            )

        allowed_stages = [
            "Qualification",
            "Proposal",
            "Negotiation",
            "Won",
            "Lost"
        ]

        if stage not in allowed_stages:

            flash(
                "Invalid opportunity stage.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=None,
                customers=customers_list,
                edit_mode=False
            )

        expected_close = None

        if expected_close_text:

            try:

                expected_close = datetime.strptime(
                    expected_close_text,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                flash(
                    "Invalid expected close date.",
                    "danger"
                )

                return render_template(
                    "opportunity_form.html",
                    opportunity=None,
                    customers=customers_list,
                    edit_mode=False
                )

        if (
            stage not in ["Won", "Lost"]
            and expected_close
            and expected_close < date.today()
        ):

            flash(
                "Expected close date cannot be in the past for active opportunities.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=None,
                customers=customers_list,
                edit_mode=False
            )

        opportunity = Opportunity(
            name=name,
            customer_id=int(customer_id),
            owner_id=current_user.id,
            stage=stage,
            amount=amount,
            probability=probability,
            expected_close=expected_close,
            source=source,
            notes=notes
        )

        db.session.add(opportunity)

        db.session.flush()

        create_audit(
            action="CREATE",
            module="Opportunity",
            result="SUCCESS",
            record_id=opportunity.id,
            details=f"Opportunity created: {opportunity.name}"
        )

        db.session.commit()

        flash(
            "Opportunity created successfully.",
            "success"
        )

        return redirect(
            url_for("opportunities")
        )

    return render_template(
        "opportunity_form.html",
        opportunity=None,
        customers=customers_list,
        edit_mode=False
    )


@app.route(
    "/opportunities/edit/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def edit_opportunity(id):

    opportunity = db.session.get(
        Opportunity,
        id
    )

    if not opportunity:
        abort(404)

    customers_list = Customer.query.order_by(
        Customer.name
    ).all()

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        customer_id = request.form.get(
            "customer_id"
        )

        stage = request.form.get(
            "stage",
            "Qualification"
        ).strip()

        amount_text = request.form.get(
            "amount",
            ""
        ).strip()

        probability_text = request.form.get(
            "probability",
            ""
        ).strip()

        expected_close_text = request.form.get(
            "expected_close",
            ""
        ).strip()

        source = request.form.get(
            "source",
            ""
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        try:

            amount = float(amount_text)
            probability = float(probability_text)

        except ValueError:

            flash(
                "Amount and probability must be valid numbers.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=opportunity,
                customers=customers_list,
                edit_mode=True
            )

        if not name or not customer_id:

            flash(
                "Opportunity name and customer are required.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=opportunity,
                customers=customers_list,
                edit_mode=True
            )

        if amount <= 0:

            flash(
                "Opportunity amount must be greater than 0.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=opportunity,
                customers=customers_list,
                edit_mode=True
            )

        if probability < 0 or probability > 100:

            flash(
                "Probability must be between 0 and 100.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=opportunity,
                customers=customers_list,
                edit_mode=True
            )

        allowed_stages = [
            "Qualification",
            "Proposal",
            "Negotiation",
            "Won",
            "Lost"
        ]

        if stage not in allowed_stages:

            flash(
                "Invalid opportunity stage.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=opportunity,
                customers=customers_list,
                edit_mode=True
            )

        expected_close = None

        if expected_close_text:

            try:

                expected_close = datetime.strptime(
                    expected_close_text,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                flash(
                    "Invalid expected close date.",
                    "danger"
                )

                return render_template(
                    "opportunity_form.html",
                    opportunity=opportunity,
                    customers=customers_list,
                    edit_mode=True
                )

        if (
            stage not in ["Won", "Lost"]
            and expected_close
            and expected_close < date.today()
        ):

            flash(
                "Expected close date cannot be in the past for active opportunities.",
                "danger"
            )

            return render_template(
                "opportunity_form.html",
                opportunity=opportunity,
                customers=customers_list,
                edit_mode=True
            )

        old_stage = opportunity.stage

        opportunity.name = name
        opportunity.customer_id = int(customer_id)
        opportunity.stage = stage
        opportunity.amount = amount
        opportunity.probability = probability
        opportunity.expected_close = expected_close
        opportunity.source = source
        opportunity.notes = notes

        create_audit(
            action="UPDATE",
            module="Opportunity",
            result="SUCCESS",
            record_id=opportunity.id,
            details=f"Opportunity updated: {opportunity.name}"
        )

        if old_stage != stage:

            create_audit(
                action="STAGE_CHANGE",
                module="Opportunity",
                result="SUCCESS",
                record_id=opportunity.id,
                details=(
                    f"Stage changed from "
                    f"{old_stage} to {stage}"
                )
            )

        db.session.commit()

        flash(
            "Opportunity updated successfully.",
            "success"
        )

        return redirect(
            url_for("opportunities")
        )

    return render_template(
        "opportunity_form.html",
        opportunity=opportunity,
        customers=customers_list,
        edit_mode=True
    )


@app.route(
    "/opportunities/delete/<int:id>",
    methods=["POST"]
)
@login_required
def delete_opportunity(id):

    opportunity = db.session.get(
        Opportunity,
        id
    )

    if not opportunity:
        abort(404)

    opportunity_name = opportunity.name

    create_audit(
        action="DELETE",
        module="Opportunity",
        result="SUCCESS",
        record_id=opportunity.id,
        details=f"Opportunity deleted: {opportunity_name}"
    )

    db.session.delete(opportunity)

    db.session.commit()

    flash(
        "Opportunity deleted successfully.",
        "success"
    )

    return redirect(
        url_for("opportunities")
    )


# ============================================================
# FOLLOW-UPS
# ============================================================

@app.route("/followups")
@login_required
def followups():

    search = request.args.get(
        "search",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()

    query = FollowUp.query

    if search:

        search_pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                FollowUp.subject.ilike(search_pattern),
                FollowUp.type.ilike(search_pattern),
                FollowUp.notes.ilike(search_pattern)
            )
        )

    if status:

        query = query.filter(
            FollowUp.status == status
        )

    followups_list = query.order_by(
        FollowUp.date.asc()
    ).all()

    return render_template(
        "followups.html",
        followups=followups_list,
        search=search,
        status=status
    )


@app.route(
    "/followups/create",
    methods=["GET", "POST"]
)
@login_required
def create_followup():

    customers_list = Customer.query.order_by(
        Customer.name
    ).all()

    leads_list = Lead.query.order_by(
        Lead.name
    ).all()

    if request.method == "POST":

        customer_id = request.form.get(
            "customer_id"
        )

        lead_id = request.form.get(
            "lead_id"
        )

        date_text = request.form.get(
            "date",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        followup_type = request.form.get(
            "type",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Planned"
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        if not date_text or not subject or not followup_type:

            flash(
                "Date, subject, and type are required.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=None,
                customers=customers_list,
                leads=leads_list,
                edit_mode=False
            )

        try:

            followup_date = datetime.strptime(
                date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid follow-up date.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=None,
                customers=customers_list,
                leads=leads_list,
                edit_mode=False
            )

        if followup_date < date.today():

            flash(
                "Follow-up date cannot be in the past.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=None,
                customers=customers_list,
                leads=leads_list,
                edit_mode=False
            )

        allowed_types = [
            "Call",
            "Meeting",
            "Email",
            "Task"
        ]

        allowed_statuses = [
            "Planned",
            "Completed",
            "Missed",
            "Cancelled"
        ]

        if followup_type not in allowed_types:

            flash(
                "Invalid follow-up type.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=None,
                customers=customers_list,
                leads=leads_list,
                edit_mode=False
            )

        if status not in allowed_statuses:

            flash(
                "Invalid follow-up status.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=None,
                customers=customers_list,
                leads=leads_list,
                edit_mode=False
            )

        if customer_id and lead_id:

            flash(
                "Select either a customer or a lead, not both.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=None,
                customers=customers_list,
                leads=leads_list,
                edit_mode=False
            )

        if not customer_id and not lead_id:

            flash(
                "Select either a customer or a lead.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=None,
                customers=customers_list,
                leads=leads_list,
                edit_mode=False
            )

        followup = FollowUp(
            customer_id=int(customer_id)
            if customer_id else None,

            lead_id=int(lead_id)
            if lead_id else None,

            date=followup_date,
            subject=subject,
            type=followup_type,
            status=status,
            notes=notes,
            user_id=current_user.id
        )

        db.session.add(followup)

        db.session.flush()

        create_audit(
            action="CREATE",
            module="FollowUp",
            result="SUCCESS",
            record_id=followup.id,
            details=f"Follow-up created: {followup.subject}"
        )

        db.session.commit()

        flash(
            "Follow-up created successfully.",
            "success"
        )

        return redirect(
            url_for("followups")
        )

    return render_template(
        "followup_form.html",
        followup=None,
        customers=customers_list,
        leads=leads_list,
        edit_mode=False
    )


@app.route(
    "/followups/edit/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def edit_followup(id):

    followup = db.session.get(
        FollowUp,
        id
    )

    if not followup:
        abort(404)

    customers_list = Customer.query.order_by(
        Customer.name
    ).all()

    leads_list = Lead.query.order_by(
        Lead.name
    ).all()

    if request.method == "POST":

        customer_id = request.form.get(
            "customer_id"
        )

        lead_id = request.form.get(
            "lead_id"
        )

        date_text = request.form.get(
            "date",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        followup_type = request.form.get(
            "type",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Planned"
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        try:

            followup_date = datetime.strptime(
                date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid follow-up date.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=followup,
                customers=customers_list,
                leads=leads_list,
                edit_mode=True
            )

        if not subject:

            flash(
                "Subject is required.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=followup,
                customers=customers_list,
                leads=leads_list,
                edit_mode=True
            )

        allowed_types = [
            "Call",
            "Meeting",
            "Email",
            "Task"
        ]

        allowed_statuses = [
            "Planned",
            "Completed",
            "Missed",
            "Cancelled"
        ]

        if followup_type not in allowed_types:

            flash(
                "Invalid follow-up type.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=followup,
                customers=customers_list,
                leads=leads_list,
                edit_mode=True
            )

        if status not in allowed_statuses:

            flash(
                "Invalid follow-up status.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=followup,
                customers=customers_list,
                leads=leads_list,
                edit_mode=True
            )

        if customer_id and lead_id:

            flash(
                "Select either a customer or a lead, not both.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=followup,
                customers=customers_list,
                leads=leads_list,
                edit_mode=True
            )

        if not customer_id and not lead_id:

            flash(
                "Select either a customer or a lead.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=followup,
                customers=customers_list,
                leads=leads_list,
                edit_mode=True
            )

        if (
            status == "Planned"
            and followup_date < date.today()
        ):

            flash(
                "A planned follow-up cannot have a past date.",
                "danger"
            )

            return render_template(
                "followup_form.html",
                followup=followup,
                customers=customers_list,
                leads=leads_list,
                edit_mode=True
            )

        old_status = followup.status
        old_date = followup.date

        followup.customer_id = (
            int(customer_id)
            if customer_id
            else None
        )

        followup.lead_id = (
            int(lead_id)
            if lead_id
            else None
        )

        followup.date = followup_date
        followup.subject = subject
        followup.type = followup_type
        followup.status = status
        followup.notes = notes

        create_audit(
            action="UPDATE",
            module="FollowUp",
            result="SUCCESS",
            record_id=followup.id,
            details=f"Follow-up updated: {followup.subject}"
        )

        if old_status != status:

            create_audit(
                action="STATUS_CHANGE",
                module="FollowUp",
                result="SUCCESS",
                record_id=followup.id,
                details=(
                    f"Status changed from "
                    f"{old_status} to {status}"
                )
            )

        if old_date != followup_date:

            create_audit(
                action="RESCHEDULE",
                module="FollowUp",
                result="SUCCESS",
                record_id=followup.id,
                details=(
                    f"Date changed from "
                    f"{old_date} to {followup_date}"
                )
            )

        db.session.commit()

        flash(
            "Follow-up updated successfully.",
            "success"
        )

        return redirect(
            url_for("followups")
        )

    return render_template(
        "followup_form.html",
        followup=followup,
        customers=customers_list,
        leads=leads_list,
        edit_mode=True
    )


@app.route(
    "/followups/delete/<int:id>",
    methods=["POST"]
)
@login_required
def delete_followup(id):

    followup = db.session.get(
        FollowUp,
        id
    )

    if not followup:
        abort(404)

    subject = followup.subject

    create_audit(
        action="DELETE",
        module="FollowUp",
        result="SUCCESS",
        record_id=followup.id,
        details=f"Follow-up deleted: {subject}"
    )

    db.session.delete(followup)

    db.session.commit()

    flash(
        "Follow-up deleted successfully.",
        "success"
    )

    return redirect(
        url_for("followups")
    )


# ============================================================
# ACTIVITIES
# ============================================================

@app.route("/activities")
@login_required
def activities():

    activities_list = Activity.query.order_by(
        Activity.date.desc()
    ).all()

    return render_template(
        "activities.html",
        activities=activities_list
    )


@app.route(
    "/activities/create",
    methods=["GET", "POST"]
)
@login_required
def create_activity():

    customers_list = Customer.query.order_by(
        Customer.name
    ).all()

    leads_list = Lead.query.order_by(
        Lead.name
    ).all()

    if request.method == "POST":

        customer_id = request.form.get(
            "customer_id"
        )

        lead_id = request.form.get(
            "lead_id"
        )

        activity_type = request.form.get(
            "type",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        date_text = request.form.get(
            "date",
            ""
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        if customer_id and lead_id:

            flash(
                "Select either a customer or a lead, not both.",
                "danger"
            )

            return render_template(
                "activity_form.html",
                customers=customers_list,
                leads=leads_list
            )

        if not customer_id and not lead_id:

            flash(
                "Select either a customer or a lead.",
                "danger"
            )

            return render_template(
                "activity_form.html",
                customers=customers_list,
                leads=leads_list
            )

        if not activity_type or not subject or not date_text:

            flash(
                "Type, subject, and date are required.",
                "danger"
            )

            return render_template(
                "activity_form.html",
                customers=customers_list,
                leads=leads_list
            )

        try:

            activity_date = datetime.strptime(
                date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid activity date.",
                "danger"
            )

            return render_template(
                "activity_form.html",
                customers=customers_list,
                leads=leads_list
            )

        allowed_types = [
            "Call",
            "Meeting",
            "Email",
            "Task"
        ]

        if activity_type not in allowed_types:

            flash(
                "Invalid activity type.",
                "danger"
            )

            return render_template(
                "activity_form.html",
                customers=customers_list,
                leads=leads_list
            )

        activity = Activity(
            customer_id=int(customer_id)
            if customer_id
            else None,

            lead_id=int(lead_id)
            if lead_id
            else None,

            type=activity_type,
            subject=subject,
            date=activity_date,
            notes=notes,
            user_id=current_user.id
        )

        db.session.add(activity)

        db.session.flush()

        create_audit(
            action="CREATE",
            module="Activity",
            result="SUCCESS",
            record_id=activity.id,
            details=f"Activity created: {activity.subject}"
        )

        db.session.commit()

        flash(
            "Activity created successfully.",
            "success"
        )

        return redirect(
            url_for("activities")
        )

    return render_template(
        "activity_form.html",
        customers=customers_list,
        leads=leads_list
    )


@app.route(
    "/activities/delete/<int:id>",
    methods=["POST"]
)
@login_required
def delete_activity(id):

    activity = db.session.get(
        Activity,
        id
    )

    if not activity:
        abort(404)

    subject = activity.subject

    create_audit(
        action="DELETE",
        module="Activity",
        result="SUCCESS",
        record_id=activity.id,
        details=f"Activity deleted: {subject}"
    )

    db.session.delete(activity)

    db.session.commit()

    flash(
        "Activity deleted successfully.",
        "success"
    )

    return redirect(
        url_for("activities")
    )


# ============================================================
# ADMIN - USERS
# ============================================================

@app.route("/users")
@login_required
def users():

    check = admin_required()

    if check:
        return check

    users_list = User.query.order_by(
        User.id.desc()
    ).all()

    return render_template(
        "users.html",
        users=users_list
    )


@app.route(
    "/users/create",
    methods=["GET", "POST"]
)
@login_required
def create_user():

    check = admin_required()

    if check:
        return check

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        role = request.form.get(
            "role",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        allowed_roles = [
            "Admin",
            "Manager",
            "Sales Executive"
        ]

        if not name or not email or not role or not password:

            flash(
                "All required fields must be filled.",
                "danger"
            )

            return render_template(
                "user_form.html"
            )

        if not valid_email(email):

            flash(
                "Invalid email address.",
                "danger"
            )

            return render_template(
                "user_form.html"
            )

        if role not in allowed_roles:

            flash(
                "Invalid role.",
                "danger"
            )

            return render_template(
                "user_form.html"
            )

        if not valid_password(password):

            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )

            return render_template(
                "user_form.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "user_form.html"
            )

        if User.query.filter_by(
            email=email
        ).first():

            flash(
                "A user with this email already exists.",
                "danger"
            )

            return render_template(
                "user_form.html"
            )

        user = User(
            name=name,
            email=email,
            password_hash=bcrypt.generate_password_hash(
                password
            ).decode("utf-8"),
            role=role,
            is_active=True
        )

        db.session.add(user)

        db.session.flush()

        create_audit(
            action="CREATE",
            module="User",
            result="SUCCESS",
            record_id=user.id,
            details=(
                f"User created with role {role}: {email}"
            )
        )

        db.session.commit()

        flash(
            "User created successfully.",
            "success"
        )

        return redirect(
            url_for("users")
        )

    return render_template(
        "user_form.html"
    )


@app.route(
    "/users/toggle/<int:id>",
    methods=["POST"]
)
@login_required
def toggle_user(id):

    check = admin_required()

    if check:
        return check

    user = db.session.get(
        User,
        id
    )

    if not user:
        abort(404)

    if user.id == current_user.id:

        flash(
            "You cannot deactivate your own account.",
            "danger"
        )

        return redirect(
            url_for("users")
        )

    user.is_active = not user.is_active

    action = (
        "ACTIVATE"
        if user.is_active
        else "DEACTIVATE"
    )

    create_audit(
        action=action,
        module="User",
        result="SUCCESS",
        record_id=user.id,
        details=f"User status changed: {user.email}"
    )

    db.session.commit()

    flash(
        "User status updated successfully.",
        "success"
    )

    return redirect(
        url_for("users")
    )


# ============================================================
# AUDIT LOGS
# ============================================================

@app.route("/audit")
@login_required
def audit_logs():

    check = admin_required()

    if check:
        return check

    audit_logs_list = AuditLog.query.order_by(
        AuditLog.timestamp.desc()
    ).all()

    return render_template(
        "audit.html",
        audit_logs=audit_logs_list
    )


# ============================================================
# REPORTS
# ============================================================

@app.route("/reports")
@login_required
def reports():

    report_type = request.args.get(
        "report_type",
        "overview"
    )

    search = request.args.get(
        "search",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    customer_count = Customer.query.count()

    lead_count = Lead.query.count()

    opportunity_count = Opportunity.query.count()

    followup_count = FollowUp.query.count()

    opportunities_list = Opportunity.query.all()

    pipeline_value = sum(
        (opportunity.amount or 0)
        for opportunity in opportunities_list
    )

    weighted_pipeline = sum(
        (opportunity.amount or 0)
        * (opportunity.probability or 0)
        / 100
        for opportunity in opportunities_list
    )

    # --------------------------------------------------------
    # Defaults
    # --------------------------------------------------------

    report_data = []

    report_title = "CRM Reporting Overview"

    report_description = (
        "Select a report type to view detailed CRM information."
    )

    conversion_total = 0
    conversion_converted = 0
    conversion_rate = 0

    # --------------------------------------------------------
    # Customer Report
    # --------------------------------------------------------

    if report_type == "customers":

        report_title = "Customer Report"

        report_description = (
            "Customer information, status, contact details, "
            "and assigned sales executive."
        )

        query = Customer.query

        if search:

            search_pattern = f"%{search}%"

            query = query.filter(
                db.or_(
                    Customer.name.ilike(search_pattern),
                    Customer.email.ilike(search_pattern),
                    Customer.phone.ilike(search_pattern)
                )
            )

        if status:

            query = query.filter(
                Customer.status == status
            )

        report_data = query.order_by(
            Customer.id.desc()
        ).all()

    # --------------------------------------------------------
    # Lead Report
    # --------------------------------------------------------

    elif report_type == "leads":

        report_title = "Lead Report"

        report_description = (
            "Lead source, contact details, status, "
            "priority, and ownership information."
        )

        query = Lead.query

        if search:

            search_pattern = f"%{search}%"

            query = query.filter(
                db.or_(
                    Lead.name.ilike(search_pattern),
                    Lead.email.ilike(search_pattern),
                    Lead.phone.ilike(search_pattern),
                    Lead.source.ilike(search_pattern)
                )
            )

        if status:

            query = query.filter(
                Lead.status == status
            )

        report_data = query.order_by(
            Lead.id.desc()
        ).all()

    # --------------------------------------------------------
    # Follow-Up Report
    # --------------------------------------------------------

    elif report_type == "followups":

        report_title = "Follow-Up Report"

        report_description = (
            "Planned, completed, missed, and cancelled "
            "follow-up activities."
        )

        query = FollowUp.query

        if search:

            search_pattern = f"%{search}%"

            query = query.filter(
                db.or_(
                    FollowUp.subject.ilike(search_pattern),
                    FollowUp.type.ilike(search_pattern),
                    FollowUp.notes.ilike(search_pattern)
                )
            )

        if status:

            query = query.filter(
                FollowUp.status == status
            )

        report_data = query.order_by(
            FollowUp.date.asc()
        ).all()

    # --------------------------------------------------------
    # Opportunity Report
    # --------------------------------------------------------

    elif report_type == "opportunities":

        report_title = "Opportunity Report"

        report_description = (
            "Opportunity stage, amount, probability, "
            "weighted value, owner, and expected close date."
        )

        query = Opportunity.query

        if search:

            search_pattern = f"%{search}%"

            query = query.filter(
                db.or_(
                    Opportunity.name.ilike(search_pattern),
                    Opportunity.source.ilike(search_pattern),
                    Opportunity.notes.ilike(search_pattern)
                )
            )

        if status:

            query = query.filter(
                Opportunity.stage == status
            )

        report_data = query.order_by(
            Opportunity.id.desc()
        ).all()

    # --------------------------------------------------------
    # Pipeline Report
    # --------------------------------------------------------

    elif report_type == "pipeline":

        report_title = "Pipeline Report"

        report_description = (
            "Opportunity pipeline with weighted pipeline "
            "calculated from amount and probability."
        )

        query = Opportunity.query

        if search:

            search_pattern = f"%{search}%"

            query = query.filter(
                db.or_(
                    Opportunity.name.ilike(search_pattern),
                    Opportunity.source.ilike(search_pattern)
                )
            )

        if status:

            query = query.filter(
                Opportunity.stage == status
            )

        report_data = query.order_by(
            Opportunity.amount.desc()
        ).all()

    # --------------------------------------------------------
    # Conversion Report
    # --------------------------------------------------------

    elif report_type == "conversion":

        report_title = "Lead Conversion Report"

        report_description = (
            "Lead conversion performance based on "
            "the current lead status."
        )

        conversion_total = Lead.query.count()

        conversion_converted = Lead.query.filter_by(
            status="Converted"
        ).count()

        if conversion_total > 0:

            conversion_rate = (
                conversion_converted
                / conversion_total
                * 100
            )

    # --------------------------------------------------------
    # User Activity Report
    # --------------------------------------------------------

    elif report_type == "user_activity":

        report_title = "User Activity Report"

        report_description = (
            "Number of recorded CRM activities created "
            "by each user."
        )

        activities_list = Activity.query.all()

        activity_counts = {}

        for activity in activities_list:

            if activity.user:

                user_name = (
                    activity.user.name
                    or activity.user.email
                )

            else:

                user_name = "Unknown"

            activity_counts[user_name] = (
                activity_counts.get(
                    user_name,
                    0
                ) + 1
            )

        report_data = [
            {
                "user": user,
                "count": count
            }

            for user, count
            in sorted(
                activity_counts.items(),
                key=lambda item: item[1],
                reverse=True
            )
        ]

    # --------------------------------------------------------
    # Audit Report
    # --------------------------------------------------------

    elif report_type == "audit":

        report_title = "Audit Report"

        report_description = (
            "System audit records including user, action, "
            "module, result, and timestamp."
        )

        query = AuditLog.query

        if search:

            search_pattern = f"%{search}%"

            query = query.filter(
                db.or_(
                    AuditLog.action.ilike(search_pattern),
                    AuditLog.module.ilike(search_pattern),
                    AuditLog.result.ilike(search_pattern),
                    AuditLog.details.ilike(search_pattern)
                )
            )

        report_data = query.order_by(
            AuditLog.timestamp.desc()
        ).all()

    # --------------------------------------------------------
    # Render
    # --------------------------------------------------------

    return render_template(
        "reports.html",

        customer_count=customer_count,
        lead_count=lead_count,
        opportunity_count=opportunity_count,
        followup_count=followup_count,

        pipeline_value=pipeline_value,
        weighted_pipeline=weighted_pipeline,

        report_type=report_type,
        report_title=report_title,
        report_description=report_description,
        report_data=report_data,

        search=search,
        status=status,

        conversion_total=conversion_total,
        conversion_converted=conversion_converted,
        conversion_rate=conversion_rate
    )


# ============================================================
# REST API - CUSTOMERS
# ============================================================

@app.route(
    "/api/customers",
    methods=["GET"]
)
@login_required
def api_customers():

    customers_list = Customer.query.order_by(
        Customer.id.desc()
    ).all()

    return jsonify([
        {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "address": customer.address,
            "status": customer.status,
            "assigned_to_id": customer.assigned_to_id,
            "notes": customer.notes,
            "created_at": (
                customer.created_at.isoformat()
                if customer.created_at
                else None
            )
        }

        for customer in customers_list
    ]), 200


@app.route(
    "/api/customers",
    methods=["POST"]
)
@login_required
def api_create_customer():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "error": "JSON request body is required."
        }), 400

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    phone = str(
        data.get("phone", "")
    ).strip()

    address = str(
        data.get("address", "")
    ).strip()

    status = str(
        data.get("status", "Active")
    ).strip()

    notes = str(
        data.get("notes", "")
    ).strip()

    if not name or not email or not phone:

        return jsonify({
            "error": "Name, email, and phone are required."
        }), 400

    if not valid_email(email):

        return jsonify({
            "error": "Invalid email address."
        }), 400

    if not valid_phone(phone):

        return jsonify({
            "error": "Phone number must contain 10 to 15 digits."
        }), 400

    if Customer.query.filter_by(
        email=email
    ).first():

        return jsonify({
            "error": "Customer email already exists."
        }), 409

    if Customer.query.filter_by(
        phone=phone
    ).first():

        return jsonify({
            "error": "Customer phone already exists."
        }), 409

    customer = Customer(
        name=name,
        email=email,
        phone=phone,
        address=address,
        status=status,
        assigned_to_id=current_user.id,
        notes=notes
    )

    db.session.add(customer)

    db.session.flush()

    create_audit(
        action="CREATE",
        module="Customer API",
        result="SUCCESS",
        record_id=customer.id,
        details="Customer created through API"
    )

    db.session.commit()

    return jsonify({
        "message": "Customer created successfully.",
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "status": customer.status
        }
    }), 201


# ============================================================
# REST API - LEADS
# ============================================================

@app.route(
    "/api/leads",
    methods=["GET"]
)
@login_required
def api_leads():

    leads_list = Lead.query.order_by(
        Lead.id.desc()
    ).all()

    return jsonify([
        {
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "source": lead.source,
            "status": lead.status,
            "priority": lead.priority,
            "owner_id": lead.owner_id,
            "notes": lead.notes,
            "created_at": (
                lead.created_at.isoformat()
                if lead.created_at
                else None
            )
        }

        for lead in leads_list
    ]), 200


# ============================================================
# REST API - OPPORTUNITIES
# ============================================================

@app.route(
    "/api/opportunities",
    methods=["GET"]
)
@login_required
def api_opportunities():

    opportunities_list = Opportunity.query.order_by(
        Opportunity.id.desc()
    ).all()

    return jsonify([
        {
            "id": opportunity.id,
            "name": opportunity.name,
            "customer_id": opportunity.customer_id,
            "owner_id": opportunity.owner_id,
            "stage": opportunity.stage,
            "amount": opportunity.amount,
            "probability": opportunity.probability,
            "weighted_pipeline": (
                (opportunity.amount or 0)
                * (opportunity.probability or 0)
                / 100
            ),
            "expected_close": (
                opportunity.expected_close.isoformat()
                if opportunity.expected_close
                else None
            ),
            "source": opportunity.source,
            "notes": opportunity.notes,
            "created_at": (
                opportunity.created_at.isoformat()
                if opportunity.created_at
                else None
            )
        }

        for opportunity in opportunities_list
    ]), 200


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(403)
def forbidden(error):

    return render_template(
        "base.html"
    ), 403


@app.errorhandler(404)
def not_found(error):

    return """
    <h1>404 - Page Not Found</h1>
    <p>The requested page does not exist.</p>
    """, 404


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    db.create_all()

    admin_email = "admin@acxiomcrm.com"

    admin = User.query.filter_by(
        email=admin_email
    ).first()

    if not admin:

        admin = User(
            name="System Administrator",
            email=admin_email,
            password_hash=bcrypt.generate_password_hash(
                "Admin@123"
            ).decode("utf-8"),
            role="Admin",
            is_active=True
        )

        db.session.add(admin)

        db.session.flush()

        create_audit(
            action="SYSTEM_INITIALIZATION",
            module="Authentication",
            result="SUCCESS",
            record_id=admin.id,
            details="Default administrator account created.",
            user_id=admin.id
        )

        db.session.commit()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    with app.app_context():
        initialize_database()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )