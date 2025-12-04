from autogen_core import CancellationToken
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    UserMessage,
    LLMMessage,
    SystemMessage,
)

from autogen_core.tools import FunctionTool
import json
from typing import List
from tools.tool_tracing_utils import trace_span_info
from utils.logger import get_logger

logger = get_logger()

class BaseReflection:
    def __init__(self,
                 system_message: str
                ):
        self._system_message = SystemMessage(content=system_message)
        self._thought = ""
        self._thinking_prompt = (
            "Based on context above, use the tools available to "
            "you to think and follow a step-by-step thought process "
            "that will guide you to the solution to the task. "
            "The thought should be in the form of a markdown list "
            "with a checkbox at the start of each step. "
            "Update your thought process as the task progresses."
        )
        tools = [
            FunctionTool(
                name="create_thought",
                description="Create a thought process",
                func=self.create_thought,
            ),
            FunctionTool(
                name="get_thought",
                description="Get the current thought process",
                func=self.get_thought,
            ),
            FunctionTool(
                name="update_thought",
                description="Update the current thought process",
                func=self.update_thought,
            ),
        ]
        self._tools = dict([(tool.name, tool) for tool in tools])
    @trace_span_info
    async def create_thought(self, thought: str):
        self._thought = thought
        return 'Thought created'
    @trace_span_info
    async def get_thought(self):
        return self._thought
    @trace_span_info
    async def update_thought(self, thought: str):
        self._thought = thought
        return 'Thought updated'
    async def think(self, context: List[LLMMessage],
                    model_client: ChatCompletionClient,
                    agent_type: str):
        if isinstance(context[-1], UserMessage):
            if isinstance(context[-1].content, str):
                context[-1].content += "\n\n" + self._thinking_prompt
            else:
                context[-1].content.append(self._thinking_prompt)
        else:
            context.append(UserMessage(content=self._thinking_prompt, source=agent_type))

        think_context = await self.run_reflection(context, model_client, agent_type)

        return think_context

    async def run_reflection(self, context: List[LLMMessage],
                             model_client: ChatCompletionClient,
                             agent_type: str):
        get_thought_called = False
        if self._thought:
            available_tools = [
                self._tools["get_thought"].schema,
                self._tools["update_thought"].schema
            ]
            result = await model_client.create(
                messages=[self._system_message] + context,
                tools=available_tools,
                tool_choice="required"
            )
            
            tool_execution_result = []
            get_thought_called = False
            for call in result.content:
                arguments = json.loads(call.arguments)

                if call.name in self._tools:
                    logger.info("Running tool: %s", call.name)

                    # run tool
                    try:
                        tool_result = await self._tools[call.name].run_json(
                            arguments, CancellationToken()
                        )
                        # save tool results
                        tool_execution_result.append(
                            FunctionExecutionResult(
                                name=call.name,
                                content=self._tools[call.name].return_value_as_string(
                                    tool_result
                                ),
                                call_id=call.id,
                            )
                        )
                    except Exception as e:
                        tool_execution_result.append(
                            FunctionExecutionResult(
                                name=call.name,
                                content=str(e),
                                call_id=call.id,
                                is_error=True,
                            )
                        )

                if call.name == "get_thought":
                    get_thought_called = True
            
            if get_thought_called:
                context.append(
                    AssistantMessage(content=result.content, source=agent_type)
                )
                context.append(
                    FunctionExecutionResultMessage(content=tool_execution_result)
                )
                think_context = await self.run_reflection(context, model_client, agent_type)
            else:
                think_context = []
                think_context.append(
                    AssistantMessage(content=result.content, source=agent_type)
                )
                think_context.append(
                    FunctionExecutionResultMessage(content=tool_execution_result)
                )

        else:
            result = await model_client.create(
                messages=[self._system_message] + context,
                tools=[
                    self._tools["create_thought"].schema
                ],
                tool_choice=self._tools["create_thought"]
            )
            context.append(
                AssistantMessage(content=result.content, source=agent_type)
            )
            tool_execution_result = []
            for call in result.content:
                arguments = json.loads(call.arguments)

                if call.name in self._tools:
                    logger.info("Running tool: %s", call.name)

                    # run tool
                    try:
                        tool_result = await self._tools[call.name].run_json(
                            arguments, CancellationToken()
                        )
                        # save tool results
                        tool_execution_result.append(
                            FunctionExecutionResult(
                                name=call.name,
                                content=self._tools[call.name].return_value_as_string(
                                    tool_result
                                ),
                                call_id=call.id,
                            )
                        )
                    except Exception as e:
                        tool_execution_result.append(
                            FunctionExecutionResult(
                                name=call.name,
                                content=str(e),
                                call_id=call.id,
                                is_error=True,
                            )
                        )
            think_context = []
            think_context.append(
                AssistantMessage(content=result.content, source=agent_type)
            )
            think_context.append(
                FunctionExecutionResultMessage(content=tool_execution_result)
            )
        return think_context
            