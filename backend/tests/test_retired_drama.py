import pytest
from pydantic import ValidationError

from app.schemas.reversal import ReversePromptRequest
from scripts.purge_drama_workspaces import exclusive_keys, object_keys


def test_cleanup_only_extracts_owned_object_urls():
    base = "https://media.example.com"
    assert object_keys({
        "result": [{"url": base + "/generations/image.png?x-oss-process=resize"}],
        "reference": "https://other.example.com/image.png",
        "invalid": base + "/../private.png",
    }, base) == {"generations/image.png"}
    assert object_keys([], base) == set()
    assert object_keys("https://other.example.com/image.png", "") == set()


def test_cleanup_preserves_shared_library_canvas_and_metadata_references():
    base = "https://media.example.com"
    keys = {"exclusive.png", "library.png", "canvas.png", "metadata.png", "prompt.png"}
    retained = [
        {"image_url": base + "/library.png"},
        {"canvas": {"nodes": [{"data": {"asset": base + "/canvas.png?resize=100"}}]}},
        {"object_key": "metadata.png"},
        {"prompt": "Reference " + base + "/prompt.png"},
    ]
    assert exclusive_keys(keys, retained, base) == {"exclusive.png"}


@pytest.mark.parametrize("mode", ["character_profile", "character_visual_plan"])
def test_retired_character_response_modes_are_rejected(mode):
    with pytest.raises(ValidationError) as exc:
        ReversePromptRequest(
            workspace_id="00000000-0000-0000-0000-000000000001",
            node_id="image-1", model="gpt-5.6-sol", media_type="image",
            media_url="https://example.com/image.png", prompt="test", response_mode=mode,
        )
    assert any(error["loc"] == ("response_mode",) for error in exc.value.errors())
