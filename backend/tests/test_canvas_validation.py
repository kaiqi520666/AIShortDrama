import pytest

from app.services.canvas_validation import CanvasValidationError, validate_canvas_payload


def test_canvas_validation_accepts_valid_references():
    validate_canvas_payload(
        {
            "schema_version": 6,
            "nodes": [{"id": "text-1"}, {"id": "image-2"}],
            "edges": [{"source": "text-1", "target": "image-2"}],
            "groups": [{"nodeIds": ["text-1", "image-2"]}],
        }
    )


@pytest.mark.parametrize(
    "canvas, message",
    [
        ({"nodes": [{"id": "a"}, {"id": "a"}]}, "节点 ID 重复"),
        ({"nodes": [{"id": "a"}], "edges": [{"source": "a", "target": "missing"}]}, "不存在"),
        ({"nodes": [{"id": "a"}], "edges": [{"source": "a", "target": "a"}]}, "自连接"),
        ({"nodes": [{"id": "a"}], "groups": [{"nodeIds": ["missing"]}]}, "无效节点"),
    ],
)
def test_canvas_validation_rejects_invalid_references(canvas, message):
    with pytest.raises(CanvasValidationError, match=message):
        validate_canvas_payload(canvas)
