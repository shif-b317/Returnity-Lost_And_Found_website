# RETURNITY: Lost and Found Management System

> "Lost it? Return to it."
> Lost and Found for a kinder tomorrow.

RETURNITY is a modern, full-stack Lost and Found Management Platform developed with Python 3, Flask, and MySQL. It solves the vulnerability of conventional lost and found notice boards by segregating publicly visible listing attributes from confidential ownership verification markers, integrating a rule-based decision support scoring system, and empowering authorized administrators to evaluate claims with an immutable audit trail.

---
##Links
Website Link: http://127.0.0.1:5000
Admin Login URL: http://127.0.0.1:5000/admin/login

---

## 1. Key Platform Features

- **Split Information Division Architecture:**
  - **Public Information:** Item title, category, general location, approximate date, and exterior photographs are visible to community members.
  - **Private Verification Information:** Confidential identifying markers (internal markings, hidden scratches, specific contents, serial numbers, exact location) are encrypted in the database and never shown publicly or to claimants.
- **Rule-Based Claim Verification Engine:**
  - Calculates a transparent Claim Verification Score (0 to 100 points) based on objective criteria (location alignment, date proximity, private feature accuracy, distinctive marks, and uploaded purchase receipts).
  - Categorizes claims into confidence tiers: **Strong Verification (80-100)**, **Needs Review (60-79)**, and **Low Confidence (<60)**.
- **Suspicious Activity & Anomaly Detection:**
  - Automatically flags rapid claim velocity (3 or more claims within 24 hours).
  - Detects claimants with repeated rejected claim histories.
  - Penalizes submissions that merely regurgitate words from the public description.
  - Places items with multiple competing claimants into a dedicated review queue.
- **Isolated Evidence Storage:**
  - Sensitive ownership documents (purchase receipts, invoices, warranty documents) are saved in an isolated storage directory (`uploads/evidence/`) outside the public web root.
  - Documents are served strictly through a protected route (`/evidence/<filename>`) requiring administrative clearance or proof of claim ownership.
- **Rule-Based Cross-Match Engine:**
  - Automatically checks active lost and found reports using category matching, keyword overlap, location alignment, and date proximity.
- **Administrative Operations Console:**
  - Real-time live database metrics: total users, lost reports, found reports, pending claims, and items needing review.
  - Verification review interface comparing claimant answers directly against stored private markers.
  - Administrative actions: Approve, Reject, Request More Information, or Keep Under Review.
  - User management, item management, and category administration.
- **Security & Complete Audit Logging:**
  - Immutable historical audit logs recording all registrations, logins, reports, claim filings, administrative decisions, and status transitions.
  - Werkzeug Scrypt password hashing with unique salts.
  - Parameterized SQL queries preventing SQL injection across all database interactions.
  - Server-side session verification with HTTPOnly cookies.

---

## 2. Technology Stack

- **Backend:** Python 3 (Flask 3.x WSGI framework)
- **Database:** MySQL 8.x / MariaDB 10.x
- **Connector:** `mysql-connector-python` (parameterized queries with dictionary cursors)
- **Templating Engine:** Jinja2
- **Authentication & Security:** Flask session management, Werkzeug Scrypt password hashing
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (no external heavy frameworks)
- **Image Processing:** Pillow (for favicon and asset formatting)

---

## 3. Brand Identity & Color Palette

RETURNITY is built around a dedicated, sophisticated brand palette:

| Color Name | HEX Code | RGB Code | Application in Interface |
| :--- | :--- | :--- | :--- |
| **Italian Roast** | `#280B0F` | rgb(40, 11, 15) | Dark hero background, footer, table headers, dark buttons |
| **Tamarind** | `#3B1319` | rgb(54, 19, 25) | Navigation bar, secondary dark cards, section headers |
| **Rubine** | `#8D3A3C` | rgb(141, 58, 60) | Primary call-to-action buttons, active highlights, badges |
| **Boho** | `#7B694E` | rgb(123, 105, 78) | Secondary buttons, borders, subtle callouts |
| **Camel Coat** | `#C6B39A` | rgb(198, 179, 154) | Warm card backgrounds, brand typography, logo accents |

---

## 4. Directory Structure

