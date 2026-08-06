# 🎫 DicoEvent API

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?&style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?&style=for-the-badge&logo=docker&logoColor=white)
![Celery](https://img.shields.io/badge/celery-%2337814A.svg?&style=for-the-badge&logo=celery&logoColor=white)

**DicoEvent** is a high-traffic, mission-critical RESTful API backend designed for scalable event management and ticketing. Built with **Django REST Framework (DRF)** and a microservices-ready containerized architecture, it handles concurrent ticket bookings, asynchronous email notifications, and robust data management.

## ✨ Key Features

- **Robust Authentication & Security:** 
  - Stateless JSON Web Token (JWT) authentication using `djangorestframework-simplejwt`.
  - API Rate Limiting (Throttling) to prevent DDoS abuse and brute-force attacks.
- **High Concurrency Quota Management:** 
  - Implementation of **Atomic Database Transactions** (`select_for_update`) to prevent ticket overbooking and race conditions during high-volume flash sales.
- **Performance & Scalability:** 
  - **Redis** integration for efficient endpoint caching.
  - **Celery & Celery Beat** for offloading heavy asynchronous tasks (e.g., event reminders, email dispatches).
- **S3-Compatible Object Storage:** Seamless media handling using **MinIO**.
- **Automated Quality Control:** Integrated with **Pytest** for unit testing and **Ruff** for strict code linting and formatting.
- **Production-Ready Operations:** Includes a lightweight Kubernetes-ready `/health/` readiness probe and is fully containerized using Docker Compose.

---

## 🛠 Tech Stack & Architecture

- **Backend Framework:** Python 3.10, Django 4.2, Django REST Framework
- **Databases:** PostgreSQL 15 (Relational Data), Redis (Caching & Message Broker)
- **Background Workers:** Celery & Celery Beat
- **Object Storage:** MinIO (Local S3 Alternative)
- **Containerization:** Docker & Docker Compose
- **Documentation:** OpenAPI 3.0 / Swagger UI (`drf-spectacular`)
- **CI/CD & Code Quality:** GitHub Actions, Pytest, Ruff

### Entity-Relationship Diagram (ERD)
The database structure relies on a decoupled, modular Django app design (`core`, `events`, `registrations`, `tickets`, `payments`). 
*(See `ERD-DicoEvent-versi-1.png` for the complete schema design).*

---

## 🚀 Getting Started

### Prerequisites
Make sure you have the following installed on your machine:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Installation & Execution

1. **Clone the repository:**
   ```bash
   git clone https://github.com/alifkha7/dico_event.git
   cd dico_event
   ```

2. **Environment Configuration:**
   Copy the example environment variables to create your `.env` file.
   ```bash
   cp .env.example .env
   ```

3. **Build and Spin Up Containers:**
   The `docker-compose.yml` file is configured to spin up the Web API, PostgreSQL, Redis, Celery Worker, Celery Beat, and MinIO in detached mode.
   ```bash
   docker-compose up --build -d
   ```

4. **Verify Deployment:**
   Check the health of the application by navigating to the health check endpoint:
   ```
   GET http://localhost:8000/api/health/
   ```

---

## 📚 API Documentation

DicoEvent uses `drf-spectacular` to auto-generate OpenAPI 3.0 specifications. Once the server is running, you can interact with the API endpoints via:

- **Swagger UI:** [http://localhost:8000/api/docs/swagger/](http://localhost:8000/api/docs/swagger/)
- **ReDoc:** [http://localhost:8000/api/docs/redoc/](http://localhost:8000/api/docs/redoc/)
- **Raw Schema:** [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

---

## 🧪 Testing & Linting

We enforce strict coding standards and maintain high test coverage. You can run these commands inside the `web` container, or locally if using `Pipenv`.

**Run Unit Tests:**
```bash
docker-compose exec web pytest
```

**Run Linter (Ruff):**
```bash
docker-compose exec web ruff check .
```

---

## 🤝 Contribution Guidelines
This repository is primarily developed as a portfolio showcase. However, feedback, bug reports, and pull requests are highly appreciated. 

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
