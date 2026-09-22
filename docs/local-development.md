# Local Development Guide

## Prerequisites
- Python 3.11.4
- Node.js 24
- Docker & Docker Compose
- Git

## Step-by-step Setup
1. Clone the repo
2. Create virtualenv and install dependencies
3. Copy `.env.example` to `.env`

## Starting Infrastructure
```bash
docker-compose -f infrastructure/docker-compose.yml up -d
```

## Starting Backend
```bash
cd backend
uvicorn app.main:app --reload
```

## Starting Frontend
```bash
cd frontend
npm run dev
```

## Testing
Backend: `pytest`
Frontend: `npm run test`

## Access URLs
| Service | URL |
|---|---|
| Backend | http://localhost:8000 |
| Frontend | http://localhost:3000 |
| Keycloak | http://localhost:8180 |
| HAPI FHIR | http://localhost:8090 |
| Swagger UI | http://localhost:8000/docs |
