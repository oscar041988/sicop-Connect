-- 0035 · Perfil de Hermatix: tipos nuevos «capacidad» y «evaluacion» (pedido de Ivania, 2026-11-04).
--
-- La parte A de docs/PERFIL_LISTA_INICIAL.md (aprobada por Oscar el 2026-11-04) trae datos que no son experiencia,
-- permisos ni pólizas: soporte técnico, taller, garantía y marcas («capacidad») y lo que da puntos en la evaluación
-- de las ofertas: PYME, ISO 14001, inclusión de mayores de 45 («evaluacion»).
--
-- SQLite no cambia un CHECK sin reconstruir la tabla: se copian todos los elementos con su id. company_profile_versions
-- y eligibility_items apuntan a company_profile_items: por eso esta migración corre con las llaves foráneas apagadas
-- (línea de abajo, app/database.py) y antes de confirmarse se revisan con PRAGMA foreign_key_check: los ids son los
-- mismos, así que ninguna queda rota. DROP TABLE no dispara el trigger de borrado; el trigger se vuelve a crear igual.
--
-- migracion: sin llaves foraneas

CREATE TABLE company_profile_items_nueva (
    id                 INTEGER PRIMARY KEY,
    tipo               TEXT NOT NULL CHECK (tipo IN ('experiencia', 'certificacion', 'permiso', 'personal', 'poliza',
                                                    'financiero', 'legal', 'capacidad', 'evaluacion')),
    titulo             TEXT NOT NULL CHECK (length(trim(titulo)) > 0),
    creado_por         INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    creado_por_nombre  TEXT NOT NULL CHECK (length(trim(creado_por_nombre)) > 0),
    created_at         TEXT NOT NULL,
    UNIQUE (tipo, titulo)
);

INSERT INTO company_profile_items_nueva (id, tipo, titulo, creado_por, creado_por_nombre, created_at)
SELECT id, tipo, titulo, creado_por, creado_por_nombre, created_at FROM company_profile_items;

DROP TABLE company_profile_items;
ALTER TABLE company_profile_items_nueva RENAME TO company_profile_items;

CREATE TRIGGER perfil_elementos_no_se_borran
BEFORE DELETE ON company_profile_items
BEGIN
    SELECT RAISE(ABORT, 'Los elementos del perfil no se borran: márcalos como pendientes');
END;
