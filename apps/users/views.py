from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import User
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UpdatePushTokenView(APIView):
    def patch(self, request):
        user = request.user
        token = request.data.get("push_token")
        if not token:
            return Response(
                {"detail": "push_token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.push_token = token
        user.save(update_fields=["push_token"])
        return Response({"status": "ok"})
