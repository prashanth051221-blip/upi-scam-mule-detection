from django.urls import path

from . import views

urlpatterns = [
    path("", views.start, name="start"),
    path("demo/<slug:slug>/", views.load_demo, name="load_demo"),
    path("settings/", views.update_settings, name="settings"),
    path("overview/", views.overview, name="overview"),
    path("alerts/", views.alerts, name="alerts"),
    path("payment/<str:txn_id>/", views.payment, name="payment"),
    path("rings/", views.rings, name="rings"),
    path("rings/<int:ring>/", views.rings, name="ring"),
    path("evidence/", views.evidence, name="evidence"),
    path("export/<str:kind>.csv", views.export, name="export"),
]
