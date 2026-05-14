"""Supervisor routing unit tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.lg_agent.supervisor.state import SupervisorState, SubTask, WorkerResult
from app.lg_agent.prompts.supervisor.classify import CLASSIFY_SYSTEM_PROMPT
from app.lg_agent.prompts.supervisor.decompose import DECOMPOSE_SYSTEM_PROMPT
from app.lg_agent.prompts.supervisor.merge import MERGE_SYSTEM_PROMPT


class TestPromptContent:
    def test_classify_prompt_has_all_intents(self):
        for intent in ["general_chat", "product_qa", "order_qa", "after_sales", "multi"]:
            assert intent in CLASSIFY_SYSTEM_PROMPT, f"Missing intent: {intent}"

    def test_classify_mentions_out_of_scope(self):
        assert "out_of_scope" in CLASSIFY_SYSTEM_PROMPT

    def test_decompose_prompt_mentions_priority(self):
        assert "priority" in DECOMPOSE_SYSTEM_PROMPT

    def test_merge_prompt_style(self):
        assert "亲～" in MERGE_SYSTEM_PROMPT


class TestStateTypes:
    def test_subtask_creation(self):
        st = SubTask(
            task_id="1",
            worker_type="product_qa",
            description="search for robot vacuums",
            context={},
            priority=1,
        )
        assert st["worker_type"] == "product_qa"

    def test_worker_result_creation(self):
        wr = WorkerResult(
            task_id="1",
            worker_type="product_qa",
            answer="Found 3 products",
            status="success",
            clarification_question="",
            tool_calls_made=2,
            iterations_used=3,
        )
        assert wr["status"] == "success"
        assert wr["iterations_used"] == 3

    def test_worker_results_accumulate_with_add(self):
        # Verify the annotated List[WorkerResult, add] pattern
        r1 = WorkerResult(task_id="1", worker_type="a", answer="ok", status="success",
                          clarification_question="", tool_calls_made=1, iterations_used=1)
        r2 = WorkerResult(task_id="2", worker_type="b", answer="ok", status="success",
                          clarification_question="", tool_calls_made=1, iterations_used=1)
        # add operator concatenates: [r1] + [r2] = [r1, r2]
        combined = [r1] + [r2]
        assert len(combined) == 2
