# Observability — ELK + Prometheus + Grafana (skeleton)

Implements thesis Ch.4 §4.9 at **skeleton level (Option A)**: containers
are wired and the api-gateway exports metrics; other services appear
DOWN until they install `django-prometheus`.

## Endpoints

| URL | Tool | Default credentials |
|---|---|---|
| <http://localhost:9200> | Elasticsearch HTTP | (security disabled) |
| <http://localhost:5601> | Kibana | (security disabled) |
| <http://localhost:9090> | Prometheus | — |
| <http://localhost:9090/targets> | Prometheus targets (UP / DOWN) | — |
| <http://localhost:3000> | Grafana | `admin` / `admin` |
| <http://localhost:8000/metrics> | api-gateway metrics endpoint (Django) | — |

## What's wired today

- **api-gateway** has `django-prometheus` installed; middleware records request count + latency histograms; `/metrics` is exposed; the `JWTAuthMiddleware` exempts `/metrics` so Prometheus can scrape without auth.
- **Prometheus** scrapes api-gateway every 15s (and itself, and all other services as listed jobs — they show DOWN).
- **Grafana** auto-provisions a Prometheus datasource and an "API Gateway" dashboard with: requests/s by view, p95 latency, status-code split, targets up/down counters.
- **Elasticsearch + Kibana** are running but no log shipper is wired — Kibana opens with empty indices.

## What's NOT wired (honest skeleton state)

- `auth-service`, `customer-service`, …, `ai-service`: no `/metrics` yet.
  They appear DOWN in <http://localhost:9090/targets>.
- No Filebeat / Logstash: Docker logs are NOT shipped to Elasticsearch.
- No alerting rules in Prometheus, no notification channels in Grafana.

## Migration to full monitoring (Option B — for v02 of the thesis if you want)

For each Django service:

1. Add to `requirements.txt`:
   ```
   django-prometheus>=2.3
   ```
2. In `<svc>/settings.py`:
   - Append `'django_prometheus'` to `INSTALLED_APPS`.
   - Wrap `MIDDLEWARE` with `PrometheusBeforeMiddleware` first and `PrometheusAfterMiddleware` last.
3. In `<svc>/urls.py`, add at the top:
   ```python
   path('', include('django_prometheus.urls')),
   ```
4. Rebuild the service: `docker-compose up --build -d <svc-name>`.
5. Confirm at <http://localhost:9090/targets> the service flips from DOWN to UP.

For the FastAPI ai-service, use `prometheus-fastapi-instrumentator`:
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)  # /metrics
```

For ELK log shipping, add a `filebeat` container with autodiscover for
the `bookstore_default` Docker network and ship to `elasticsearch:9200`.

## Resource cost

Approx. additional RAM after warm-up:

| Container | RAM | Notes |
|---|---|---|
| elasticsearch | ~1.0 GB | Capped by `ES_JAVA_OPTS=-Xms512m -Xmx512m` |
| kibana | ~400 MB | |
| prometheus | ~150 MB | |
| grafana | ~150 MB | |
| **Total** | **~1.7 GB extra** | On top of the 14 application services |
