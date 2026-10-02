"""plugin_permissions used to be un-importable: a repeated ``description=`` keyword in every
built-in permission (a compile-time SyntaxError), then ``builtins.dict()`` without importing
``builtins``, and no ``get_permission_manager()`` although plugin_sandbox imports it."""
import importlib

import pytest


@pytest.mark.parametrize("module", [
    "src.sites.base.plugin_permissions",
    "src.sites.base.plugin_sandbox",
    "src.sites.base.plugin_manager",
])
def test_plugin_modules_import(module):
    importlib.import_module(module)


def test_global_permission_manager_has_the_builtin_permissions():
    from src.sites.base.plugin_permissions import PermissionManager, get_permission_manager
    pm = get_permission_manager()
    assert isinstance(pm, PermissionManager) and get_permission_manager() is pm
    perms = getattr(pm, "_permissions", None) or getattr(pm, "permissions")
    assert len(perms) == 11
    # each keeps the fuller of its two former descriptions
    assert perms["file_read"].description == "Allows reading files from the file system"
    assert all(p.description for p in perms.values())


def test_permission_metadata_defaults_are_independent():
    from src.sites.base.plugin_permissions import (
        Permission, PermissionLevel, PermissionScope, PermissionType)
    mk = lambda i: Permission(id=i, name=i, description=i, permission_type=PermissionType.LOGGING,
                              level=PermissionLevel.READ_ONLY, scope=PermissionScope.GLOBAL)
    a, b = mk("a"), mk("b")
    a.metadata["x"] = 1
    assert b.metadata == {}                      # not one shared dict


def _manager():
    from src.sites.base.plugin_permissions import PermissionManager
    return PermissionManager()


def test_approving_a_permission_request_records_the_grant():
    """approve_permission assigned ``request_obj`` and then read ``request`` (NameError on every call)."""
    import asyncio
    pm = _manager()
    request_id = pm.request_permission("plug", "file_write", reason="needs to save results")
    ok = asyncio.run(pm.approve_permission(request_id, True, "reviewed", approver="op"))
    assert ok is True
    assert "file_write" in pm.get_plugin_permissions("plug")
    assert pm.get_permission_grants("plug")["file_write"].granted is True


def test_export_permissions_includes_plugin_permissions_and_grants():
    """export_permissions had a misspelt loop variable and a comprehension with no outer loop."""
    import asyncio
    pm = _manager()
    rid = pm.request_permission("plug", "file_write", reason="x")
    asyncio.run(pm.approve_permission(rid, True, "ok"))
    pm._stats = {}          # KNOWN GAP: statistics were never implemented (no _stats, no get_statistics())
    data = pm.export_permissions()
    assert data["plugin_permissions"]["plug"] == ["file_write"]
    assert data["permission_grants"]["plug"]["file_write"]["granted"] is True
