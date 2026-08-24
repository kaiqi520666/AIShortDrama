from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.auth import validate_password


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=2, max_length=32)
    email: EmailStr
    password: str
    verification_code: str = Field(pattern=r"^\d{6}$")

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip().casefold()
        if len(value) < 2:
            raise ValueError("用户名至少需要 2 个字符")
        if any(character.isspace() or not character.isprintable() for character in value):
            raise ValueError("用户名不能包含空格或控制字符")
        return value

    @field_validator("password")
    @classmethod
    def validate_user_password(cls, value: str) -> str:
        validate_password(value)
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str


class EmailCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    captcha_token: str = Field(min_length=1, max_length=4096)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password(value)
        return value
