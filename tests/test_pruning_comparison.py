from contextlens.pruning.comparison import compare_strategies


def test_comparison_uses_identical_tasks_and_reports_actual_metrics():
    seen = []

    def run(task, strategy):
        seen.append((task, strategy))
        return {
            "success": True,
            "input_tokens": 100,
            "output_tokens": 20,
            "cost_usd": 0.01,
            "latency_seconds": 1.2,
        }

    rows = compare_strategies(["task one", "task two"], run)
    assert len(rows) == 6
    assert {task for task, _ in seen} == {"task one", "task two"}
    assert {strategy for _, strategy in seen} == {"baseline", "rules", "jev"}
    assert all(row["success"] is True for row in rows)
