# 🤝 FairAid — Fair Resource Distribution System

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1.3-black?style=flat-square&logo=flask)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?style=flat-square&logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

> A humanitarian resource distribution platform that ensures aid reaches the most vulnerable people first. Built with Flask, SQLAlchemy, and a custom vulnerability scoring algorithm.

---

## 📌 What It Does

FairAid helps humanitarian field offices manage and prioritise aid distribution by:

- ✅ **Vulnerability Scoring** — automatically ranks beneficiaries by need
- ✅ **Smart Prioritisation** — elderly, disabled, displaced, and low-income flagged first
- ✅ **Secure Login** — role-based access for Admin and Staff
- ✅ **Search & Filter** — instantly find any beneficiary by name
- ✅ **Data Migration** — import beneficiaries from CSV files
- ✅ **Field-Ready** — optimised for low-bandwidth environments

---

## 🧮 Vulnerability Scoring Algorithm

| Criteria | Points |
|---|---|
| Age 65+ | +20 |
| Disability | +25 |
| Extreme poverty (income < $20) | +30 |
| Low income (income < $50) | +15 |
| Large household (5+ members) | +10 |
| Displaced status | +20 |
| **Maximum Score** | **105** |

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask 3.1 |
| Database | SQLAlchemy, SQLite |
| Authentication | Flask-Login, Werkzeug |
| Frontend | Bootstrap 5, HTML5 |
| Data | Pandas, NumPy |
| Deployment | Gunicorn, Render.com |

---

## 📁 Project Structure