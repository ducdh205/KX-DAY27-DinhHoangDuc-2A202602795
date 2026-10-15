"""Offline checks for routing boundaries, graph wiring, and LLM contract."""

import unittest
from unittest.mock import Mock, patch

from common.schemas import AUTO_APPROVE_THRESHOLD, ESCALATE_THRESHOLD, PRAnalysis
from exercises import exercise_1_confidence as exercise


def analysis_at(confidence):
    return PRAnalysis(
        summary="Synthetic review for an offline test.",
        confidence=confidence,
        confidence_reasoning="Synthetic confidence for testing routing only.",
    )


class ConfidenceRoutingTests(unittest.TestCase):
    def test_threshold_boundaries(self):
        for confidence, expected in [
            (0.0, "escalate"),
            (ESCALATE_THRESHOLD - 0.001, "escalate"),
            (ESCALATE_THRESHOLD, "human_approval"),
            (AUTO_APPROVE_THRESHOLD - 0.001, "human_approval"),
            (AUTO_APPROVE_THRESHOLD, "auto_approve"),
            (1.0, "auto_approve"),
        ]:
            with self.subTest(confidence=confidence):
                self.assertEqual(
                    exercise.node_route({"analysis": analysis_at(confidence)}),
                    {"decision": expected},
                )

    def test_analyze_uses_structured_output_and_both_pr_fields(self):
        expected = analysis_at(ESCALATE_THRESHOLD)
        structured_llm = Mock()
        structured_llm.invoke.return_value = expected
        with patch.object(exercise, "get_llm") as factory:
            factory.return_value.with_structured_output.return_value = structured_llm
            result = exercise.node_analyze({"pr_title": "Test title", "pr_diff": "+test diff"})
        factory.return_value.with_structured_output.assert_called_once_with(PRAnalysis)
        messages = structured_llm.invoke.call_args.args[0]
        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        self.assertIn("Test title", messages[1]["content"])
        self.assertIn("+test diff", messages[1]["content"])
        self.assertIs(result["analysis"], expected)

    def test_graph_reaches_each_terminal(self):
        for confidence, decision, final_action in [
            (AUTO_APPROVE_THRESHOLD, "auto_approve", "auto_approved"),
            (ESCALATE_THRESHOLD, "human_approval", "pending_human_approval"),
            (ESCALATE_THRESHOLD - 0.001, "escalate", "pending_escalation"),
        ]:
            with self.subTest(decision=decision):
                fetch = Mock(return_value={"pr_title": "Offline PR", "pr_diff": "+offline"})
                analyze = Mock(return_value={"analysis": analysis_at(confidence)})
                with (
                    patch.object(exercise, "node_fetch_pr", fetch),
                    patch.object(exercise, "node_analyze", analyze),
                ):
                    graph = exercise.build_graph()
                    result = graph.invoke({"pr_url": "https://example.test/pull/1"})
                fetch.assert_called_once()
                analyze.assert_called_once()
                self.assertEqual(analyze.call_args.args[0]["pr_title"], "Offline PR")
                self.assertEqual(result["decision"], decision)
                self.assertEqual(result["final_action"], final_action)
                self.assertNotIn("__interrupt__", result)


if __name__ == "__main__":
    unittest.main()
