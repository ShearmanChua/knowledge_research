def parse_chat_n(chat, n_previous=1):
    """
    Parse a chat history into a list of steps.

    Each step contains information about the system prompt, user prompt,
    strategy used by the assistant, previous responses, current response, and
    the chat index.

    Args:
        chat (list): A list of messages in the chat history.
        n_previous (int, optional): The number of previous responses to include
            in each step. Defaults to 1.

    Returns:
        list: A list of steps, each containing information about the system
            prompt, user prompt, strategy, previous responses, current response, and
            chat index.
    """
    steps = []
    strategy = []
    system_prompt = None
    user_prompt = None
    previous_responses = []  # Rolling history of assistant responses

    for idx, msg in enumerate(chat):
        role = msg.get("message.role") or msg.get("role")

        if role == "system":
            system_prompt = msg.get("message.content") or msg.get("content")

        elif role == "user":
            user_prompt = msg.get("message.content") or msg.get("content")
            # Reset history for new user turn["step_score"]
            previous_responses = []

        elif role == "assistant":
            # if assistant message is a tool call
            if msg.get("message.tool_calls") or msg.get("tool_calls"):
                tool_calls = msg.get("message.tool_calls") or msg.get("tool_calls")
                # Format tool calls
                tool_calls_strs = [
                    f"Tool Call: {tool_call.get('tool_call.function.name')}\n"
                    f"Arguments: {tool_call.get('tool_call.function.arguments')}"
                    for tool_call in tool_calls
                ]

                tool_calls_str = "\n\n".join(tool_calls_strs)

                strategy.extend(
                    [tool_call["tool_call.function.name"] for tool_call in tool_calls]
                )

                tool_results = []

                for i in range(idx + 1, len(chat)):
                    role = chat[i].get("message.role") or chat[i].get("role")
                    if role == "tool":
                        tool_results.append(chat[i])
                    else:
                        # Stop collecting tool results if a non-tool message is reached
                        break

                if tool_results:
                    tool_results_str = [
                        f"Tool ID: {result['message.tool_call_id']}\n"
                        f"Tool Result: {result['message.content']}"
                        for result in tool_results
                    ]

                    tool_results_str = "\n\n".join(tool_results_str)
                    current_response = (
                        f"Tool_calls:\n\n{tool_calls_str}\n\n"
                        f"Tool_results:\n\n{tool_results_str}"
                    )

                else:
                    # do not process tool calls if there are no tool results
                    continue

                previous_response_str = "" if previous_responses else None

                for idx, response in enumerate(previous_responses[-n_previous:]):
                    res_num = f"---------- Previous response {-(-len(previous_responses[-n_previous:]) + idx)} ----------\n\n"
                    previous_response_str += res_num + response + "\n\n"

                # Create step
                step = {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "strategy": " -> ".join(strategy),
                    "previous_responses": previous_response_str,  # last n
                    "current_response": current_response,
                    "chat_index": idx,
                }
                steps.append(step)

                # Update history
                previous_responses.append(current_response)
                previous_responses = previous_responses[-n_previous:]

            else:
                # Normal assistant message
                assistant_response = msg.get("message.content") or msg.get("content")

                strategy.append("agent response")

                previous_response_str = "" if previous_responses else None

                for idx, response in enumerate(previous_responses[-n_previous:]):
                    res_num = f"---------- Previous response {-(-len(previous_responses[-n_previous:]) + idx)} ----------\n\n"
                    previous_response_str += res_num + response + "\n\n"

                step = {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "strategy": " -> ".join(strategy),
                    "previous_responses": previous_response_str,  # last n
                    "current_response": assistant_response,
                    "chat_index": idx,
                }
                steps.append(step)

                previous_responses.append(assistant_response)
                previous_responses = previous_responses[-n_previous:]

    return steps
