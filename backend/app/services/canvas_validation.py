from typing import Any


CURRENT_CANVAS_SCHEMA_VERSION = 6


class CanvasValidationError(ValueError):
    pass


def validate_canvas_payload(canvas: dict[str, Any]) -> None:
    schema_version = canvas.get("schema_version", 1)
    if not 1 <= schema_version <= CURRENT_CANVAS_SCHEMA_VERSION:
        raise CanvasValidationError(f"画布版本 {schema_version} 不受支持")

    nodes = canvas.get("nodes") or []
    edges = canvas.get("edges") or []
    groups = canvas.get("groups") or []
    node_ids = [node.get("id") for node in nodes if isinstance(node, dict)]
    if len(node_ids) != len(nodes) or any(not node_id for node_id in node_ids):
        raise CanvasValidationError("画布节点缺少有效 ID")
    if len(set(node_ids)) != len(node_ids):
        raise CanvasValidationError("画布节点 ID 重复")
    node_id_set = set(node_ids)

    for edge in edges:
        if not isinstance(edge, dict) or not edge.get("source") or not edge.get("target"):
            raise CanvasValidationError("画布连线格式无效")
        if edge["source"] not in node_id_set or edge["target"] not in node_id_set:
            raise CanvasValidationError("画布连线引用了不存在的节点")
        if edge["source"] == edge["target"]:
            raise CanvasValidationError("画布不允许节点自连接")

    for group in groups:
        if not isinstance(group, dict):
            raise CanvasValidationError("画布分组格式无效")
        group_node_ids = group.get("nodeIds") or []
        if len(set(group_node_ids)) != len(group_node_ids) or any(
            node_id not in node_id_set for node_id in group_node_ids
        ):
            raise CanvasValidationError("画布分组引用了无效节点")

    if len(nodes) > 2000 or len(edges) > 4000 or len(groups) > 1000:
        raise CanvasValidationError("画布内容超出允许大小")
