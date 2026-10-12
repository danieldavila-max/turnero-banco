# Turnero bancario

Aplicación web Angular para gestionar turnos en cuatro mesas. No usa backend ni base de datos: los datos se guardan en el `localStorage` del navegador.

## Requisitos

- Node.js 20.19 o posterior
- npm

## Iniciar localmente

Desde `frontend/`:

```powershell
npm install
npm start
```

Abre `http://localhost:4200`. Los botones **Cliente** y **Administrador** cambian la vista. El cliente genera turnos y ve las mesas ocupadas; el administrador finaliza la atención y el turno más antiguo en espera pasa automáticamente a esa mesa.

## Datos locales

El estado persiste en el navegador y se sincroniza entre pestañas abiertas en el mismo navegador y origen. Cada navegador, perfil o dispositivo tiene sus propios datos; borrar los datos del sitio también borra los turnos. No se requiere Python, una API ni una base de datos.

## Desplegar en Vercel

Importa el repositorio `danieldavila-max/turnero-banco` como un proyecto de Vercel con **Root Directory** `frontend`, framework Angular, comando de compilación `npm run build` y directorio de salida `dist/turnero/browser`. No hacen falta variables de entorno ni servicios adicionales.
