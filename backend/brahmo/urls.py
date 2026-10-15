from django.urls import path
from rest_framework.routers import DefaultRouter

from . import api_safety, views

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="product")
router.register("nlem", views.NLEMViewSet, basename="nlem")
router.register("jan-aushadhi", views.JanAushadhiViewSet, basename="jan-aushadhi")
router.register("regulatory-events", views.RegulatoryEventViewSet, basename="regulatory-event")
router.register("stock", views.PharmacyStockViewSet, basename="stock")
router.register("protocols", views.ProtocolDocumentViewSet, basename="protocol")
router.register("protocol-units", views.ProtocolUnitViewSet, basename="protocol-unit")
router.register("gaps", views.GapEntryViewSet, basename="gap")
router.register("load-batches", views.LoadBatchViewSet, basename="load-batch")

urlpatterns = router.urls + [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("interactions/", views.InteractionListView.as_view(), name="interactions"),
    path("interactions/check/", views.InteractionCheckView.as_view(), name="interaction-check"),
    path("stock-summary/", views.StockSummaryView.as_view(), name="stock-summary"),
    path("rail/check/", api_safety.RailCheckView.as_view(), name="rail-check"),
    path("qa/", api_safety.GroundedQAView.as_view(), name="qa"),
    path("trace/", api_safety.TraceView.as_view(), name="trace"),
]
