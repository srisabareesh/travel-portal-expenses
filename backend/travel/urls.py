from rest_framework.routers import DefaultRouter

from .views import CountryViewSet, TravelRequestViewSet


router = DefaultRouter()

router.register(
    "countries",
    CountryViewSet,
    basename="country",
)

router.register(
    "travel-requests",
    TravelRequestViewSet,
    basename="travel-request",
)

urlpatterns = router.urls