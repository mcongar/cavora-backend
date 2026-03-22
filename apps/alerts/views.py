from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from .models import Alert
from .serializers import AlertSerializer


class AlertListView(generics.ListAPIView):
    serializer_class = AlertSerializer

    def get_queryset(self):
        return Alert.objects.filter(
            user=self.request.user,
            dismissed=False,
        ).select_related(
            "user_product__catalog_product"
        ).order_by("trigger_date")


class DismissAlertView(APIView):
    def patch(self, request, pk):
        alert = generics.get_object_or_404(
            Alert,
            id=pk,
            user=request.user
        )
        alert.dismissed = True
        alert.dismissed_at = timezone.now()
        alert.save(update_fields=["dismissed", "dismissed_at"])
        return Response({"status": "dismissed"})
