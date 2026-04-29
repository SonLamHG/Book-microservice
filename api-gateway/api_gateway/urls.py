from django.urls import path, include

urlpatterns = [
    # /metrics — exposed for Prometheus scrape (django-prometheus default).
    path('', include('django_prometheus.urls')),
    path('', include('gateway.urls')),
]
