from collections import Counter

from fastapi.routing import APIRoute

from app.api.routes import (
    admin,
    admin_audits,
    admin_billing,
    admin_models,
    admin_reference_assets,
    admin_tasks,
    admin_templates,
    admin_users,
)
from app.core.identity import get_current_admin


def test_admin_routes_have_single_owner_and_keep_admin_permission():
    routers = [
        admin,
        admin_audits,
        admin_billing,
        admin_models,
        admin_reference_assets,
        admin_tasks,
        admin_templates,
        admin_users,
    ]
    routes = [
        route for module in routers for route in module.router.routes if isinstance(route, APIRoute)
    ]
    keys = Counter((method, route.path) for route in routes for method in route.methods)
    assert [key for key, count in keys.items() if count != 1] == []
    for route in routes:
        assert get_current_admin in [dependency.call for dependency in route.dependant.dependencies]
    assert {route.path for route in admin_models.router.routes} == {
        "/models", "/models/{media_type}/{model_id}"
    }
    assert {route.path for route in admin_tasks.router.routes} == {
        "/tasks", "/tasks/{task_id}", "/tasks/{task_id}/provider-status",
        "/tasks/{task_id}/resolve-review",
    }
    assert all(not route.path.startswith("/models") for route in admin_billing.router.routes)
    assert all(not route.path.startswith("/tasks") for route in admin_templates.router.routes)
