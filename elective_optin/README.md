# Priority-Based Elective Opt-In System

A Django web application for fair, transparent elective course allocation in universities.

Students submit ranked preferences (1-3), and the system allocates seats based on a priority algorithm: **CGPA (descending) > Timestamp (ascending) > Preference Rank**. Real-time seat availability is shown via AJAX, and administrators can export allocation reports as CSV.

---

## Core Goal

Build a Django web app for fair, transparent elective course allocation:
- Students submit preferences
- System allocates seats based on priority rules (CGPA / timestamp / branch)
- Real-time seat availability via AJAX

---

## Must-Have Features

| # | Feature | CO Mapped | Django Implementation | Acceptance Criteria |
|---|---------|-----------|----------------------|---------------------|
| 1 | **Elective Registration** | CO2 | `models.py`: `Preference(student, elective, rank)` + validators | Invalid CGPA/rank rejected; preference saved |
| 2 | **Real-Time Seat Counter (AJAX)** | CO5 | `views.py`: `@require_GET def seat_count(...)` + jQuery/fetch | Seat count updates live; reflects allocations |
| 3 | **Allocation Logic** | CO2 + CO4 | `utils.py`: `allocate_electives()` with `order_by('-cgpa', 'submitted_at')` | High-CGPA students get priority; overflow rejected |
| 4 | **Allocation Report (CSV)** | CO4 | `HttpResponse(content_type='text/csv')` + filtered queryset | CSV opens in Excel; filters work |
| 5 | **Responsive UI** | CO3 | Bootstrap 5 + `{% block content %}` | Usable on phone + desktop |

---

## Starter Code Structure

```
elective_optin/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── electives/
│   ├── __init__.py
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── utils.py
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
├── templates/
│   ├── base.html
│   ├── electives/
│   │   ├── landing.html
│   │   ├── catalog.html
│   │   ├── submit.html
│   │   ├── results.html
│   │   ├── student_dashboard.html
│   │   ├── admin_dashboard.html
│   │   └── recommendations.html
│   └── registration/
│       └── login.html
├── static/
│   └── js/
│       └── ajax_seats.js
├── manage.py
├── requirements.txt
└── README.md
```

---

## CO Mapping for README

| CO | How Demonstrated | SDG |
|----|------------------|-----|
| CO1 | URL routing for preferences/allocation/export | SDG 4.3 |
| CO2 | Preference model + validated forms | SDG 4.5 |
| CO3 | Reusable base.html + responsive views | SDG 10.2 |
| CO4 | CSV export with filtered querysets | SDG 16.6 |
| CO5 | AJAX seat counter | SDG 9.C |

---

## SDG Justification

Our Priority-Based Elective Opt-In system advances **SDG 4: Quality Education** (Target 4.5) by implementing a transparent, rule-based allocation algorithm that ensures equitable access to specialized courses regardless of section, background, or submission timing. The CSV export (CO4) supports **SDG 16** (Target 16.6) by providing auditable allocation reports. Built with Django validated forms (CO2) and AJAX seat counters (CO5), the system demonstrates responsive design that reduces bias in academic opportunity distribution while promoting inclusive access to technical education.

---

## Nice-to-Have / Bonus

- Waitlist Auto-Promotion (post_delete signal)
- Branch Quota Enforcement (JSONField)
- Visual Preference Flow (Chart.js)
- Admin Override (Django Admin action)

---

## Out of Scope

- Multi-round counseling
- Real-time chat
- ERP integration
- Demand forecasting
- Payment processing

---

## Local Setup & Installation

### Prerequisites
- Python 3.10+

### 1. Create Virtual Environment

```powershell
# Windows
python -m venv venv
venv\Scripts\activate
```

```bash
# Mac/Linux
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Initialization

```bash
cd elective_optin
python manage.py makemigrations electives
python manage.py migrate
```

### 4. Seed Demo Data (Optional)

```bash
python seed_data.py
```

### 5. Run the Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.

---

## Demo Credentials

**Student Logins:**
- `student1` to `student8`
- Password: `pass123`

**Admin Login:**
- `admin`
- Password: `admin123`

---

## Verification Checklist

- [x] App loads at `http://127.0.0.1:8000`
- [x] Submit valid preference -> saves to DB
- [x] Invalid CGPA/rank -> shows error
- [x] AJAX seat counter updates live
- [x] Allocation logic -> high-CGPA gets priority
- [x] Overflow rejected with clear message
- [x] `/export/?branch=CSE` -> valid CSV
- [x] Mobile view works
- [x] README has CO-SDG + justification

---

## Key URLs

| URL | Purpose | Access |
|-----|---------|--------|
| `/` | Landing page | Public |
| `/catalog/` | Course catalog with live seats | Public |
| `/login/` | Student/Admin login | Public |
| `/submit/` | Submit preferences | Student |
| `/dashboard/` | Student dashboard | Student |
| `/results/` | My allocation result | Student |
| `/admin-dashboard/` | Analytics & run allocation | Admin |
| `/export/` | Download CSV report | Admin |
| `/api/seats/` | Live seat data (all courses) | Public |
| `/api/seats/<id>/` | Live seat data (single course) | Public |

---

## Technology Stack

- **Backend:** Django 4.2+
- **Frontend:** Bootstrap 5, Chart.js (admin dashboard)
- **Database:** SQLite (default)
- **AJAX:** Fetch API with 3-second polling

---

*Built for FA-2 MVP demonstration.*
