# mydvls-backend

# 🚀 FastAPI Project

A modern backend API built with **FastAPI** and **PostgreSQL**.

---

## 📌 Features

- FastAPI (high-performance Python framework)
- PostgreSQL database integration
- SQLAlchemy ORM
- Alembic migrations
- Environment-based configuration
- Clean project structure

---

## ⚙️ Requirements

- Python 3.10+
- PostgreSQL
- pip / virtualenv

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <project-folder>
```

### 2. create vertual enviroment

- python -m venv venv
- source venv/bin/activate # Mac/Linux
- venv\Scripts\activate # Windows

### 3. Install requirements

- pip install -r requirements.txt

### 4. Setup environment variable

- cp .env.example .env

### 5. Run the server

- uvicorn main:app --reload

## Project Structure

.
├── app/
| |\_\_ api/
│ ├── models/
│ ├── schemas/
│ ├── routes/
│ └── services/
├── main.py
├── requirements.txt
└── README.md

## Features

- User authentication
- Product management
- Cart system
- Coupon/discount handling

## API Documentation

Once the server is running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
