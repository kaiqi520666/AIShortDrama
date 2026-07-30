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
        {"duration": 0},
        {"duration": 3},
        {"resolution": "1080P"},
        {"aspect_ratio": "2:1"},
        {"reference_images": [f"https://example.com/{index}.png" for index in range(10)]},
        {"reference_images": ["file:///tmp/reference.png"]},
        {"reference_audios": ["https://example.com/reference.mp3"]},
        {
            "reference_images": ["https://example.com/reference.png"],
            "reference_videos": [f"https://example.com/{index}.mp4" for index in range(4)],
        },
        {
            "reference_images": ["https://example.com/reference.png"],
            "reference_audios": [f"https://example.com/{index}.mp3" for index in range(4)],
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
        video_request(
            reference_images=["https://example.com/one.png"],
            reference_videos=["https://example.com/one.mp4"],
            reference_audios=["https://example.com/one.mp3"],
        )
    )
    assert seedance["image_with_roles"] == [
        {"url": "https://example.com/one.png", "role": "reference_image"}
    ]
    assert seedance["video_with_roles"] == [
        {"url": "https://example.com/one.mp4", "role": "reference_video"}
    ]
    assert seedance["audio_with_roles"] == [
        {"url": "https://example.com/one.mp3", "role": "reference_audio"}
    ]


def test_seedance_accepts_registered_avatar_asset_reference():
    payload = build_video_provider_payload(video_request(reference_images=["asset://pa_test"]))
    assert payload["image_with_roles"] == [{"url": "asset://pa_test", "role": "reference_image"}]


def test_seedance_can_request_last_frame_for_segment_continuity():
    payload = build_video_provider_payload(video_request(return_last_frame=True))
    assert payload["return_last_frame"] is True
