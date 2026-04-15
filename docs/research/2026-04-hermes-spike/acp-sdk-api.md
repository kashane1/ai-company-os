# ACP SDK API — agent-client-protocol 0.8.1 (hermes v0.7.0 pin)

Introspected 2026-04-14 from /Users/simons/hermes/.venv (python 3.14).
Hermes v0.7.0 pins `agent-client-protocol>=0.8.1,<0.9` in `pyproject.toml`.

`acp_adapter/server.py:12-40` imports these symbols from `acp.schema`:
`AuthMethod, InitializeResponse, AgentCapabilities, SessionCapabilities,`
`ClientCapabilities, Implementation, SessionForkCapabilities,`
`SessionListCapabilities, AuthenticateResponse`. At 0.9.0 the `AuthMethod`
symbol was removed from `acp.schema` in favor of the three-variant union
`EnvVarAuthMethod | TerminalAuthMethod | AuthMethodAgent` — running
`pip install "agent-client-protocol==0.9.0"` and re-running `python -m acp_adapter.entry`
produces `ImportError: cannot import name 'AuthMethod' from 'acp.schema'`.
Phase 4 client MUST pin `>=0.8.1,<0.9` until a future hermes release
updates its own imports.

## Public surface of acp.__init__

- dict   AGENT_METHODS
- class  Agent(*args, **kwargs)
- class  Any(*args, **kwargs)
- class  AuthenticateRequest(*, _meta: Dict[str, Any] | None = None, methodId: str) -> None
- class  AuthenticateResponse(*, _meta: Dict[str, Any] | None = None) -> None
- dict   CLIENT_METHODS
- class  CancelNotification(*, _meta: Dict[str, Any] | None = None, sessionId: str) -> None
- class  Client(*args, **kwargs)
- class  CreateTerminalRequest(*, _meta: Dict[str, Any] | None = None, args: List[str] | None = None, command: str, cwd: str | None = None, env: List[acp.schema.EnvVariable] | None = None, outputByteLimit: Annotated[int | None, Ge(ge=0)] = None, sessionId: str) -> None
- class  CreateTerminalResponse(*, _meta: Dict[str, Any] | None = None, terminalId: str) -> None
- class  InitializeRequest(*, _meta: Dict[str, Any] | None = None, clientCapabilities: acp.schema.ClientCapabilities | None = ClientCapabilities(field_meta=None, fs=FileSystemCapability(field_meta=None, read_text_file=False, write_text_file=False), terminal=False), clientInfo: acp.schema.Implementation | None = None, protocolVersion: Annotated[int, Ge(ge=0), Le(le=65535)]) -> None
- class  InitializeResponse(*, _meta: Dict[str, Any] | None = None, agentCapabilities: acp.schema.AgentCapabilities | None = AgentCapabilities(field_meta=None, load_session=False, mcp_capabilities=McpCapabilities(field_meta=None, http=False, sse=False), prompt_capabilities=PromptCapabilities(field_meta=None, audio=False, embedded_context=False, image=False), session_capabilities=SessionCapabilities(field_meta=None, fork=None, list=None, resume=None)), agentInfo: acp.schema.Implementation | None = None, authMethods: List[acp.schema.AuthMethod] | None = [], protocolVersion: Annotated[int, Ge(ge=0), Le(le=65535)]) -> None
- class  KillTerminalCommandRequest(*, _meta: Dict[str, Any] | None = None, sessionId: str, terminalId: str) -> None
- class  KillTerminalCommandResponse(*, _meta: Dict[str, Any] | None = None) -> None
- class  LoadSessionRequest(*, _meta: Dict[str, Any] | None = None, cwd: str, mcpServers: List[acp.schema.HttpMcpServer | acp.schema.SseMcpServer | acp.schema.McpServerStdio], sessionId: str) -> None
- class  LoadSessionResponse(*, _meta: Dict[str, Any] | None = None, configOptions: List[acp.schema.SessionConfigOption] | None = None, models: acp.schema.SessionModelState | None = None, modes: acp.schema.SessionModeState | None = None) -> None
- class  NewSessionRequest(*, _meta: Dict[str, Any] | None = None, cwd: str, mcpServers: List[acp.schema.HttpMcpServer | acp.schema.SseMcpServer | acp.schema.McpServerStdio]) -> None
- class  NewSessionResponse(*, _meta: Dict[str, Any] | None = None, configOptions: List[acp.schema.SessionConfigOption] | None = None, models: acp.schema.SessionModelState | None = None, modes: acp.schema.SessionModeState | None = None, sessionId: str) -> None
- int    PROTOCOL_VERSION
- class  PromptRequest(*, _meta: Dict[str, Any] | None = None, prompt: List[acp.schema.TextContentBlock | acp.schema.ImageContentBlock | acp.schema.AudioContentBlock | acp.schema.ResourceContentBlock | acp.schema.EmbeddedResourceContentBlock], sessionId: str) -> None
- class  PromptResponse(*, _meta: Dict[str, Any] | None = None, stopReason: Literal['end_turn', 'max_tokens', 'max_turn_requests', 'refusal', 'cancelled'], usage: acp.schema.Usage | None = None) -> None
- class  ReadTextFileRequest(*, _meta: Dict[str, Any] | None = None, limit: Annotated[int | None, Ge(ge=0)] = None, line: Annotated[int | None, Ge(ge=0)] = None, path: str, sessionId: str) -> None
- class  ReadTextFileResponse(*, _meta: Dict[str, Any] | None = None, content: str) -> None
- class  ReleaseTerminalRequest(*, _meta: Dict[str, Any] | None = None, sessionId: str, terminalId: str) -> None
- class  ReleaseTerminalResponse(*, _meta: Dict[str, Any] | None = None) -> None
- class  RequestError(code: 'int', message: 'str', data: 'Any | None' = None) -> 'None'
- class  RequestPermissionRequest(*, _meta: Dict[str, Any] | None = None, options: List[acp.schema.PermissionOption], sessionId: str, toolCall: acp.schema.ToolCallUpdate) -> None
- class  RequestPermissionResponse(*, _meta: Dict[str, Any] | None = None, outcome: acp.schema.DeniedOutcome | acp.schema.AllowedOutcome) -> None
- class  SessionNotification(*, _meta: Dict[str, Any] | None = None, sessionId: str, update: acp.schema.UserMessageChunk | acp.schema.AgentMessageChunk | acp.schema.AgentThoughtChunk | acp.schema.ToolCallStart | acp.schema.ToolCallProgress | acp.schema.AgentPlanUpdate | acp.schema.AvailableCommandsUpdate | acp.schema.CurrentModeUpdate | acp.schema.ConfigOptionUpdate | acp.schema.SessionInfoUpdate | acp.schema.UsageUpdate) -> None
- class  SetSessionConfigOptionRequest(*, _meta: Dict[str, Any] | None = None, configId: str, sessionId: str, value: str) -> None
- class  SetSessionConfigOptionResponse(*, _meta: Dict[str, Any] | None = None, configOptions: List[acp.schema.SessionConfigOption]) -> None
- class  SetSessionModeRequest(*, _meta: Dict[str, Any] | None = None, modeId: str, sessionId: str) -> None
- class  SetSessionModeResponse(*, _meta: Dict[str, Any] | None = None) -> None
- class  SetSessionModelRequest(*, _meta: Dict[str, Any] | None = None, modelId: str, sessionId: str) -> None
- class  SetSessionModelResponse(*, _meta: Dict[str, Any] | None = None) -> None
- class  TerminalOutputRequest(*, _meta: Dict[str, Any] | None = None, sessionId: str, terminalId: str) -> None
- class  TerminalOutputResponse(*, _meta: Dict[str, Any] | None = None, exitStatus: acp.schema.TerminalExitStatus | None = None, output: str, truncated: bool) -> None
- class  WaitForTerminalExitRequest(*, _meta: Dict[str, Any] | None = None, sessionId: str, terminalId: str) -> None
- class  WaitForTerminalExitResponse(*, _meta: Dict[str, Any] | None = None, exitCode: Annotated[int | None, Ge(ge=0)] = None, signal: str | None = None) -> None
- class  WriteTextFileRequest(*, _meta: Dict[str, Any] | None = None, content: str, path: str, sessionId: str) -> None
- class  WriteTextFileResponse(*, _meta: Dict[str, Any] | None = None) -> None
- mod    agent
- func   audio_block(data: 'str', mime_type: 'str') -> 'AudioContentBlock'
- mod    client
- func   connect_to_agent(client: 'Client', input_stream: 'Any', output_stream: 'Any', *, use_unstable_protocol: 'bool' = False, **connection_kwargs: 'Any') -> 'ClientSideConnection'
- mod    connection
- mod    core
- func   default_environment() -> 'dict[str, str]'
- func   embedded_blob_resource(uri: 'str', blob: 'str', *, mime_type: 'str | None' = None) -> 'BlobResourceContents'
- func   embedded_text_resource(uri: 'str', text: 'str', *, mime_type: 'str | None' = None) -> 'TextResourceContents'
- mod    exceptions
- mod    helpers
- func   image_block(data: 'str', mime_type: 'str', *, uri: 'str | None' = None) -> 'ImageContentBlock'
- mod    interfaces
- mod    meta
- func   plan_entry(content: 'str', *, priority: 'PlanEntryPriority' = 'medium', status: 'PlanEntryStatus' = 'pending') -> 'PlanEntry'
- func   resource_block(resource: 'TextResourceContents | BlobResourceContents') -> 'EmbeddedResourceContentBlock'
- func   resource_link_block(name: 'str', uri: 'str', *, mime_type: 'str | None' = None, size: 'int | None' = None, description: 'str | None' = None, title: 'str | None' = None) -> 'ResourceContentBlock'
- mod    router
- async  run_agent(agent: 'Agent', input_stream: 'Any' = None, output_stream: 'Any' = None, *, use_unstable_protocol: 'bool' = False, stdio_buffer_limit_bytes: 'int' = 52428800, **connection_kwargs: 'Any') -> 'None'
- mod    schema
- func   session_notification(session_id: 'str', update: 'SessionUpdate') -> 'SessionNotification'
- func   spawn_agent_process(to_client: 'Callable[[Agent], Client] | Client', command: 'str', *args: 'str', env: 'Mapping[str, str] | None' = None, cwd: 'str | Path | None' = None, transport_kwargs: 'Mapping[str, Any] | None' = None, **connection_kwargs: 'Any') -> 'AsyncIterator[tuple[ClientSideConnection, aio_subprocess.Process]]'
- func   spawn_client_process(to_agent: 'Callable[[Client], Agent] | Agent', command: 'str', *args: 'str', env: 'Mapping[str, str] | None' = None, cwd: 'str | Path | None' = None, transport_kwargs: 'Mapping[str, Any] | None' = None, **connection_kwargs: 'Any') -> 'AsyncIterator[tuple[AgentSideConnection, aio_subprocess.Process]]'
- func   spawn_stdio_connection(handler: 'MethodHandler', command: 'str', *args: 'str', env: 'Mapping[str, str] | None' = None, cwd: 'str | Path | None' = None, observers: 'list[StreamObserver] | None' = None, **transport_kwargs: 'Any') -> 'AsyncIterator[tuple[Connection, aio_subprocess.Process]]'
- func   spawn_stdio_transport(command: 'str', *args: 'str', env: 'Mapping[str, str] | None' = None, cwd: 'str | Path | None' = None, stderr: 'int | None' = -1, limit: 'int | None' = None, shutdown_timeout: 'float' = 2.0) -> 'AsyncIterator[tuple[asyncio.StreamReader, asyncio.StreamWriter, aio_subprocess.Process]]'
- func   start_edit_tool_call(tool_call_id: 'str', title: 'str', path: 'str', content: 'Any', *, extra_options: 'Sequence[ToolCallContentVariant] | None' = None) -> 'ToolCallStart'
- func   start_read_tool_call(tool_call_id: 'str', title: 'str', path: 'str', *, extra_options: 'Sequence[ToolCallContentVariant] | None' = None) -> 'ToolCallStart'
- func   start_tool_call(tool_call_id: 'str', title: 'str', *, kind: 'ToolKind | None' = None, status: 'ToolCallStatus | None' = None, content: 'Sequence[ToolCallContentVariant] | None' = None, locations: 'Sequence[ToolCallLocation] | None' = None, raw_input: 'Any | None' = None, raw_output: 'Any | None' = None) -> 'ToolCallStart'
- mod    stdio
- async  stdio_streams(limit: 'int | None' = None) -> 'tuple[asyncio.StreamReader, asyncio.StreamWriter]'
- mod    task
- mod    telemetry
- func   text_block(text: 'str') -> 'TextContentBlock'
- func   tool_content(block: 'ContentBlock') -> 'ContentToolCallContent'
- func   tool_diff_content(path: 'str', new_text: 'str', old_text: 'str | None' = None) -> 'FileEditToolCallContent'
- func   tool_terminal_ref(terminal_id: 'str') -> 'TerminalToolCallContent'
- mod    transports
- func   update_agent_message(content: 'ContentBlock') -> 'AgentMessageChunk'
- func   update_agent_message_text(text: 'str') -> 'AgentMessageChunk'
- func   update_agent_thought(content: 'ContentBlock') -> 'AgentThoughtChunk'
- func   update_agent_thought_text(text: 'str') -> 'AgentThoughtChunk'
- func   update_plan(entries: 'Iterable[PlanEntry]') -> 'AgentPlanUpdate'
- func   update_tool_call(tool_call_id: 'str', *, title: 'str | None' = None, kind: 'ToolKind | None' = None, status: 'ToolCallStatus | None' = None, content: 'Sequence[ToolCallContentVariant] | None' = None, locations: 'Sequence[ToolCallLocation] | None' = None, raw_input: 'Any | None' = None, raw_output: 'Any | None' = None) -> 'ToolCallProgress'
- func   update_user_message(content: 'ContentBlock') -> 'UserMessageChunk'
- func   update_user_message_text(text: 'str') -> 'UserMessageChunk'
- mod    utils

## PROTOCOL_VERSION

- `PROTOCOL_VERSION = 1` (int, 16-bit unsigned per
  `InitializeRequest.protocolVersion: Annotated[int, Ge(ge=0), Le(le=65535)]`).

## PromptResponse.stopReason literal values

- captured from class signature (field lookup by name failed —
  pydantic v2 exposes camelCase JSON field via alias, not attr):
  `(*, _meta: Dict[str, Any] | None = None, stopReason: Literal['end_turn', 'max_tokens', 'max_turn_requests', 'refusal', 'cancelled'], usage: acp.schema.Usage | None = None) -> None`

Verified values per the inlined Literal in `PromptResponse(*, ..., stopReason:`
Literal['end_turn','max_tokens','max_turn_requests','refusal','cancelled'])`.
There is **no 'error' variant**. JSON-RPC errors surface as typed
exceptions raised by `conn.prompt(...)`, not as a stop_reason value.
Phase 4 client must wrap prompt calls in `try/except` against the SDK
error taxonomy (see `acp.exceptions` below), not check for a sentinel stop_reason.

## RequestError shape

- `(code: 'int', message: 'str', data: 'Any | None' = None) -> 'None'`

## acp.exceptions public surface

```
Any
RequestError
annotations
```
