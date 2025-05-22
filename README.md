Proyecto FastAPI con Docker - Arquitectura de Microservicios

Este proyecto es una API REST construida con FastAPI y Docker, utilizando una arquitectura de microservicios.

## Requisitos

- Docker
- Docker Compose

## Estructura del Proyecto

```
.
├── microservices/
│   └── Agent/
│       ├── main.py
│       ├── requirements.txt
│       └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Microservicios

### Agent
- Puerto: 8000
- Descripción: Microservicio principal de Agent
- Endpoints:
  - `GET /`: Mensaje de bienvenida
  - `GET /health`: Verificación del estado del servicio

## Cómo ejecutar el proyecto

1. Construir y levantar los contenedores:
```bash
docker-compose up --build
```

2. Para ejecutar en modo detached (background):
```bash
docker-compose up -d
```

3. Para detener los contenedores:
```bash
docker-compose down
```

## Documentación de la API

Una vez que la aplicación esté corriendo, puedes acceder a la documentación automática en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
