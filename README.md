# News Scraper (NewsAPI) — Emisor = término de búsqueda

Este proyecto trae noticias desde **NewsAPI** usando como **término de búsqueda** el valor de la columna **Emisor** en un Excel del repositorio. Está pensado para operar **100% en GitHub** (repo privado) con ejecución programada vía **GitHub Actions** (gratis).

## 🧱 Estructura

```
/
├─ news_fetch.py
├─ config.yml
├─ requirements.txt
├─ README.md
├─ data/
│  └─ clientes.xlsx          # Aquí el equipo edita emisores (términos)
└─ .github/
   └─ workflows/
      └─ news-cron.yml       # Cron cada X horas
```

## ⚙️ Configuración rápida

1. **Crea un repo privado** en GitHub y sube estos archivos.
2. En **Settings → Secrets and variables → Actions → New repository secret**, agrega:
   - `NEWSAPI_KEY` con tu API key de NewsAPI.
3. (Opcional) Ajusta el **cron** en `.github/workflows/news-cron.yml` (está en UTC). Ejecuta cada 25 de cada mes a las 4:00 p.m.

## ✍️ Cómo **añadir o editar un Emisor** (término de búsqueda)

1. En GitHub, ve a `data/clientes.xlsx`.
2. Descárgalo o **sube una nueva versión** editada (drag & drop en la UI).
3. Asegúrate que tenga las columnas:
   - **Emisor** (obligatoria): es el término de búsqueda que se enviará a NewsAPI.
   - **Idioma** (opcional): `es`, `en`, etc. Si se deja vacío, se usan los `languages` de `config.yml`.
4. En la hoja Excludes, escribir la lista de dominios a excluir (opcional)

### Ejemplo de `clientes.xlsx`

| Emisor                   | Idioma |
|-------------------------|--------|
| Empresa1                  | es     |
| Empresa2      | es     |
| Empresa4              | en     |
| Empresa5   | es     |

> Nota: Puedes usar frases entre comillas o varias palabras como término.

## 🕒 Programación (GitHub Actions)

El workflow `news-cron.yml` corre por cron (por defecto cada 25 de cada mes a las 4:00 p.m.) y también manualmente desde la pestaña **Actions**. Si hay cambios en los archivos de salida, hace commit automático a la rama.

### Cambiar la frecuencia
Edita el cron en el workflow (UTC). Ejemplos:
- Cada 12 horas: `0 */12 * * *`
- Todos los días a las 10:00 UTC: `0 10 * * *`

## ⚠️ Cuotas y límites

- Revisa tu plan de **NewsAPI** para no exceder la cuota diaria.
- Puedes reducir idiomas, emisores o `page_size` en `config.yml` para controlar el volumen.

## 🧩 Personalizaciones útiles (opcionales)

- **Filtrar por dominios** en `config.yml` (lista `domains`).
