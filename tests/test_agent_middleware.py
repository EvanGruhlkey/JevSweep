from pathlib import Path

from contextlens.pruning import (
    ContextPruner,
    PruningSession,
    ReceiptStore,
    SemanticScores,
)
from contextlens.pruning.middleware import ToolResultMiddleware
from contextlens.pruning.transcript import compact_transcript, recover_message


class Scorer:
    backend_id = "fixture"

    def __init__(self):
        self.calls = 0

    def score(self, request):
        self.calls += 1
        return SemanticScores("fixture", {2: 1.0})


def test_wrapper_prunes_before_return_and_recovers_exact_content(tmp_path: Path):
    scorer = Scorer()
    store = ReceiptStore(tmp_path)
    session = PruningSession(
        ContextPruner(scorer, store), "fix value", minimum_tokens=0, context_radius=0
    )
    middleware = ToolResultMiddleware(session, minimum_expected_savings=1)
    source = (
        "VALUE = 1\r\nprint(VALUE)\r\n"
        + "\r\n".join(f"unused_{i} = {i}" for i in range(100))
        + "\r\n"
    )
    wrapped = middleware.wrap(lambda **kwargs: source, "read_file")
    result = wrapped(path="a.py")
    assert scorer.calls == 1
    assert result != source
    receipt_id = result.split("cl_", 1)[1][:24]
    assert store.read("cl_" + receipt_id) == source


def test_middleware_fails_open_and_skips_risky_outputs(tmp_path: Path):
    scorer = Scorer()
    session = PruningSession(
        ContextPruner(scorer, ReceiptStore(tmp_path)), "fix", minimum_tokens=0
    )
    middleware = ToolResultMiddleware(session, minimum_expected_savings=1)
    error = "Traceback (most recent call last):\n" + "x\n" * 500
    assert middleware.wrap(lambda **kwargs: error, "read_file")(path="a.py") == error
    assert middleware.wrap(lambda **kwargs: "x", "write_file")(path="a.py") == "x"
    assert scorer.calls == 0


def test_compaction_keeps_state_and_recovers_dropped_message(tmp_path: Path):
    store = ReceiptStore(tmp_path)
    messages = [{"role": "user", "content": "fix bug"}]
    messages += [
        {"role": "tool", "content": f"read {i} " + "x" * 400} for i in range(30)
    ]
    messages += [
        {"role": "tool", "content": "git diff -- changed file"},
        {"role": "assistant", "content": "working"},
    ]
    compacted = compact_transcript(messages, store, keep_recent=2, minimum_tokens=100)
    assert sum(len(str(item)) for item in compacted) < sum(
        len(str(item)) for item in messages
    )
    assert compacted[0] == messages[0]
    assert messages[-2:] == compacted[-2:]
    assert recover_message(compacted[1], store) == messages[1]
