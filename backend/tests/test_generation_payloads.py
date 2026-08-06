from app.core.identity import DEFAULT_WORKSPACE_ID
from app.schemas.generation import ImageGenerationRequest, VideoGenerationRequest
from app.services.generation_tasks import (
    build_image_provider_payload,
    build_video_provider_payload,
)


def test_image_provider_payloads_cover_every_model():
    cases = [
        (
            {
                "model": "gpt-image-2",
                "size": "16:9",
                "resolution": "1K",
            },
            {
                "model": "gpt-image-2",
                "prompt": "test image",
                "size": "16:9",
                "n": 1,
                "resolution": "1k",
                "response_format": "url",
            },
        ),
        (
            {
                "model": "doubao-seedream-5-0-pro",
                "size": "16:9",
                "resolution": "2K",
                "reference_images": ["https://example.com/reference.png"],
            },
            {
                "model": "doubao-seedream-5-0-pro",
                "prompt": "test image",
                "size": "16:9",
                "n": 1,
                "metadata": {"resolution": "2K", "watermark": False},
                "image_urls": ["https://example.com/reference.png"],
            },
        ),
        (
            {
                "model": "doubao-seedream-5-0",
                "size": "9:16",
                "resolution": "3K",
            },
            {
                "model": "doubao-seedream-5-0",
                "prompt": "test image",
                "size": "9:16",
                "n": 1,
                "metadata": {"resolution": "3K", "watermark": False},
            },
        ),
        (
            {
                "model": "gemini-3-pro-image-preview",
                "size": "4:3",
                "resolution": "4K",
                "reference_images": ["https://example.com/reference.png"],
            },
            {
                "model": "gemini-3-pro-image-preview",
                "prompt": "test image",
                "size": "4:3",
                "n": 1,
                "metadata": {"resolution": "4K"},
                "image_urls": ["https://example.com/reference.png"],
            },
        ),
        (
            {
                "model": "gemini-3.1-flash-image-preview",
                "size": "1:4",
                "resolution": "1K",
                "reference_images": ["https://example.com/reference.png"],
                "google_search": True,
                "google_image_search": True,
            },
            {
                "model": "gemini-3.1-flash-image-preview",
                "prompt": "test image",
                "size": "1:4",
                "n": 1,
                "metadata": {
                    "resolution": "1K",
                    "google_search": True,
                    "google_image_search": True,
                },
                "image_urls": ["https://example.com/reference.png"],
            },
        ),
    ]

    for request_data, expected in cases:
        request = ImageGenerationRequest(
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id=f"{request_data['model']}-test",
            prompt="test image",
            **request_data,
        )
        assert build_image_provider_payload(request) == expected, request.model


def test_video_provider_payloads_cover_every_model():
    cases = [
        (
            {
                "model": "seedance-2",
                "duration": 5,
                "resolution": "1080p",
                "aspect_ratio": "adaptive",
                "generate_audio": True,
            },
            {
                "model": "seedance-2",
                "prompt": "test video",
                "duration": 5,
                "resolution": "1080p",
                "aspect_ratio": "adaptive",
                "generate_audio": True,
            },
        ),
        (
            {
                "model": "seedance-2-fast",
                "duration": 8,
                "resolution": "720p",
                "aspect_ratio": "9:16",
                "generate_audio": False,
                "reference_images": ["https://example.com/one.png"],
            },
            {
                "model": "seedance-2-fast",
                "prompt": "test video",
                "duration": 8,
                "resolution": "720p",
                "aspect_ratio": "9:16",
                "generate_audio": False,
                "image_with_roles": [
                    {"url": "https://example.com/one.png", "role": "reference_image"}
                ],
            },
        ),
        (
            {
                "model": "seedance-2-mini",
                "duration": 10,
                "resolution": "480p",
                "aspect_ratio": "1:1",
                "reference_images": [
                    "https://example.com/one.png",
                    "https://example.com/two.png",
                ],
            },
            {
                "model": "seedance-2-mini",
                "prompt": "test video",
                "duration": 10,
                "resolution": "480p",
                "aspect_ratio": "1:1",
                "generate_audio": True,
                "image_with_roles": [
                    {"url": "https://example.com/one.png", "role": "reference_image"},
                    {"url": "https://example.com/two.png", "role": "reference_image"},
                ],
            },
        ),
    ]

    for request_data, expected in cases:
        request = VideoGenerationRequest(
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id=f"{request_data['model']}-test",
            prompt="test video",
            **request_data,
        )
        assert build_video_provider_payload(request) == expected, request.model
