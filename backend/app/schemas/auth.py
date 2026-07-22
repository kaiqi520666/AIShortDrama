from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.auth import validate_password


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=2, max_length=32)
    email: EmailStr
    password: str

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
