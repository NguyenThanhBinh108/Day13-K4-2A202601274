from __future__ import annotations

from app import agent as agent_module


class ManagedPrompt:
    version = 3

    def compile(self, **variables: str) -> str:
        return (
            f"Feature={variables['feature']}\n"
            f"Docs={variables['docs']}\n"
            f"Question={variables['message']}"
        )


class RecordingLangfuseClient:
    def __init__(self) -> None:
        self.prompt = ManagedPrompt()
        self.trace_updates: list[dict] = []
        self.generation_updates: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        return self.prompt

    def update_current_trace(self, **kwargs) -> None:
        self.trace_updates.append(kwargs)

    def update_current_generation(self, **kwargs) -> None:
        self.generation_updates.append(kwargs)


def test_agent_links_prompt_version_to_trace_and_generation(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    monkeypatch.setenv("LANGFUSE_PROMPT_LABEL", "production")
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)

    agent = agent_module.LabAgent()
    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Explain traces",
    )

    trace_metadata = client.trace_updates[-1]["metadata"]
    generation_update = client.generation_updates[-1]
    assert trace_metadata == {
        "prompt_name": "day13-chat",
        "prompt_label": "production",
        "prompt_version": "3",
        "prompt_source": "langfuse",
    }
    assert generation_update["prompt"] is client.prompt
    assert generation_update["metadata"]["prompt_version"] == "3"


def test_trace_carries_correlation_id_so_traces_link_back_to_logs(monkeypatch) -> None:
    from structlog.contextvars import bind_contextvars, clear_contextvars

    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret-key")
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)

    clear_contextvars()
    bind_contextvars(correlation_id="req-abc12345")
    try:
        agent_module.LabAgent.run.__wrapped__(
            agent_module.LabAgent(),
            user_id="student-01",
            feature="monitoring",
            session_id="session-01",
            message="Where is the bottleneck?",
        )
    finally:
        clear_contextvars()

    trace_update = client.trace_updates[-1]
    assert "cid:req-abc12345" in trace_update["tags"]
    assert client.generation_updates[-1]["metadata"]["correlation_id"] == "req-abc12345"
    # Metadata của trace vẫn chỉ chứa 4 field prompt như public test yêu cầu.
    assert "correlation_id" not in trace_update["metadata"]


def test_correlation_id_falls_back_when_agent_runs_outside_a_request() -> None:
    from structlog.contextvars import bind_contextvars, clear_contextvars

    clear_contextvars()
    assert agent_module.current_correlation_id() == agent_module.UNKNOWN_CORRELATION_ID

    # "MISSING" là giá trị placeholder của middleware khi chưa hoàn thiện; không được
    # để nó trôi lên trace và trông như một correlation ID thật.
    bind_contextvars(correlation_id="MISSING")
    try:
        assert agent_module.current_correlation_id() == agent_module.UNKNOWN_CORRELATION_ID
    finally:
        clear_contextvars()
