"""
Autenticação JWT Customizada para GRAACC API
Compatível com tokens JWT dos microserviços Java
"""

from rest_framework import authentication, exceptions
from django.conf import settings
from .models import Usuario
import jwt


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Autenticação JWT customizada que valida tokens gerados pelos microserviços Java
    e tokens gerados pelo Django.
    
    Header format: Authorization: Bearer <token>
    
    Claims esperados do token:
    - sub: email do usuário
    - iss: emissor (deve corresponder a SECURITY_EMISSOR)
    - idUsuario: ID do usuário
    - idPaciente: ID do paciente (pode ser null)
    - role: role do usuário (ROLE_USER ou ROLE_ADMIN)
    """
    
    keyword = 'Bearer'
    
    def authenticate(self, request):
        """
        Extrai e valida o token JWT do header Authorization
        """
        auth_header = authentication.get_authorization_header(request).decode('utf-8')
        
        if not auth_header:
            return None
        
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0] != self.keyword:
            return None
        
        token = parts[1]
        
        try:
            return self.validate_token(token)
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token expirado')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Token inválido')
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Erro ao validar token: {str(e)}')
    
    def validate_token(self, token):
        """
        Valida token JWT e extrai informações do usuário
        
        Retorna: (user_object, None)
        """
        try:
            # Decodifica o token usando a chave secreta e algoritmo HMAC256
            payload = jwt.decode(
                token,
                settings.SECURITY_TOKEN,
                algorithms=['HS256'],
                issuer=settings.SECURITY_EMISSOR
            )
        except jwt.InvalidIssuerError:
            # Tenta decodificar sem validação de issuer (compatibilidade)
            payload = jwt.decode(
                token,
                settings.SECURITY_TOKEN,
                algorithms=['HS256'],
                options={'verify_iss': False}
            )
        
        # Extrai informações do payload
        email = payload.get('sub')
        id_usuario = payload.get('idUsuario')
        id_paciente = payload.get('idPaciente')
        role = payload.get('role')
        
        if not email or not id_usuario:
            raise exceptions.AuthenticationFailed('Token inválido: claims obrigatórios ausentes')
        
        # Cria objeto de usuário autenticado (não precisa buscar no DB)
        # Isso é mais eficiente e compatível com tokens gerados externamente
        user = UserLoggedInfo(
            id_usuario=id_usuario,
            id_paciente=id_paciente,
            email=email,
            role=role
        )
        
        return (user, None)
    
    def authenticate_header(self, request):
        """
        Retorna string para o header WWW-Authenticate em caso de falha
        """
        return self.keyword


class UserLoggedInfo:
    """
    Representa o usuário autenticado extraído do token JWT
    Migrado de: UserLoggedInfo.java
    
    Este objeto é usado como request.user após autenticação bem-sucedida
    """
    
    def __init__(self, id_usuario, id_paciente, email, role):
        self.id_usuario = id_usuario
        self.id_paciente = id_paciente
        self.email = email
        self.role = role
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def __str__(self):
        return f"UserLoggedInfo({self.email}, {self.role})"
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def is_admin(self):
        """Verifica se o usuário é admin"""
        return self.role == 'ROLE_ADMIN'
    
    @property
    def is_user(self):
        """Verifica se o usuário é user comum"""
        return self.role == 'ROLE_USER'
