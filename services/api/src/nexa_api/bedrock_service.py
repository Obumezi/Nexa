"""Amazon Bedrock integration for Nexa household briefings."""

from __future__ import annotations

import json
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from nexa_api.config import get_settings

settings = get_settings()


def generate_household_briefing(
    household_context: dict[str, Any],
) -> str:
    """Generate a concise household briefing using Amazon Bedrock."""

    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.bedrock_region,
    )

    system_prompt = (
        "You are Nexa, a concise household intelligence assistant. "
        "Summarize the provided household state naturally. "
        "Use only the facts supplied. "
        "Do not invent information. "
        "Keep the answer to two or three short sentences."
    )

    user_prompt = (
        "Create a household briefing from this JSON state:\n\n"
        f"{json.dumps(household_context, default=str, indent=2)}"
    )

    try:
        response = client.converse(
            modelId=settings.bedrock_model_id,
            system=[
                {
                    "text": system_prompt,
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": user_prompt,
                        }
                    ],
                }
            ],
            inferenceConfig={
                "maxTokens": 250,
                "temperature": 0.2,
                "topP": 0.9,
            },
        )
    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(
            "Amazon Bedrock could not generate the household briefing."
        ) from exc

    content = response["output"]["message"]["content"]

    for block in content:
        text = block.get("text")

        if isinstance(text, str) and text.strip():
            return text.strip()

    raise RuntimeError(
        "Amazon Bedrock returned no text for the household briefing."
    )