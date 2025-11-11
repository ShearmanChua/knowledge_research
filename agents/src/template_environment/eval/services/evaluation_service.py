import pandas as pd
import json
from tqdm import tqdm

from metrics.tool_metrics import (
    compute_tool_latencies,
    aggregate_tool_stats,
    finalize_tool_stats,
    compute_tool_entropy,
    score_tool_quality
)
from metrics.agent_step_metrics import (
    stepwise_agent_eval,
    compute_stepwise_metrics,
)
from utils.sql_utils import (
    Evaluation,
    Agent,
    AgentTrace,
    AgentStep,
    ToolUsefulness,
)

from utils.chat_utils import parse_chat_n

from utils.logger import get_logger

logger = get_logger()


class EvaluationService:
    def __init__(self):
        self.trace_df = None
        self.current_evaluation_id = None
        self.db = None
        self.agent_trajectories_dict = {}

    def run_evaluation(self, evaluation_id, trace_df, db):
        self.current_evaluation_id = evaluation_id
        self.db = db

        try:
            # Get evaluation results - now grouped by agent_type
            self.evaluate_trace(trace_df)
            
            result = self.agent_trajectories_dict  

            db_eval = (
                db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
            )

            if not db_eval:
                raise ValueError(f"Evaluation {evaluation_id} not found")

            # Process each agent type
            for agent, agent_data in result.items():

                # Create agent type record
                db_agent = Agent(
                    evaluation_id=evaluation_id,
                    trace_id=db_eval.trace_id,
                    name=agent,
                    tool_metrics=agent_data.get("tool_metrics", {}),
                    stepwise_metrics=agent_data.get("stepwise_metrics", {}),
                )

                db_eval.agents.append(db_agent)

                # Process each agent trace
                for trace_id, agent_trace_data in agent_data.items():
                    # Skip the tool_metrics and stepwise_metrics keys
                    if not agent_trace_data.get("agent_type"):
                        continue

                    # Create agent trace record
                    db_agent_trace = AgentTrace(
                        invocation_id=trace_id,
                        agent_type=agent_trace_data.get("agent_type", agent),
                        invocation_msg=agent_trace_data.get("invocation", {}).get(
                            "invocation_msg", ""
                        ),
                        invocated_by=agent_trace_data.get("invocation", {}).get(
                            "invocated_by", "Unknown"
                        ),
                        available_tools=agent_trace_data.get("available_tools", ""),
                        chat_history=agent_trace_data.get("chat_history", []),
                    )

                    # Save agent steps
                    for i, step in enumerate(agent_trace_data.get("agent_steps", [])):
                        step_score = step.get("step_score", {})

                        db_step = AgentStep(
                            step_index=i,
                            system_prompt=step.get("system_prompt", ""),
                            user_prompt=step.get("user_prompt", ""),
                            strategy=step.get("strategy", ""),
                            previous_responses=step.get("previous_responses"),
                            current_response=step.get("current_response", ""),
                            chat_index=step.get("chat_index", 0),
                            step_score=step_score,
                            step_score_aggregated=step.get("step_score_aggregated"),
                            step_quality=step.get("step_quality"),
                        )
                        db_agent_trace.agent_steps.append(db_step)

                    db_agent.agent_traces.append(db_agent_trace)

            # Update status to completed
            db_eval.status = "COMPLETED"
            db.flush()   # assign all FKs
            db.commit()
        except Exception as e:
            db.rollback()   # rollback FIRST
            db_eval = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
            if db_eval:
                db_eval.status = "FAILED"
                db.commit()
            print(f"Error running evaluation: {str(e)}")

    def evaluate_trace(self, df: pd.DataFrame):

        self.curate_agent_trajectories_dict(df)
        self.calculate_tool_metrics()
        self.calculate_tool_usefulness(df)
        self.evaluate_agent_steps()

        return 

    def curate_agent_trajectories_dict(self, df: pd.DataFrame):
        agent_spans = df[df["span_kind"] == "AGENT"]

        for _, parent_row in agent_spans.iterrows():
            # Initialize agent if not present
            if parent_row["name"] not in self.agent_trajectories_dict:
                self.agent_trajectories_dict[parent_row["name"]] = {}

            # Filter and sort LLM spans
            completion_spans_columns_to_drop = [
                "events",
                "attributes.output.mime_type",
                "attributes.tool.name",
                "attributes.tool_name",
                "attributes.tool.description",
                "attributes.tool_description",
                "attributes.tool.parameters",
                "attributes.input.mime_type",
                "attributes.tool_args",
                "attributes.message_context",
                "attributes.recipient_agent_type",
                "attributes.recipient_agent_class",
                "attributes.messaging",
                "attributes.sender_agent_type",
                "attributes.available tools",
                "attributes.sender_agent_class",
                "attributes.message",
            ]

            completion_spans = df[
                (df["parent_id"] == parent_row["context.span_id"])
                & (df["span_kind"] == "LLM")
            ].sort_values("start_time")

            completion_spans.drop(
                completion_spans_columns_to_drop, axis=1, errors="ignore", inplace=True
            )

            # Filter and sort TOOL spans
            tool_spans_columns_to_drop = [
                "events",
                "attributes.output.mime_type",
                "attributes.llm.tools",
                "attributes.input.mime_type",
                "attributes.llm.token_count.prompt",
                "attributes.llm.output_messages",
                "attributes.llm.token_count.total",
                "attributes.llm.token_count.completion",
                "attributes.llm.system",
                "attributes.llm.invocation_parameters",
                "attributes.llm.input_messages",
                "attributes.llm.model_name",
                "attributes.llm.provider",
                "attributes.tool_name",
                "attributes.tool_description",
                "attributes.status",
                "attributes.tool_args",
                "attributes.message_context",
                "attributes.recipient_agent_type",
                "attributes.recipient_agent_class",
                "attributes.messaging",
                "attributes.sender_agent_type",
                "attributes.available tools",
                "attributes.sender_agent_class",
                "attributes.message",
            ]

            tool_spans = df[
                (df["parent_id"] == parent_row["context.span_id"])
                & (df["span_kind"] == "TOOL")
            ].sort_values("start_time")

            tool_spans.drop(
                tool_spans_columns_to_drop, axis=1, errors="ignore", inplace=True
            )

            # Clean invocation field
            invocation_msg = parent_row.get("attributes.input.value", None)
            invocated_by = parent_row.get("attributes.sender_agent_type", None)
            invocation = {"invocation_msg": invocation_msg, "invoked_by": invocated_by}
            available_tools = parent_row.get("attributes.available tools", None)

            self.agent_trajectories_dict[parent_row["name"]][
                parent_row["context.span_id"]
            ] = {
                "tool_spans": tool_spans,
                "completion_spans": completion_spans,
                "agent_type": parent_row["name"],
                "invocation": invocation,
                "available_tools": available_tools,
            }

        return

    def calculate_tool_metrics(self):

        tool_success_rate = {}
        for agent, traces in tqdm(
            self.agent_trajectories_dict.items(), desc="Processing agents"
        ):
            metrics = self.process_agent_tool_metrics(agent, traces)
            tool_success_rate[agent] = metrics
            self.agent_trajectories_dict[agent]["tool_metrics"] = metrics

        logger.info(
            "Tool Success Rate: %s",
            (
                json.dumps(tool_success_rate, indent=4, sort_keys=True)
                if tool_success_rate
                else tool_success_rate
            ),
        )

        return

    def process_agent_tool_metrics(self, agent_name: str, agent_traces: dict) -> dict:
        """Process all traces for a single agent and return metrics."""
        metrics = {
            "tool_calls": 0,
            "successful_tool_calls": 0,
            "tool_success_rate": 0.0,
            "tools_invoked": {},
            "invalid_tools_invoked": {},
        }
        all_tool_sequence_full = []

        for invocation_trace in tqdm(
            agent_traces.values(), desc=f"Processing {agent_name}", leave=False
        ):
            tool_spans = compute_tool_latencies(invocation_trace["tool_spans"].copy())

            all_tool_sequence_full.extend(
                list(
                    zip(
                        tool_spans["attributes.tool.name"],
                        tool_spans["attributes.input.value"].astype(str),
                        tool_spans["attributes.output.value"].astype(str),
                    )
                )
            )

            metrics["tool_calls"] += len(tool_spans)
            metrics["successful_tool_calls"] += tool_spans[
                tool_spans["status_code"] != "ERROR"
            ].shape[0]

            valid_tool_spans = tool_spans[
                tool_spans["attributes.tool.description"] != "Invalid tool"
            ]
            for tool_name, group in valid_tool_spans.groupby("attributes.tool.name"):
                agg_stats = aggregate_tool_stats(group)
                if tool_name not in metrics["tools_invoked"]:
                    metrics["tools_invoked"][tool_name] = agg_stats
                else:
                    for k in agg_stats:
                        metrics["tools_invoked"][tool_name][k] += agg_stats[k]

            invalid_tool_spans = tool_spans[
                tool_spans["attributes.tool.description"] == "Invalid tool"
            ]
            for tool_name, group in invalid_tool_spans.groupby("attributes.tool.name"):
                agg_stats = aggregate_tool_stats(group)
                if tool_name not in metrics["invalid_tools_invoked"]:
                    metrics["invalid_tools_invoked"][tool_name] = agg_stats
                else:
                    for k in agg_stats:
                        metrics["invalid_tools_invoked"][tool_name][k] += agg_stats[k]

        if metrics["tool_calls"]:
            metrics["tool_success_rate"] = (
                metrics["successful_tool_calls"] / metrics["tool_calls"]
            ) * 100

        for tool_name, stats in metrics["tools_invoked"].items():
            metrics["tools_invoked"][tool_name] = finalize_tool_stats(stats)

        for tool_name, stats in metrics["invalid_tools_invoked"].items():
            metrics["invalid_tools_invoked"][tool_name] = finalize_tool_stats(stats)

        df_full_seq = pd.DataFrame(
            all_tool_sequence_full, columns=["tool_name", "input_val", "output_val"]
        )
        df_full_seq.reset_index(inplace=True)

        for tool_name in metrics["tools_invoked"]:
            tool_df = df_full_seq[df_full_seq["tool_name"] == tool_name]
            metrics["tools_invoked"][tool_name]["tool_entropy"] = compute_tool_entropy(
                tool_df
            )

        return metrics

    def calculate_tool_usefulness(self, df: pd.DataFrame):
        tqdm.pandas()
        tools_df = df[
            (df["span_kind"] == "TOOL")
        ].sort_values("start_time")
        tools_df[["tool.quality.score", "tool.quality.reason"]] = (
            tools_df.progress_apply(score_tool_quality, axis=1)
        )

        # Group by tool name and trace and aggregate
        tool_quality_df = (
            tools_df.groupby(["name", "context.trace_id"])
            .agg(
                {
                    "tool.quality.score": "mean",
                    "tool.quality.reason": lambda x: " | ".join(x.dropna().astype(str)),
                }
            )
            .reset_index()
        )

        # Optional: Rename columns for clarity
        tool_quality_df.rename(
            columns={
                "name": "tool_name",
                "context.trace_id": "trace_id",
                "tool.quality.score": "avg_tool_quality_score",
                "tool.quality.reason": "combined_tool_quality_reasons",
            },
            inplace=True,
        )

        # Save to database
        for _, row in tool_quality_df.iterrows():
            tool_usefulness = ToolUsefulness(
                trace_id=row["trace_id"],  # NEW
                tool_name=row["tool_name"],
                tool_usefulness_reason=row["combined_tool_quality_reasons"],
                tool_usefulness=row["avg_tool_quality_score"],
            )
            self.db.add(tool_usefulness)

        self.db.commit()

        return

    def evaluate_agent_steps(self, num_previous_steps=2):
        """
        Evaluate agent steps
        """

        for agent, agent_traces in tqdm(
            self.agent_trajectories_dict.items(), desc="Parsing chat history"
        ):
            for trace_id, trace in agent_traces.items():
                if "completion_spans" in trace and len(trace["completion_spans"]) > 0:
                    completion_dict = trace["completion_spans"].iloc[-1].to_dict()
                    chat_history = (
                        completion_dict["attributes.llm.input_messages"]
                        + completion_dict["attributes.llm.output_messages"]
                    )
                    agent_steps = parse_chat_n(chat_history, num_previous_steps)
                    self.agent_trajectories_dict[agent][trace_id][
                        "agent_steps"
                    ] = agent_steps
                    self.agent_trajectories_dict[agent][trace_id][
                        "chat_history"
                    ] = chat_history

        for agent, agent_traces in tqdm(
            self.agent_trajectories_dict.items(), desc="Evaluating agent steps"
        ):
            for trace_id, trace in agent_traces.items():
                if "agent_steps" in trace:
                    available_tools = trace.get("available_tools", "")
                    for step in trace["agent_steps"]:
                        step["step_score"] = stepwise_agent_eval(step, available_tools)
        
        agent_trajectories_dict = compute_stepwise_metrics(self.agent_trajectories_dict)
        self.agent_trajectories_dict = agent_trajectories_dict

        return
