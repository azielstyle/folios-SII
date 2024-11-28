import time
import jwt
from django.conf import settings
from django.http import JsonResponse
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

class JWTAuthenticationMiddleware:
    """
    Middleware para validar el token JWT en cada solicitud entrante.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Intenta obtener el token de la cabecera de autorización
        auth_header = request.headers.get("Authorization")
        if auth_header:
            try:
                # Elimina el prefijo "Bearer" si está presente
                token = auth_header.split(" ")[1]
                service_key = settings.SERVICE_KEY
                if token == service_key:
                    request.user = "service user"
                else:
                    # Decodifica el token usando la clave secreta
                    payload = jwt.decode(
                        token,
                        settings.SECRET_KEY,
                        algorithms=["HS256"]  # Asegúrate de usar el algoritmo correcto
                    )
                    #payload= {'token_type': 'access', 'exp': 1732743230, 'iat': 1732656830, 'jti': '1c4825ece9934af59337608f40df6124', 'user_id': 'clfk2xm690000mj08qq02nfab'}
                    print(payload)
                    # Añade el usuario o datos relevantes al request
                    if payload.get("token_type") == "access":
                        if payload.get("exp") < time.time():
                            return JsonResponse({"detail": "Token expirado"}, status=401)
                        request.user = payload.get("user_id")
                        request.token_payload = payload

            except (IndexError, InvalidTokenError, ExpiredSignatureError) as e:
                return JsonResponse({"detail": "Token inválido o expirado"}, status=401)

        else:
            # Si no hay token, opcionalmente puedes requerirlo
            request.user = None

        return self.get_response(request)