```text
RETURNITY/
|-- app.py                   # Core Flask application and routing definitions
|-- config.py                # Environment configuration and security constants
|-- database.py              # MySQL connector, connection pooling, and audit logging
|-- verification.py          # Rule-based claim scoring and item matching engine
|-- requirements.txt         # Python package dependencies
|-- schema.sql               # Normalized MySQL database schema with constraints
|-- test_returnity.py        # Automated test suite (14 test cases)
|-- seed_demo_data.py        # Demo listings and initial realistic dataset
|-- .env.example             # Configuration template
|-- .env                     # Local environment variables (git-ignored)
|-- .gitignore               # Version control exclusion rules
|-- README.md                # Comprehensive documentation and deployment guide
|
|-- templates/               # Jinja2 HTML Templates
|   |-- base.html            # Global layout shell with responsive navbar and footer
|   |-- index.html           # Homepage with live listings and workflow steps
|   |-- about.html           # Project background and verification explanation
|   |-- search.html          # Search and filter interface
|   |-- item_details.html    # Safe public detail view and suggested matches
|   |-- claim.html           # Ownership verification questionnaire
|   |-- claim_respond.html   # Response interface for admin inquiries
|   |-- lost.html            # Report lost item (split public and private inputs)
|   |-- found.html           # Report found item (custody location inputs)
|   |-- dashboard.html       # Member dashboard with live database metrics
|   |-- my_reports.html      # Report management (view, edit, delete)
|   |-- edit_report.html     # Report modification form
|   |-- my_claims.html       # Claim tracking and status updates
|   |-- profile.html         # User profile and password update
|   |-- terms.html           # Terms and Conditions
|   |-- privacy.html         # Privacy Policy
|   |-- 403.html             # Access forbidden error template
|   |-- 404.html             # Page not found error template
|   |-- 500.html             # Internal server error template
|   |
|   `-- admin/               # Administrator Console Templates
|       |-- base.html        # Admin console layout with sidebar
|       |-- login.html       # Dedicated administrative authentication
|       |-- dashboard.html   # Operations dashboard with verification queue
|       |-- claims.html      # Claim management with status and risk filters
|       |-- claim_review.html# Detailed review: claimant answers vs private markers
|       |-- reports.html     # Comprehensive report administration
|       |-- lost_items.html  # Lost reports with confidential verification markers
|       |-- found_items.html # Found reports with safe custody locations
|       |-- users.html       # User account governance and suspension toggle
|       |-- audit_logs.html  # Security audit trail
|       `-- settings.html    # System category configuration
|
|-- static/                  # Static Assets
|   |-- css/
|   |   `-- style.css        # Responsive brand stylesheet
|   |-- js/
|   |   `-- script.js        # Vanilla JavaScript (validation, previews, mobile nav)
|   |-- images/
|   |   |-- logo.svg         # Crisp vector SVG brand emblem and wordmark
|   |   |-- logo_icon.svg    # Compact circular emblem icon
|   |   `-- returnity_logo.jpg # Original master brand artwork
|   `-- favicon/
|       |-- favicon.svg      # Vector browser tab favicon
|       |-- favicon.ico      # Standard browser favicon
|       `-- favicon.png      # High-resolution touch icon
|
|-- uploads/                 # Local File Upload Storage
|   |-- items/               # Public exterior photographs
|   `-- evidence/            # Protected sensitive receipts and ownership proof
|
`-- database/                # Database Scripts Directory
    `-- schema.sql           # Schema pointer for reference
```

---

## 5. Installation and Local Setup

### Step 1: Clone or Navigate to the Project Directory
Open your terminal or command prompt:
```bash
cd c:\Users\shifa\OneDrive\Desktop\Returnity
```

### Step 2: Install Python Dependencies
Install all required libraries via pip:
```bash
pip install -r requirements.txt
```

### Step 3: Configure MySQL Database
Make sure your MySQL service is active (for example via XAMPP Control Panel or standalone MySQL service):
- **Default Host:** `localhost`
- **Default Port:** `3306`
- **Default User:** `root`
- **Default Password:** *(blank by default in XAMPP)*

Import the database structure and initial categories:
```bash
python -c "
import mysql.connector
with open('schema.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
conn = mysql.connector.connect(host='localhost', user='root', password='')
cur = conn.cursor()
for stmt in sql.split(';'):
    if stmt.strip():
        cur.execute(stmt.strip())
conn.commit()
cur.close()
conn.close()
print('Database returnity_db initialized successfully!')
"
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` if not already present:
```bash
copy .env.example .env
```
Ensure your database credentials in `.env` match your local setup.

