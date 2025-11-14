"""
Functions for computing tool metrics
"""

import json
import os
import pandas as pd
from pydantic import BaseModel
import requests

from prompts.prompts import TOOL_USEFULNESS_PROMPT

from utils.logger import get_logger

logger = get_logger()


def compute_tool_latencies(tool_spans: pd.DataFrame) -> pd.DataFrame:
    """Add latency column and sort by start_time."""
    tool_spans["start_time"] = pd.to_datetime(tool_spans["start_time"])
    tool_spans["end_time"] = pd.to_datetime(tool_spans["end_time"])
    tool_spans["latency"] = (
        tool_spans["end_time"] - tool_spans["start_time"]
    ).dt.total_seconds()
    return tool_spans.sort_values(by="start_time")


def aggregate_tool_stats(group: pd.DataFrame) -> dict:
    """Aggregate total calls, successful calls, and latency for a tool group."""
    total_calls = group.shape[0]
    successful_calls = group[group["status_code"] != "ERROR"].shape[0]
    total_latency = group["latency"].sum()
    return {
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "total_latency": total_latency,
    }


def finalize_tool_stats(stats: dict) -> dict:
    """Convert aggregated totals to success rate and average latency."""
    total = stats["total_calls"]
    success = stats["successful_calls"]
    total_latency = stats["total_latency"]
    return {
        "number_of_times_invoked": total,
        "success_rate": (success / total) * 100 if total else 0.0,
        "average_latency": total_latency / total if total else 0.0,
    }


def compute_jaccard_similarity(str1: str, str2: str) -> float:
    """
    Compute Jaccard similarity between two strings, based on token overlap.
    Much faster than difflib for long strings.
    """
    set1 = set(str1.split())
    set2 = set(str2.split())
    if not set1 and not set2:
        return 1.0
    return len(set1 & set2) / len(set1 | set2)


def compute_tool_entropy(tool_df: pd.DataFrame) -> float:
    """
    Compute entropy with information gain using Jaccard similarity.
    tool_df: DataFrame with ['index', 'input_val', 'output_val']
    """
    if tool_df.empty:
        return 1.0

    indices = tool_df["index"].to_numpy()
    successive = indices[1:] == indices[:-1] + 1

    if not successive.any():
        return 1.0

    successive_penalty = 0
    num_sequences = 1  # at least one sequence exists

    for i in range(len(successive)):
        if successive[i]:
            in_sim = compute_jaccard_similarity(
                tool_df.iloc[i]["input_val"], tool_df.iloc[i + 1]["input_val"]
            )
            out_sim = compute_jaccard_similarity(
                tool_df.iloc[i]["output_val"], tool_df.iloc[i + 1]["output_val"]
            )
            avg_sim = (in_sim + out_sim) / 2.0
            info_gain = 1 - avg_sim
            successive_penalty += 1 - info_gain
        else:
            num_sequences += 1

    total_calls = len(indices)
    max_penalty = total_calls - num_sequences if total_calls > 1 else 1
    entropy = 1 - (successive_penalty / max_penalty) if max_penalty > 0 else 1.0
    return max(min(entropy, 1.0), 0.0)


def score_tool_quality(row):
    class ToolScore(BaseModel):
        reason: str
        score: float

    schema = ToolScore.model_json_schema()
    api_key = os.environ.get("MODEL_API_KEY")
    model = os.environ.get("MODEL_NAME")
    model_endpoint = os.environ.get("MODEL_ENDPOINT") + "/chat/completions"

    # Headers
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "temperature": 0.7,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "tool_score_schema", "schema": schema},
        },
    }

    prompt = TOOL_USEFULNESS_PROMPT.format(
        tool_name=row["attributes.tool.name"],
        tool_description=row["attributes.tool.description"],
        tool_arguments=row["attributes.input.value"],
        tool_results=row["attributes.output.value"],
    )

    try:
        messages = [{"role": "user", "content": prompt}]
        payload["messages"] = messages
        response = requests.post(
            model_endpoint, headers=headers, data=json.dumps(payload)
        )
        response_dict = response.json()
        response = json.loads(response_dict["choices"][0]["message"]["content"])
        score = response["score"]
        reason = response["reason"]
        logger.info(response)
    except Exception as e:
        logger.error(e)

    return pd.Series([score, reason])


def score_tool_quality(row):
    class ToolScore(BaseModel):
        reason: str
        score: float

    schema = ToolScore.model_json_schema()
    api_key = os.environ.get("MODEL_API_KEY")
    model = os.environ.get("MODEL_NAME")
    model_endpoint = os.environ.get("MODEL_ENDPOINT") + "/chat/completions"

    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "temperature": 0.7,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "tool_score_schema", "schema": schema},
        },
    }

    prompt = TOOL_USEFULNESS_PROMPT.format(
        tool_name=row["attributes.tool.name"],
        tool_description=row["attributes.tool.description"],
        tool_arguments=row["attributes.input.value"],
        tool_results=row["attributes.output.value"],
    )

    try:
        messages = [{"role": "user", "content": prompt}]
        payload["messages"] = messages
        response = requests.post(
            model_endpoint, headers=headers, data=json.dumps(payload)
        )
        response_dict = response.json()
        response = json.loads(response_dict["choices"][0]["message"]["content"])
        score = response["score"]
        reason = response["reason"]
        logger.info(response)
    except Exception as e:
        logger.error(e)

    return pd.Series([score, reason])
