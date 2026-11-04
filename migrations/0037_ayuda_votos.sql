-- 0037 · «¿Te sirvió esta ayuda?» al final de cada misión (Página de ayuda, lección 4).
--
-- ayuda_votos: cada respuesta de una persona a una misión (app/ayuda/votos.py). Los administradores ven en /ayuda
-- cuántos «sí» y «no» tiene cada misión, para corregir primero las que más confunden. Nada se borra ni se
-- modifica (triggers): si alguien cambia de idea, vota otra vez.

CREATE TABLE ayuda_votos (
    id              INTEGER PRIMARY KEY,
    mision          TEXT NOT NULL CHECK (length(mision) BETWEEN 1 AND 80),   -- «08-revision»
    util            INTEGER NOT NULL CHECK (util IN (0, 1)),                 -- 1 = sí, 0 = no
    comentario      TEXT NOT NULL DEFAULT '' CHECK (length(comentario) <= 500),
    usuario_id      INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    usuario_nombre  TEXT NOT NULL CHECK (length(trim(usuario_nombre)) > 0),
    creado_en       TEXT NOT NULL
);

CREATE INDEX idx_ayuda_votos ON ayuda_votos (mision, id);

CREATE TRIGGER ayuda_votos_no_se_borran
BEFORE DELETE ON ayuda_votos
BEGIN
    SELECT RAISE(ABORT, 'Los votos de la ayuda no se borran');
END;

CREATE TRIGGER ayuda_votos_no_se_modifican
BEFORE UPDATE ON ayuda_votos
BEGIN
    SELECT RAISE(ABORT, 'Los votos de la ayuda no se modifican: vota otra vez');
END;
