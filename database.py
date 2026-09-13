import mysql.connector
from mysql.connector import errorcode
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    """Establish and return a MySQL connection using configured credentials."""
    try:
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False
        )
        return connection
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            # Database does not exist yet; try connecting without database to create it
            temp_conn = mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            temp_cursor = temp_conn.cursor()
            temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            temp_cursor.close()
            temp_conn.close()
            # Retry connecting to the created database
            return mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci"
            )
        raise err

def query_db(query, args=(), one=False):
    """Execute a parameterized SELECT query and return results as dictionaries."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, args)
        result = cursor.fetchall()
        cursor.close()
        return (result[0] if result else None) if one else result
    finally:
        conn.close()

def execute_db(query, args=(), commit=True):
    """Execute a parameterized INSERT, UPDATE, or DELETE query and optionally commit."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, args)
        last_id = cursor.lastrowid
        rowcount = cursor.rowcount
        if commit:
            conn.commit()
        cursor.close()
        return {"last_id": last_id, "rowcount": rowcount}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def log_audit(claim_id=None, item_type=None, item_id=None, user_id=None, action="", notes=None):
    """Insert an entry into claim_audit_logs for security tracking."""
    sql = """
        INSERT INTO claim_audit_logs (claim_id, item_type, item_id, user_id, action, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    execute_db(sql, (claim_id, item_type, item_id, user_id, action, notes))

def create_notification(user_id, title, message, link=None):
    """Create a user notification regarding status updates."""
    sql = """
        INSERT INTO notifications (user_id, title, message, link, is_read)
        VALUES (%s, %s, %s, %s, 0)
    """
    execute_db(sql, (user_id, title, message, link))

def init_admin_user():
    """Ensure the default administrator account exists with secure password hash."""
    admin = query_db("SELECT id FROM users WHERE email = %s", (Config.ADMIN_EMAIL,), one=True)
    if not admin:
        hashed_password = generate_password_hash(Config.ADMIN_PASSWORD, method="scrypt")
        sql = """
            INSERT INTO users (full_name, email, phone, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, 'admin', 1)
        """
        execute_db(sql, (Config.ADMIN_NAME, Config.ADMIN_EMAIL, Config.ADMIN_PHONE, hashed_password))
        print(f"Default administrator initialized: {Config.ADMIN_EMAIL}")
    else:
        # Ensure role is admin
        execute_db("UPDATE users SET role = 'admin' WHERE email = %s", (Config.ADMIN_EMAIL,))
