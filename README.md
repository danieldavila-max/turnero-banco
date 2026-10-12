# Turnero bancario

Aplicación de turnos con backend FastAPI y frontend Angular. La API guarda los turnos en SQLite, atiende en orden FIFO y asigna cada turno a una de las cuatro mesas libres.

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

La base de datos `turnos.db` se crea automáticamente en `backend/` al iniciar el servidor.
