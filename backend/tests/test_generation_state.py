import uuid

import pytest

from app.core.generation_state import InvalidTaskTransition, transition_task
from app.models import GenerationTask


def make_task(status="queued"):
    return GenerationTask(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        node_id="state-test",
        task_type="image",
        provider="toapis",
        model="gpt-image-2",
        status=status,
    )


def test_transition_task_updates_status_and_progress():
    task = make_task()

    assert transition_task(task, "running", progress=5) is True
    assert (task.status, task.progress) == ("running", 5)

    assert transition_task(task, "running", progress=5) is False


def test_transition_task_rejects_invalid_status_and_transition():
    task = make_task("succeeded")

    with pytest.raises(InvalidTaskTransition):
        transition_task(task, "running")
    with pytest.raises(InvalidTaskTransition):
        transition_task(task, "unknown")


def test_transition_task_validates_progress():
    task = make_task()

    with pytest.raises(InvalidTaskTransition):
        transition_task(task, "running", progress=101)


def test_needs_review_only_allows_explicit_manual_resolution():
    task = make_task("needs_review")
    for status in ("queued", "succeeded", "failed", "cancelled"):
        with pytest.raises(InvalidTaskTransition):
            transition_task(task, status)
    assert transition_task(task, "queued", manual=True) is True
