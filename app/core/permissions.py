"""
Permission registry for the application.
This module collects permissions from all endpoint modules.
"""
from typing import Dict, List, Optional
from app.schemas.role import PermissionCreate


class PermissionRegistry:
    """Registry to collect and provide all application permissions"""

    _instance = None
    _module_permissions: Dict[str, Dict[str, Dict[str, str]]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PermissionRegistry, cls).__new__(cls)
        return cls._instance

    def register_permissions(self, module: str, permissions: Dict[str, str],
                             descriptions: Optional[Dict[str, str]] = None):
        """
        Register permissions for a module

        Args:
            module: Module name
            permissions: Dict mapping action names to permission codes
            descriptions: Optional dict mapping permission codes to descriptions
        """
        if module not in self._module_permissions:
            self._module_permissions[module] = {}

        self._module_permissions[module]["permissions"] = permissions

        if descriptions:
            self._module_permissions[module]["descriptions"] = descriptions

    def get_module_permissions(self, module: str) -> Dict[str, str]:
        """Get all permissions for a specific module"""
        if module in self._module_permissions:
            return self._module_permissions[module]["permissions"]
        return {}

    def get_all_modules(self) -> List[str]:
        """Get list of all modules with registered permissions"""
        return list(self._module_permissions.keys())

    def get_all_permissions(self) -> Dict[str, Dict[str, str]]:
        """Get all permissions organized by module"""
        return {
            module: data["permissions"]
            for module, data in self._module_permissions.items()
        }

    def get_permission_definitions(self) -> List[PermissionCreate]:
        """
        Get all permissions as PermissionCreate objects for initialization
        """
        permission_definitions = []

        for module, data in self._module_permissions.items():
            permissions = data["permissions"]
            descriptions = data.get("descriptions", {})

            for action, code in permissions.items():
                # Create a human-readable name from code
                name = " ".join(word.capitalize() for word in code.split("_"))

                # Get description if available, otherwise generate a default one
                description = descriptions.get(code, f"Allows {action} operations on {module}")

                permission_definitions.append(
                    PermissionCreate(
                        code=code,
                        name=name,
                        module=module,
                        description=description
                    )
                )

        return permission_definitions


# Singleton instance
permission_registry = PermissionRegistry()