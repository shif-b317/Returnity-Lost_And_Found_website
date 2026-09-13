# RETURNITY – Lost & Found Management System

> **"Lost it? Return to it."**

A full-stack **Lost & Found Management System** built using **Python, Flask, MySQL, HTML, CSS, and JavaScript**. RETURNITY helps users report lost and found items, securely verify ownership through private verification markers, and manage claims using an admin dashboard with audit logging.

---

## Features

### User Features

* Report lost and found items with images.
* Search and filter items by category, location, and keywords.
* User registration and login.
* Track submitted reports and claims.
* Edit or delete personal reports.

### Claim Verification System

* Secure ownership verification using **private verification markers**.
* Rule-based **Claim Verification Score (0–100)**.
* Upload purchase receipts or supporting evidence.
* Prevents false claims using hidden item identifiers.

### Admin Features

* Dashboard with live statistics.
* Review and approve/reject claims.
* User management.
* Item management.
* Audit logs for administrative actions.

### Security Features

* Password hashing using Werkzeug.
* Parameterized SQL queries to prevent SQL Injection.
* Session-based authentication.
* Protected evidence storage outside the public directory.
* Audit trail for important actions.

---

## Technology Stack

| Technology | Purpose                  |
| ---------- | ------------------------ |
| Python     | Backend Programming      |
| Flask      | Web Framework            |
| MySQL      | Database                 |
| HTML5      | Frontend Structure       |
| CSS3       | Styling                  |
| JavaScript | Client-side Interactions |
| Jinja2     | Template Engine          |
| Pillow     | Image Processing         |

---

## Project Structure

```text
Returnity-Lost_And_Found_website/
├── app.py                  # Main Flask application
├── config.py               # Configuration settings
├── database.py             # Database connection
├── verification.py         # Claim verification engine
├── requirements.txt        # Python dependencies
├── schema.sql              # Database schema
├── seed_demo_data.py       # Demo data seeding
├── README.md               # Project documentation
├── .env.example            # Environment configuration template
│
├── templates/              # HTML templates
│   ├── admin/              # Admin dashboard templates
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── lost.html
│   ├── found.html
│   ├── search.html
│   └── profile.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── uploads/
│   ├── items/
│   └── evidence/
│
└── database/
    └── schema.sql
```

---

## How RETURNITY Works

1. **Report Item** – Users submit lost or found item details.
2. **Public Listing** – Only non-sensitive information is displayed publicly.
3. **Private Verification** – Confidential ownership details remain hidden.
4. **Claim Submission** – Claimants answer ownership verification questions.
5. **Verification Score** – The system evaluates the claim based on predefined rules.
6. **Admin Review** – Administrators approve, reject, or request more information.

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Returnity-Lost_And_Found_website
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

**Windows**

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the environment template.

```bash
copy .env.example .env
```

Update your MySQL credentials inside `.env`.

### 5. Create the Database

Import the database schema into MySQL.

```sql
SOURCE schema.sql;
```

### 6. Seed Demo Data (Optional)

```bash
python seed_demo_data.py
```

### 7. Run the Application

```bash
python app.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

---

## Admin Login

| Field     | Value                               |
| --------- | ----------------------------------- |
| Admin URL | `http://127.0.0.1:5000/admin/login` |
| Email     | `admin@returnity.org`               |
| Password  | `AdminReturnity2026!`               |

---

## Database Highlights

The project uses a normalized MySQL database with tables for:

* Users
* Lost Reports
* Found Reports
* Claims
* Audit Logs
* Categories
* Evidence Records
* Verification Details

Relationships are managed using foreign keys and cascading updates/deletes.

---

## Rule-Based Claim Verification

RETURNITY evaluates ownership claims using a transparent scoring mechanism.

| Verification Factor                 |      Score |
| ----------------------------------- | ---------: |
| Private item details match          |        +25 |
| Distinctive markings match          |        +20 |
| Receipt or ownership proof          |        +20 |
| Location alignment                  |        +15 |
| Date proximity                      |        +10 |
| Suspicious or contradictory answers | -15 to -20 |

### Verification Levels

* **80–100** → Strong Verification
* **60–79** → Needs Manual Review
* **Below 60** → Low Confidence Claim

---

## Testing

Run the automated test suite.

```bash
python test_returnity.py
```

The project includes tests for authentication, report submission, claim verification, search, and admin workflows.

---

## Future Improvements

* AI-based lost/found item matching.
* Email notifications for claim updates.
* OTP verification during claim submission.
* Mobile-responsive enhancements.
* Real-time chat between finder and claimant.

---

## Contributors

* **Bangera Shifali**
* **Aishwarya Baliga B**

---

## License

This project was developed for educational and academic purposes as a full-stack web application demonstrating secure Lost & Found management with claim verification and administrative workflow management.
