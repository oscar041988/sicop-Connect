-- 0040 · Enriquecimiento desde la PC hacia el servidor (fase 2, docs/ENVIO_ENRIQUECIMIENTO.md, 2026-11-09).
--
-- La PC de Ivania abre una corrida en el servidor, consulta SICOP con su navegador y manda cada cartel. La corrida
-- queda en enrich_runs como siempre, con dos datos nuevos:
-- * origen: 'local' (enrich run en la misma máquina que la base, como hasta ahora) o 'remoto' (la PC por la API).
-- * cola_json: los Números SICOP que el servidor le dio a la PC al abrir la corrida. El servidor solo acepta
--   resultados de esos carteles (texto JSON, lista de cadenas; NULL en las corridas locales).

ALTER TABLE enrich_runs ADD COLUMN origen TEXT NOT NULL DEFAULT 'local' CHECK (origen IN ('local', 'remoto'));
ALTER TABLE enrich_runs ADD COLUMN cola_json TEXT;
