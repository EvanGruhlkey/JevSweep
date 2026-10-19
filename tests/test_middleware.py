from pathlib import Path

from contextlens.filtering import PruneConfig, PruneSession
from contextlens.middleware import ToolResultMiddleware
from contextlens.receipts import ReceiptStore
from tests.test_filtering import FakeJudge, noise


def test_wrapped_tool_filters_automatically_and_recovers(tmp_path: Path) -> None:
    store = ReceiptStore(tmp_path)
    session = PruneSession(
        store,
        task="fix bug",
        judge=FakeJudge(0.0),
        config=PruneConfig(minimum_tokens=0),
    )
    middleware = ToolResultMiddleware(session, minimum_expected_savings=10)
    raw = noise()
    wrapped = middleware.wrap("shell", lambda arguments: raw)
    result = wrapped({"command": "npm ci"})
    assert result != raw
    assert store.read(session.outcomes[0].receipt_id) == raw


def test_wrapper_skips_small_and_error_results(tmp_path: Path) -> None:
    judge = FakeJudge(0.0)
    session = PruneSession(
        ReceiptStore(tmp_path),
        task="fix bug",
        judge=judge,
        config=PruneConfig(minimum_tokens=0),
    )
    middleware = ToolResultMiddleware(session, minimum_expected_savings=500)
    assert middleware.wrap("read_file", lambda arguments: "short")({}) == "short"
    error = "Traceback (most recent call last):\n" + noise()
    assert middleware.wrap("shell", lambda arguments: error)({}) == error
    assert not judge.states