### Step 5: Initialize Admin Account and Demo Listings
Run the seeding script to set up the default administrator and realistic demonstration items:
```bash
python seed_demo_data.py
```

### Step 6: Start the Flask Application
Run the application server:
```bash
python app.py
```
Open your web browser and navigate to:
```text
http://127.0.0.1:5000/
```

---

## 6. Default Administrator Account

An administrator account is automatically initialized upon launch:

- **Portal URL:** `http://127.0.0.1:5000/admin/login`
- **Email:** `admin@returnity.org`
- **Password:** `AdminReturnity2026!`

The administrator can:
1. Review pending verification claims.
2. Compare submitted answers against stored private verification markers.
3. Inspect uploaded ownership receipts through protected links.
4. Execute decisions: **Approve Claim**, **Reject Claim**, or **Request More Information**.
5. Manage user accounts and inspect system audit logs.

---

## 7. Running the Automated Test Suite

The project includes an automated test suite verifying all 14 core functional workflows:
```bash
python test_returnity.py
```
Expected output:
```text
..............
----------------------------------------------------------------------
Ran 14 tests in 2.391s

OK
```

---

## 8. Production Deployment Guide

To transition RETURNITY from a local development environment to a production server (such as Ubuntu Linux on AWS EC2, DigitalOcean, or Linode):

### 1. Production WSGI Server (Gunicorn)
Do not use the Flask built-in development server in production. Install Gunicorn:
```bash
pip install gunicorn
```
Test running Gunicorn:
```bash
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

### 2. Systemd Service Configuration
Create a service unit file at `/etc/systemd/system/returnity.service`:
```ini
[Unit]
Description=RETURNITY Lost and Found Flask Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/returnity
Environment="PATH=/var/www/returnity/venv/bin"
ExecStart=/var/www/returnity/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable returnity
sudo systemctl start returnity
```

### 3. Nginx Reverse Proxy Configuration
Configure Nginx at `/etc/nginx/sites-available/returnity`:
```nginx
server {
    listen 80;
    server_name returnity.org www.returnity.org;

    client_max_body_size 6M;

    # Static assets served directly by Nginx for speed
    location /static/ {
        alias /var/www/returnity/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Public item images
    location /uploads/items/ {
        alias /var/www/returnity/uploads/items/;
        expires 7d;
    }

    # Proxy all application requests and protected evidence routes to Flask
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/returnity /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 9. Custom Domain and HTTPS Setup

To bind your custom domain (e.g., `returnity.org`):

1. **DNS Configuration:**
   - Log into your domain registrar (e.g., Namecheap, GoDaddy, Cloudflare).
   - In DNS Management, add:
     - **Type:** `A` | **Host:** `@` | **Value:** `<Your Server Public IP>` | **TTL:** Auto
     - **Type:** `CNAME` | **Host:** `www` | **Value:** `returnity.org` | **TTL:** Auto
2. **DNS Propagation Check:**
   Verify using terminal:
   ```bash
   nslookup returnity.org
   ```
3. **Obtain Free SSL Certificate via Let's Encrypt Certbot:**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d returnity.org -d www.returnity.org
   ```
   Certbot will automatically modify your Nginx configuration to enforce HTTPS on port 443 with modern TLS protocols and set up automatic certificate renewal.

---

## 10. MCA Project Viva Preparation Guide

Key technical discussion points for project viva:

1. **Problem Statement:**
   Conventional lost and found systems display all item traits openly, enabling dishonest individuals to impersonate owners simply by restating public information.
2. **Our Solution (Dual Division Architecture):**
   When an item is reported, information is partitioned into:
   - *Public Listing:* General attributes aiding community discovery.
   - *Private Verification Markers:* Confidential identifying attributes (micro-scratches, internal contents, serial prefixes) used exclusively to evaluate ownership claims.
3. **Verification Engine Mechanics:**
   Claims are subjected to transparent, rule-based scoring (not an opaque black box). Factors include:
   - Private detail match: +25
   - Distinctive markings match: +20
   - Ownership evidence (invoices, receipts): +20
   - Location alignment: +15
   - Date proximity: +10
   - Contradictions and high velocity submissions: -15 to -20 penalty
4. **Administrative Oversight:**
   The scoring algorithm serves as an objective decision support mechanism. Final approval authority resides with verified administrators.
5. **Database Normalization:**
   Structured 3NF relational schema with 10 tables, explicit foreign keys with cascading deletions, indexes on search fields, and isolated audit logging.
