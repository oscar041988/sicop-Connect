-- 0016 · Baja definitiva de usuarios («Eliminar» en la página Usuarios; decisión de Ivania, 2026-10-26).
--
-- Un usuario no se borra de la tabla: sus revisiones, seguimientos e historial lo siguen nombrando
-- (REFERENCES users ON DELETE RESTRICT). «Eliminar» es una baja que no se deshace:
-- * eliminado_en: cuándo se dio de baja (NULL = usuario vigente).
-- * La baja desactiva al usuario, cambia su contraseña por una que no es de nadie y libera su correo
--   (eliminado-<id>@baja.invalid), para que se pueda crear otra cuenta con él. El nombre se conserva.
-- * Triggers: un usuario dado de baja ya no se modifica (no se puede reactivar) y ningún usuario se borra.

ALTER TABLE users ADD COLUMN eliminado_en TEXT;

CREATE TRIGGER usuario_eliminado_no_se_modifica
BEFORE UPDATE ON users
WHEN OLD.eliminado_en IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Un usuario eliminado no se modifica ni se reactiva');
END;

CREATE TRIGGER usuarios_no_se_borran
BEFORE DELETE ON users
BEGIN
    SELECT RAISE(ABORT, 'Los usuarios no se borran: se dan de baja');
END;
