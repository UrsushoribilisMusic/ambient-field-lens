"""Phase 1 wire contract: bounded inputs, independently enforced default-deny."""
import base64
import binascii
from io import BytesIO
from typing import Literal
import warnings

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_JPEG_BYTES = 2 * 1024 * 1024
MAX_BASE64_CHARS = 4 * ((MAX_JPEG_BYTES + 2) // 3)
MAX_BODY_BYTES = 3 * 1024 * 1024
MAX_IMAGE_PIXELS = 4_194_304
CALIBRATION_PENDING_DETAIL = 'Calibration not yet run (Phase 1). Verify in the manual before touching the machine.'


class AssistRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    query: str = Field(min_length=1, max_length=2000)
    image_jpeg_base64: str = Field(default='', max_length=MAX_BASE64_CHARS)

    @field_validator('query')
    @classmethod
    def nonblank_query(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 and c not in '\n\t' for c in value):
            raise ValueError('query must contain visible text without control characters')
        return value

    @field_validator('image_jpeg_base64')
    @classmethod
    def valid_jpeg(cls, value):
        if not value:
            return value  # Missing camera frame is a normal amber outcome.
        try:
            raw = base64.b64decode(value, validate=True)
            if not raw or len(raw) > MAX_JPEG_BYTES:
                raise ValueError('JPEG byte limit exceeded')
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as image:
                    if image.format != 'JPEG' or image.width * image.height > MAX_IMAGE_PIXELS:
                        raise ValueError('unsupported image format or dimensions')
                    image.verify()
                with Image.open(BytesIO(raw)) as image:
                    image.load()  # Reject truncated/corrupt pixel data, not just bad headers.
        except (ValueError, binascii.Error, OSError, UnidentifiedImageError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValueError('image must be a complete JPEG within configured limits') from exc
        return value


class AssistResponse(BaseModel):
    # This phase cannot emit a green step, even if a backend accidentally supplies one.
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True, revalidate_instances='always')
    verdict: Literal['verify'] = 'verify'
    step: None = None
    score: float = Field(default=0.0, ge=0.0, le=0.0, allow_inf_nan=False)
    detail: str = Field(default='', max_length=300)


def deny(detail):
    return AssistResponse(detail=detail)
