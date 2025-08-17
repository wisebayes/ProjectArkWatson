import os
from typing import Optional

import requests


def send_slack_message(message: str, webhook_url: Optional[str] = None) -> bool:
    url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return False
    try:
        resp = requests.post(url, json={"text": message}, timeout=10)
        return resp.status_code // 100 == 2
    except Exception:
        return False


