# Service Connect API

A Flask REST API with OpenAPI documentation for Service Connect platform, providing user and provider authentication.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env` file:
```
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=3306
DB_NAME=service_connect
```

3. Run the application:
```bash
python app.py
```

## API Documentation

Visit `/docs/` for interactive OpenAPI documentation.

## Endpoints

### Authentication

- `POST /api/auth/user/register` - Register a new user
- `POST /api/auth/user/login` - User login
- `POST /api/auth/provider/register` - Register a new provider
- `POST /api/auth/provider/login` - Provider login
- `GET /api/auth/me` - Get current user/provider info (requires JWT token)

## Usage

### Register User
```bash
curl -X POST http://localhost:5000/api/auth/user/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "address": "123 Main St",
    "password": "password123"
  }'
```

### Login User
```bash
curl -X POST http://localhost:5000/api/auth/user/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123"
  }'
```

### Register Provider
```bash
curl -X POST http://localhost:5000/api/auth/provider/register \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Acme Services",
    "full_name": "Jane Smith",
    "email": "jane@acme.com",
    "address": "456 Business Ave",
    "password": "password123",
    "about": "We provide excellent services"
  }'
```

### Get Current User Info
```bash
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```