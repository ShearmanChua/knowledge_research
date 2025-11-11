from typing import List
import phoenix as px
from phoenix.trace.dsl import SpanQuery
import pandas as pd


# Initiate Phoenix client
px_client = px.Client()


def get_trace_spans(
    trace_id: str, span_kinds: List[str]
):  # Get spans from the last 24hrs only

    query = SpanQuery().where(
        (f"context.trace_id == '{trace_id}'" f" and span_kind in {span_kinds}")
    )

    trace_df = px_client.query_spans(
        query,
        project_name="PLACEHOLDER_project_name",
    )
    trace_df["start_time"] = pd.to_datetime(trace_df["start_time"])

    trace_df.to_csv(f"trace_{trace_id}.csv", index=False)

    return trace_df


def get_parent_details(df):
    df = df.merge(
        df[["context.span_id", "span_kind", "name", "attributes.input.value"]],
        how="left",
        left_on="parent_id",
        right_on="context.span_id",
        suffixes=("", "_parent"),
    )

    # Rename the new column
    df.rename(columns={"span_kind_parent": "parent_span_kind"}, inplace=True)
    df.rename(columns={"name_parent": "parent_name"}, inplace=True)
    df.rename(columns={"attributes.input.value_parent": "parent_input"}, inplace=True)

    # Optional: Drop the duplicate span_id column from the merge
    df.drop(columns=["context.span_id_parent"], inplace=True)

    return df


if __name__ == "__main__":
    df = get_trace_spans("8ee62c613992450b235799b04f83db4a", ["AGENT", "LLM", "TOOL"])

    df = get_parent_details(df)
