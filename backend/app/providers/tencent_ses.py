import asyncio
import json
import logging

from tencentcloud.common import credential
from tencentcloud.ses.v20201002 import models, ses_client

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class TencentSesSendError(RuntimeError):
    pass


def _send_verification_email(email: str, code: str) -> None:
    settings = get_settings()
    if not settings.tencent_cloud_secret_id or not settings.tencent_cloud_secret_key:
        raise TencentSesSendError("腾讯云 SES 未配置")
    client = ses_client.SesClient(
        credential.Credential(
            settings.tencent_cloud_secret_id,
            settings.tencent_cloud_secret_key,
        ),
        settings.tencent_ses_region,
    )
    request = models.SendEmailRequest()
    request.from_json_string(
        json.dumps(
            {
                "FromEmailAddress": settings.tencent_ses_from_email,
                "Destination": [email],
                "Subject": "商图 AI 注册验证码",
                "Template": {
                    "TemplateID": settings.tencent_ses_template_id,
                    "TemplateData": json.dumps({"code": code}),
                },
            }
        )
    )
    client.SendEmail(request)


async def send_verification_email(email: str, code: str) -> None:
    try:
        await asyncio.to_thread(_send_verification_email, email, code)
    except Exception as exc:
        logger.exception("Tencent SES verification email failed")
        raise TencentSesSendError("验证码邮件发送失败，请稍后重试") from exc
