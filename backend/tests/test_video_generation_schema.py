import pytest
from pydantic import ValidationError

from app.core.identity import DEFAULT_WORKSPACE_ID
from app.schemas.generation import VideoGenerationRequest
from app.services.generation_tasks import build_video_provider_payload


def video_request(**updates):
    data = {
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "node_id": "video-test",
        "model": "seedance-2",
        "prompt": "test video",
        "duration": 5,
        "resolution": "720p",
        "aspect_ratio": "16:9",
    }
    return VideoGenerationRequest(**(data | updates))


@pytest.mark.parametrize(
    "updates",
    [
        {"prompt": "   "},
        {"duration": 3},
        {"resolution": "1080P"},
        {"aspect_ratio": "2:1"},
        {"reference_images": [f"https://example.com/{index}.png" for index in range(10)]},
        {
            "model": "happyhorse-1.1",
            "duration": 5,
            "resolution": "1080P",
            "generate_audio": True,
        },
    ],
)
def test_invalid_video_request(updates):
    with pytest.raises(ValidationError):
        video_request(**updates)


def test_seedance_mini_duration_options():
    request = video_request(model="seedance-2-mini", duration=8, resolution="480p")
    assert request.duration == 8


def test_provider_payloads_use_reference_mode():
    seedance = build_video_provider_payload(
        video_request(reference_images=["https://example.com/one.png"])
    )
    happyhorse = build_video_provider_payload(
        video_request(
            model="happyhorse-1.1",
            duration=5,
            resolution="1080P",
            reference_images=["https://example.com/one.png"],
        )
    )
    happyhorse_text = build_video_provider_payload(
        video_request(model="happyhorse-1.1", duration=5, resolution="1080P")
    )
    assert seedance["image_with_roles"] == [
        {"url": "https://example.com/one.png", "role": "reference_image"}
    ]
    assert happyhorse["action"] == "reference-to-video"
    assert happyhorse["reference_images"] == ["https://example.com/one.png"]
    assert "generate_audio" not in happyhorse
    assert happyhorse_text["action"] == "text-to-video"
    assert "reference_images" not in happyhorse_text
