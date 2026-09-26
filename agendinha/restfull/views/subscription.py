from ..models import PushSubscription, Usuario
from ..permissions import IsAdminOrUser
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from pywebpush import webpush
import json

@api_view(['POST'])
@permission_classes([IsAdminOrUser])
def save_subscription(request):
    data = json.loads(request.body)

    user = Usuario.objects.get(id_usuario=data["id_usuario"])

    PushSubscription.objects.update_or_create(
        usuario=user,
        endpoint=data["endpoint"],
        defaults={
            "p256dh": data["keys"]["p256dh"],
            "auth": data["keys"]["auth"],
        }
    )

    return Response({"status": "saved"}, status=status.HTTP_200_OK)

def send_push(id_usuario, title, body, url="/"):
    subscriptions = PushSubscription.objects.filter(id_usuario=id_usuario)
    for sub in subscriptions:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh,
                    "auth": sub.auth,
                },
            },
            data=json.dumps({
                "title": title,
                "body": body,
                "url": url,
            }),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": settings.VAPID_ADMIN_EMAIL,
            },
        )