# 🎓 Priority-Based Elective Opt-In System

A Django-based web application that enables **fair, transparent, and automated elective course allocation** based on student preferences and priority rules.

---

## 🚀 Overview

This system allows students to:

* Submit elective preferences
* View real-time seat availability
* Get automatically allocated based on merit
* Receive alternative suggestions if a course is full

The platform ensures **fairness, transparency, and efficiency** in elective selection.

---

## 🎯 Problem Statement

Manual elective allocation often leads to:

* Bias and lack of transparency
* First-come-first-serve unfairness
* No proper tracking or reporting

---

## ✅ Solution

This system introduces:

* 📊 Priority-based allocation (CGPA + timestamp)
* ⚡ Real-time seat updates using AJAX
* 🔁 Smart alternative suggestions if course is full
* 📄 CSV export for audit and reporting

---

## 🧠 Core Features

### 1. Elective Registration

* Students submit:

  * Student ID
  * Branch
  * CGPA
  * Preference ranking (1–3)
* Validation ensures correct input

---

### 2. Real-Time Seat Counter (AJAX)

* Displays available seats dynamically
* Updates without page refresh

---

### 3. Allocation Logic

* Priority rules:

  * Higher CGPA first
  * Earlier submission time
  * Optional branch quota

---

### 4. Smart Alternative Suggestions

* If a course is full:

  * System suggests other available electives
  * Improves user experience

---

### 5. CSV Export

* Export allocation results
* Filter by branch or elective
* Useful for faculty review

---

### 6. Responsive UI

* Built with Bootstrap 5
* Works on mobile and desktop

---

## 🏗️ Tech Stack

| Technology        | Purpose           |
| ----------------- | ----------------- |
| Django            | Backend framework |
| SQLite            | Database          |
| Bootstrap 5       | Responsive UI     |
| JavaScript / AJAX | Real-time updates |
| Pandas (optional) | CSV handling      |

---

## 📂 Project Structure

```
elective_optin/
│
├── electives/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── utils.py
│
├── templates/
│   ├── submit.html
│   ├── results.html
│
├── static/
│   └── js/ajax_seats.js
│
├── manage.py
├── requirements.txt
└── README.md
```

---

## ⚙️ How It Works (Flow)

1. Student submits preferences
2. Data is validated and stored
3. Allocation algorithm processes entries
4. AJAX updates seat availability
5. If course is full → alternatives shown
6. Admin can export results as CSV

---

## 🔄 Before vs After

### ❌ Before

* Manual allocation
* No transparency
* Errors and bias

### ✅ After

* Automated system
* Fair allocation
* Real-time updates
* Auditable reports

---

## 🧪 Verification Checklist

* ✔ Application runs successfully
* ✔ Form submission works
* ✔ Validation errors handled
* ✔ AJAX seat counter updates live
* ✔ Allocation logic works correctly
* ✔ Full courses trigger suggestions
* ✔ CSV export works
* ✔ Responsive on mobile

---

## 🛠️ Setup Instructions

```bash
# Clone the repository
git clone https://github.com/rkshetty-20/Django.git

# Navigate into project
cd Django

# Create virtual environment
python -m venv venv

# Activate environment
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

---

## 🚀 Future Enhancements

* Waitlist auto-promotion
* Admin override panel
* Graphical analytics dashboard
* Multi-round allocation

---

## 👨‍💻 Author

Developed as part of FA-2 Django MVP Project.

---

## ⭐ Final Note

This project focuses on **clarity, fairness, and real-world usability**, ensuring a strong balance between **technical implementation and academic requirements**.
