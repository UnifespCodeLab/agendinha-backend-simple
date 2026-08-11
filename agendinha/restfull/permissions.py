from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permissão que permite acesso apenas para usuários com role ADMIN
    Equivalente a: @PreAuthorize("hasRole('ADMIN')")
    """
    message = "Apenas administradores têm permissão para esta ação."

    def has_permission(self, request, view):
        # Verifica se o usuário está autenticado
        if not request.user or not hasattr(request.user, 'role'):
            return False
        
        # Verifica se o role é ADMIN
        return request.user.role == 'ROLE_ADMIN'


class IsUser(permissions.BasePermission):
    """
    Permissão que permite acesso apenas para usuários com role USER
    Equivalente a: @PreAuthorize("hasRole('USER')")
    """
    message = "Apenas usuários comuns têm permissão para esta ação."

    def has_permission(self, request, view):
        # Verifica se o usuário está autenticado
        if not request.user or not hasattr(request.user, 'role'):
            return False
        
        # Verifica se o role é USER
        return request.user.role == 'ROLE_USER'


class IsAdminOrUser(permissions.BasePermission):
    """
    Permissão que permite acesso para usuários com role ADMIN ou USER
    Equivalente a: @PreAuthorize("hasAnyRole('ADMIN', 'USER')")
    """
    message = "Você precisa estar autenticado para acessar este recurso."

    def has_permission(self, request, view):
        # Verifica se o usuário está autenticado
        if not request.user or not hasattr(request.user, 'role'):
            return False
        
        # Verifica se o role é ADMIN ou USER
        return request.user.role in ['ROLE_ADMIN', 'ROLE_USER']


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permissão que permite acesso ao proprietário do recurso ou admin
    Útil para operações de atualização/deleção que requerem ownership
    """
    message = "Você não tem permissão para acessar este recurso."

    def has_object_permission(self, request, view, obj):
        # Admin tem acesso total
        if hasattr(request.user, 'role') and request.user.role == 'ROLE_ADMIN':
            return True
        
        # Verifica se o usuário é o dono do objeto
        # Ajuste conforme necessário para cada model
        if hasattr(obj, 'id_usuario'):
            return obj.id_usuario == request.user.id_usuario
        
        return False