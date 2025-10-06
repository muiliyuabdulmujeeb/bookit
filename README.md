# BookIt API

A production-ready REST API for a bookings platform that enables users to browse services, make bookings, and leave reviews. Built with FastAPI and PostgreSQL.

## 📋 Table of Contents

- [Features](#features)
- [Architecture Decisions](#architecture-decisions)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [API Endpoints](#api-endpoints)

## ✨ Features

- **User Authentication & Authorization**: JWT-based authentication with role-based access control (User/Admin)
- **Service Management**: Browse, search, and manage services with pricing and availability
- **Booking System**: Create, manage, and track bookings with conflict validation
- **Review System**: Users can leave reviews for completed bookings
- **Advanced Filtering**: Search and filter services and bookings with multiple parameters
- **Production Ready**: Structured logging, environment-based configuration, and proper error handling

## 🏗 Architecture Decisions

### Database Choice: PostgreSQL

I chose **PostgreSQL** over MongoDB for the following reasons:

1. **ACID Compliance**: Critical for booking systems to ensure data consistency, especially for preventing double bookings and maintaining transaction integrity
2. **Strong Relational Model**: The entities (Users, Services, Bookings, Reviews) have clear relationships that benefit from foreign key constraints and referential integrity
3. **Complex Queries**: PostgreSQL excels at complex queries with JOINs, which are essential for filtering bookings by user, service, date ranges, and status
4. **Data Validation**: Built-in constraints (UNIQUE, CHECK, NOT NULL) provide an additional layer of data validation beyond application logic
5. **Mature Ecosystem**: Excellent ORM support (SQLAlchemy), migration tools (Alembic), and production deployment options

### Application Architecture

The application follows a **3-layer architecture pattern**:

```
┌─────────────────────────────────────┐
│         API Layer (Routers)         │  ← HTTP handling, request/response
├─────────────────────────────────────┤
│      Service Layer (Business)       │  ← Business logic, validation
├─────────────────────────────────────┤
│    Repository Layer (Database)      │  ← Data access, queries
└─────────────────────────────────────┘
```

This separation ensures:
- **Testability**: Each layer can be tested independently
- **Maintainability**: Clear separation of concerns
- **Scalability**: Easy to modify or extend individual components

## 🛠 Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 17+
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose)
- **Password Hashing**: argon
- **Validation**: Pydantic v2


## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 17+
- pip for dependency management

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/muiliyuabdulmujeeb/bookit.git
cd bookit
```

2. **Create and activate a virtual environment**
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
touch .env
# Edit .env with your configuration
```

5. **Set up the database**

# Run migrations
alembic upgrade head
```

6. **Run the development server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
API documentation will be at `http://localhost:8000/docs`

## 🔧 Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `SECRET_KEY` | JWT secret key for token signing | - | Yes |
| `ALGORITHM` | JWT encoding algorithm | `HS256` | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiration time | `5` | Yes |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Refresh token expiration time | `10080` | Yes |

### Example .env file
```env
DATABASE_URL=postgresql://user:password@localhost/bookit_db
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080
```

## 📖 API Documentation

Once the application is running, you can access:

- **Swagger UI**: `http://localhost:8000/docs`


## 🚢 Deployment

### Deployment on Render

The application is deployed on [Render](https://render.com) with the following configuration:

**Production URL**: `https://bookit.onrender.com`

#### Deployment Steps

1. **Connect GitHub repository to Render**
2. **Configure environment variables in Render dashboard**
3. **Set up PostgreSQL database on Render**
4. **Deploy with automatic deploys on main branch**

#### Health Check Endpoint
```
GET /health
```

## 📝 API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/auth/register` | Register new user | Public |
| POST | `/auth/login` | User login | Public |
| POST | `/auth/refresh` | Refresh access token | Authenticated |
| POST | `/auth/logout` | Logout user | Authenticated |

### User Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/me` | Get current user profile | Authenticated |
| PATCH | `/me` | Update current user profile | Authenticated |

### Service Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/services` | List all services (with filters) | Public |
| GET | `/services/{id}` | Get service details | Public |
| POST | `/services` | Create new service | Admin |
| PATCH | `/services/{id}` | Update service | Admin |
| DELETE | `/services/{id}` | Delete service | Admin |

**Query Parameters for GET /services:**
- `q`: Search query for title/description
- `price_min`: Minimum price filter
- `price_max`: Maximum price filter
- `active`: Filter by active status (true/false)

### Booking Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/bookings` | Create new booking | User |
| GET | `/bookings` | List bookings | User (own) / Admin (all) |
| GET | `/bookings/{id}` | Get booking details | Owner / Admin |
| PATCH | `/bookings/{id}` | Update booking | Owner / Admin |
| DELETE | `/bookings/{id}` | Cancel booking | Owner (before start) / Admin |

**Query Parameters for GET /bookings:**
- `status`: Filter by status (pending/confirmed/cancelled/completed)
- `from`: Start date filter (ISO 8601)
- `to`: End date filter (ISO 8601)

### Review Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/reviews` | Create review for completed booking | User |
| GET | `/services/{id}/reviews` | Get reviews for a service | Public |
| PATCH | `/reviews/{id}` | Update review | Owner |
| DELETE | `/reviews/{id}` | Delete review | Owner / Admin |

## 📊 Status Codes

The API uses standard HTTP status codes:

- `200 OK`: Successful GET, PATCH, DELETE
- `201 Created`: Successful POST
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., booking overlap)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## 🔒 Security Considerations

- **Password Security**: All passwords are hashed using argon with salt rounds
- **JWT Security**: Tokens are signed with HS256 algorithm and include expiration
- **SQL Injection Prevention**: Using SQLAlchemy ORM with parameterized queries
- **Input Validation**: Pydantic schemas validate all input data
- **Environment Variables**: All sensitive data stored in environment variables

## 📈 Monitoring & Logging
- **Request Logging**: All HTTP requests are logged with response times
- **Health Checks**: `/health` endpoint for monitoring service status


## 👥 Author

- **Muiliyu Abdulmujeeb** - *ALT/SOE/024/5573* - [GitHub](https://github.com/muiliyuabdulmujeeb)
