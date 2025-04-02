# 💬 Messager - Real-Time Chat Application

Messager is a **Django-based real-time messaging application** powered by **Django Channels** and **Redis** for WebSockets. It enables **instant communication** between users with **text and media sharing support**.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/Django-4.2-green?style=for-the-badge&logo=django">
  <img src="https://img.shields.io/badge/WebSockets-Enabled-red?style=for-the-badge">
  <img src="https://img.shields.io/badge/Redis-Supported-yellow?style=for-the-badge&logo=redis">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker">
</p>

---

## ✨ Features

✔ **Real-time chat** using WebSockets  
✔ **JWT-based authentication** (Simple JWT)  
✔ **Direct messaging** with chat rooms  
✔ **File sharing** (images, videos, documents)  
✔ **Last seen tracking** for users  
✔ **Scalable architecture** with Django Channels & Redis  
✔ **Docker support** for easy deployment  
✔ **Websocket

---

## 🚀 Installation & Setup

### 🔹 Prerequisites
- Docker and Docker Compose
- Python 3.10+
- PostgreSQL
- Redis

### 🔹 Clone the Repository  
```bash
git clone https://github.com/Abdullaazimovs/messager.git
cd messager
```
## 🐳 Docker Setup
1. Start Containers
```bash
docker compose up 
```
2. Apply Database Migrations 
```bash
docker compose exec web python manage.py migrate
```
3. Create Superuser
```bash
docker compose exec web python manage.py createsuperuser
```
## Access Services

API: http://localhost:8000

WebSocket Endpoint: ws://localhost:8001

Admin Interface: http://localhost:8000/admin

PostgreSQL Adminer: http://localhost:8080

# 🛠️ Development Setup (Without Docker)

### Install Requirements
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
```
### Run Migrations
```bash
python manage.py migrate
```

### Start Servers

In separate terminals:
```bash
# Start Uvicorn with ASGI workers
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload

# Daphne ASGI server
daphne config.asgi:application --port 8001
```


## 🌐 API Documentation

Swagger UI: http://localhost:8000/swagger/

ReDoc: http://localhost:8000/redoc/

## 🙏 Acknowledgements

- Django Channels Team

- Redis Maintainers

- Django REST Framework

- JWT Auth Contributors

- Daphne ASGI Server Team
