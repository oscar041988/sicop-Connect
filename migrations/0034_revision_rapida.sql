-- 0034 · Asistente: primero solo los excluyentes, el resto si el cartel interesa (decisión de Oscar, 2026-11-04).
--
-- El asistente empieza en «revisión rápida» (solo pregunta los requisitos excluyentes). Cuando alguien pulsa
-- «Seguir con los demás requisitos», la sesión queda «ampliada»: se guarda cuándo y quién, y no se vuelve atrás
-- (lo respondido se conserva siempre). Las sesiones siguen sin poder borrarse (trigger de la 0031).

ALTER TABLE eligibility_sessions ADD COLUMN ampliada_en TEXT;
ALTER TABLE eligibility_sessions ADD COLUMN ampliada_por_nombre TEXT;
