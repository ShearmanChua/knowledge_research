from typing import List
import pandas as pd
import phoenix as px
from phoenix.trace.dsl import SpanQuery


def get_px_trace_spans(
    trace_id: str, project_name: str, span_kinds: List[str] = ["AGENT", "LLM", "TOOL"]
):

    px_client = px.Client()

    query = SpanQuery().where(
        (f"context.trace_id == '{trace_id}'" f" and span_kind in {span_kinds}")
    )

    trace_df = px_client.query_spans(
        query,
        project_name=project_name,
    )

    trace_df = trace_df.reset_index(drop=True)
    trace_df.loc[trace_df["status_code"] == "UNSET", "status_code"] = "OK"

    # Process the dataframe to add parent information
    trace_df = trace_df.merge(
        trace_df[["context.span_id", "span_kind", "name", "attributes.input.value"]],
        how="left",
        left_on="parent_id",
        right_on="context.span_id",
        suffixes=("", "_parent"),
    )

    # Rename the new columns
    trace_df.rename(columns={"span_kind_parent": "parent_span_kind"}, inplace=True)
    trace_df.rename(columns={"name_parent": "parent_name"}, inplace=True)
    trace_df.rename(
        columns={"attributes.input.value_parent": "parent_input"}, inplace=True
    )

    # Drop the duplicate span_id column from the merge
    trace_df.drop(columns=["context.span_id_parent"], inplace=True, errors="ignore")

    trace_df["start_time"] = pd.to_datetime(trace_df["start_time"])
    return trace_df.sort_values("start_time")
