# Turnero bancario

Aplicación de turnos con backend FastAPI y frontend Angular. En local, la API guarda los turnos en SQLite; en Vercel puede usar PostgreSQL mediante `DATABASE_URL`. En ambos casos atiende en orden FIFO y asigna cada turno a una de las cuatro mesas libres.

## Requisitos

- Python 3.11 o posterior
- Node.js 20.19 o posterior y npm

## Iniciar

1. Backend, desde `backend/`:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. Frontend, desde `frontend/`:

   ```powershell
   npm install
   npm start
   ```

3. Abrir `http://localhost:4200`. La documentación interactiva de la API está en `http://localhost:8000/docs`.

En la pantalla del banco, el cliente pulsa **Tomar turno**. En el monitor se ve el turno en atención, la mesa asignada, las mesas disponibles y la fila. El personal libera una mesa con **Finalizar atención**; el primer turno en espera pasa automáticamente a esa mesa. Los cambios se reflejan en el navegador en un intervalo corto.

La base de datos `turnos.db` se crea automáticamente en `backend/` al iniciar el servidor. `psycopg` solo se importa cuando se configura `DATABASE_URL`; si no existe esa variable, el backend usa SQLite.

## Preparar Vercel (plan Hobby)

El repositorio contiene dos aplicaciones; se despliegan como dos proyectos Vercel enlazados al mismo repositorio:

1. **API**: importa el repositorio y configura **Root Directory** como `backend`. Usa Python 3.14. Añade la variable `DATABASE_URL` con una conexión PostgreSQL de Neon.
2. **Web**: importa el mismo repositorio en un segundo proyecto y configura **Root Directory** como `frontend`. En Environment Variables añade `API_BASE_URL` con la URL del proyecto de la API, sin `/` al final.
3. Despliega primero la API para obtener su URL. Después configura `API_BASE_URL` en la web y despliega la web. Por último, agrega el dominio final de la web a `CORS_ORIGINS` en el proyecto de la API y vuelve a desplegar la API.

La configuración `backend/.python-version` selecciona Python 3.14 en Vercel. La base de datos SQLite local no se publica ni se usa como almacenamiento de producción; Vercel requiere una base persistente externa. La opción local del backend sigue usando `backend/turnos.db`.
