from rest_framework import permissions
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission


class arkPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            if request.user and request.user.groups.filter(name='ark-admin'):
                return True
            return False
