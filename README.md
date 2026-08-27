# AZUL — Plataforma real v1

## Qué incluye
- Aplicación web Flask.
- Registro e inicio de sesión.
- Base de datos SQLite.
- Productos privados por usuario.
- Análisis de rentabilidad.
- Motor inicial de recomendación de mercados.
- Interfaz responsive.

## Ejecutar
```bash
chmod +x run.sh
./run.sh
```
Abrir http://localhost:5000

## Para producción
Antes de publicar: usar PostgreSQL, HTTPS, gestión segura de secretos, recuperación de contraseña, protección CSRF, rate limiting, logs, backups, proveedores de identidad y fuentes verificables de comercio exterior. El motor de mercados debe conectarse a datos actuales y verificables; no debe presentarse el resultado demostrativo como información oficial.
