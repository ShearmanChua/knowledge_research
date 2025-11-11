import json
from pydantic import BaseModel
import os
import requests

from prompts.prompts import STEPWISE_EVALUATION_PROMPT
from utils.llm_utils import (
    extract_score_confidence
)
from utils.logger import get_logger

logger = get_logger()

def stepwise_agent_eval(step: dict, available_tools: str):
    class StepwiseScore(BaseModel):
        reason: str
        invoked_tool_correctness: float
        contextual_coherence: float
        response_completeness: float
        tool_result_correctness: float
        role_adherence: float

    schema = StepwiseScore.model_json_schema()
    schema["additionalProperties"] = False
    api_key = os.environ.get("MODEL_API_KEY")
    model = os.environ.get("MODEL_NAME")
    model_endpoint = os.environ.get("MODEL_ENDPOINT") + "/chat/completions"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "temperature": 0.7,
        "logprobs": True,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "stepwise_score_schema",
                "schema": schema,
                "strict": True
            },
        },
    }

    prompt = STEPWISE_EVALUATION_PROMPT.format(
        strategy = step["strategy"],
        system_prompt = step["system_prompt"],
        available_tools = available_tools,
        user_prompt = step["user_prompt"],
        previous_responses = step["previous_responses"],
        current_response = step["current_response"]
    )

    try:
        messages = [
            {"role": "user", "content": prompt}
        ]
        payload["messages"] = messages
        response = requests.post(model_endpoint, headers=headers, data=json.dumps(payload))
        response_dict = response.json()
        response = json.loads(response_dict["choices"][0]["message"]["content"])

        logger.info("agent stepwise eval response: %s", response)

        logprobs = extract_score_confidence(response_dict, list(response.keys()))
        new_response = {}
        for score, score_value in response.items():
            if not isinstance(score_value, str):
                new_response[score] = {
                    "score": score_value,
                    "confidence": logprobs.get(score)
                }
        response = new_response
        response["contextual_coherence"] = None if not step["previous_responses"] else response["contextual_coherence"]
        if step["strategy"].split(" -> ")[-1] == "response":
            response["invoked_tool_correctness"] = None
            response["tool_result_correctness"] = None
        else:
            response["response_completeness"] = None

        logger.info("current step: %s", step["current_response"])
        logger.info("previous responses: %s", step["previous_responses"])

    except Exception as e:
        logger.error(e)

    return response

def compute_stepwise_metrics(agent_trajectories_dict, min_score=1, max_score=5, low_quality_cutoff=2.5,
                   high_quality_cutoff=3.5, low_conf_flag=0.8):
    """
    Mutates agent_trajectories_dict in place:
      - Adds step['step_score_aggregated'] and step['step_quality']
      - Adds agent_trajectories_dict[agent]['stepwise_metrics']
    Scoring is confidence-calibrated and bounded within [min_score, max_score].
    """

    def calibrate(score, conf):
        # Clamp raw score
        s = max(min_score, min(score, max_score))
        mid = (min_score + max_score) / 2
        # Pull toward midpoint when confidence is low
        return conf * s + (1 - conf) * mid

    for agent_name, traces in agent_trajectories_dict.items():
        # Agent-level accumulators
        metric_sum = {}
        metric_count = {}

        # Iterate traces safely
        for _, trace_data in list(traces.items()):

            steps = trace_data.get("agent_steps", []) or []

            for step in steps:
                score_data = step.get("step_score", {}) or {}

                calibrated_scores = []
                low_flag = False

                for metric_key, result in score_data.items():
                    if not isinstance(result, dict):
                        continue
                    score = result.get("score")
                    conf = result.get("confidence")
                    
                    if score is None or conf is None:
                        continue

                    # Confidence-calibrated score toward midpoint
                    cal = calibrate(score, conf)
                    calibrated_scores.append(cal)

                    # Agent-level aggregation (by metric key)
                    metric_sum[metric_key] = metric_sum.get(metric_key, 0.0) + cal
                    metric_count[metric_key] = metric_count.get(metric_key, 0) + 1

                    # Keep your original low-quality rule confidence-gated
                    if conf > low_conf_flag and cal < low_quality_cutoff:
                        low_flag = True

                # Step aggregated score (simple mean of calibrated scores)
                agg = (sum(calibrated_scores) / len(calibrated_scores)) if calibrated_scores else None
                step["step_score_aggregated"] = agg

                # Step quality classification
                if low_flag:
                    quality = "low"
                elif agg is not None and agg > high_quality_cutoff:
                    quality = "high"
                elif agg is not None and agg > low_quality_cutoff:
                    quality = "medium"
                else:
                    quality = "low"
                step["step_quality"] = quality

        # Per-agent stepwise metrics: average calibrated score per metric
        stepwise_metrics = {
            m: (metric_sum[m] / metric_count[m]) for m in metric_sum.keys() if metric_count[m] > 0
        }
        agent_trajectories_dict[agent_name]["stepwise_metrics"] = stepwise_metrics

    return agent_trajectories_dict