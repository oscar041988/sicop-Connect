-- 0005 · Historial de cambios de administración (niveles de acceso aprobados por Oscar, 2026-10-12).
--
-- * audit_log: quién cambió qué y cuándo. Hoy: usuarios (crear, nivel, activar/desactivar, contraseña nueva).
--   En la lección 7 también los destinatarios de los avisos.
--   - user_id: el administrador que lo hizo desde el panel; NULL si fue desde la terminal (actor = 'terminal').
--   - actor: su nombre en ese momento, para que el historial no cambie si después se renombra.
--   - detalle: texto legible. Nunca contraseñas ni hashes.
-- * Igual que las revisiones, el historial no se borra ni se modifica.
-- * users.role ya admite 'admin' y 'encargado' (0001): no cambia.

CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    actor       TEXT NOT NULL CHECK (length(trim(actor)) > 0),
    -- Sin lista fija en un CHECK: la lección 7 agrega acciones y SQLite no deja cambiar un CHECK sin
    -- reconstruir la tabla. Las acciones válidas están en app/historial.py (ACCIONES).
    accion      TEXT NOT NULL,
    detalle     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TRIGGER audit_log_no_se_borra
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'El historial no se borra');
END;

CREATE TRIGGER audit_log_no_se_modifica
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'El historial no se modifica');
END;
