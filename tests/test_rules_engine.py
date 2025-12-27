"""Tests for the rules engine module."""

import pytest

from flowcheck.core.models import FlowState, Status
from flowcheck.rules.engine import (
    calculate_status,
    generate_recommendations,
    build_flow_state,
)


@pytest.fixture
def default_config():
    """Return default configuration for testing."""
    return {
        "max_minutes_without_commit": 60,
        "max_lines_uncommitted": 500,
    }


class TestCalculateStatus:
    """Tests for calculate_status function."""

    def test_ok_status_both_under_threshold(self, default_config):
        """Test OK status when both metrics are under threshold."""
        status = calculate_status(
            minutes_since_commit=30,
            uncommitted_lines=200,
            config=default_config,
        )
        assert status == Status.OK

    def test_warning_status_time_over(self, default_config):
        """Test WARNING status when time exceeds threshold."""
        status = calculate_status(
            minutes_since_commit=70,  # Over 60
            uncommitted_lines=200,
            config=default_config,
        )
        assert status == Status.WARNING

    def test_warning_status_lines_over(self, default_config):
        """Test WARNING status when lines exceed threshold."""
        status = calculate_status(
            minutes_since_commit=30,
            uncommitted_lines=600,  # Over 500
            config=default_config,
        )
        assert status == Status.WARNING

    def test_danger_status_time_way_over(self, default_config):
        """Test DANGER status when time greatly exceeds threshold."""
        status = calculate_status(
            minutes_since_commit=100,  # Over 60 * 1.5 = 90
            uncommitted_lines=200,
            config=default_config,
        )
        assert status == Status.DANGER

    def test_danger_status_lines_way_over(self, default_config):
        """Test DANGER status when lines greatly exceed threshold."""
        status = calculate_status(
            minutes_since_commit=30,
            uncommitted_lines=800,  # Over 500 * 1.5 = 750
            config=default_config,
        )
        assert status == Status.DANGER

    def test_custom_thresholds(self):
        """Test with custom threshold values."""
        custom_config = {
            "max_minutes_without_commit": 30,
            "max_lines_uncommitted": 100,
        }

        # Should be warning with default config, but OK here
        status = calculate_status(
            minutes_since_commit=40,
            uncommitted_lines=50,
            config=custom_config,
        )
        assert status == Status.WARNING


class TestGenerateRecommendations:
    """Tests for generate_recommendations function."""

    def test_healthy_repo_no_warnings(self, default_config):
        """Test that healthy repo gets positive message."""
        flow_state = FlowState(
            minutes_since_last_commit=30,
            uncommitted_lines=200,
            uncommitted_files=3,
            branch_name="main",
            status=Status.OK,
        )

        recs = generate_recommendations(flow_state, default_config)
        assert len(recs) == 1
        assert "healthy" in recs[0].lower()

    def test_time_nudge_generated(self, default_config):
        """Test that time-based nudge is generated."""
        flow_state = FlowState(
            minutes_since_last_commit=90,  # Over threshold
            uncommitted_lines=100,
            uncommitted_files=2,
            branch_name="main",
            status=Status.WARNING,
        )

        recs = generate_recommendations(flow_state, default_config)
        assert any("checkpoint" in r.lower() for r in recs)

    def test_lines_nudge_generated(self, default_config):
        """Test that lines-based nudge is generated."""
        flow_state = FlowState(
            minutes_since_last_commit=30,
            uncommitted_lines=600,  # Over threshold
            uncommitted_files=5,
            branch_name="main",
            status=Status.WARNING,
        )

        recs = generate_recommendations(flow_state, default_config)
        assert any("uncommitted lines" in r.lower() for r in recs)

    def test_files_warning(self, default_config):
        """Test that file count warning is generated."""
        flow_state = FlowState(
            minutes_since_last_commit=30,
            uncommitted_lines=200,
            uncommitted_files=15,  # Over 10
            branch_name="main",
            status=Status.OK,
        )

        recs = generate_recommendations(flow_state, default_config)
        assert any("files" in r.lower() for r in recs)


class TestBuildFlowState:
    """Tests for build_flow_state function."""

    def test_builds_complete_flow_state(self, default_config):
        """Test that complete FlowState is built."""
        raw_metrics = {
            "branch_name": "feature/test",
            "minutes_since_last_commit": 45,
            "uncommitted_files": 3,
            "uncommitted_lines": 150,
        }

        flow_state = build_flow_state(raw_metrics, default_config)

        assert flow_state.branch_name == "feature/test"
        assert flow_state.minutes_since_last_commit == 45
        assert flow_state.uncommitted_files == 3
        assert flow_state.uncommitted_lines == 150
        assert flow_state.status == Status.OK

    def test_status_is_calculated(self, default_config):
        """Test that status is correctly calculated."""
        raw_metrics = {
            "branch_name": "main",
            "minutes_since_last_commit": 70,  # Over threshold
            "uncommitted_files": 2,
            "uncommitted_lines": 100,
        }

        flow_state = build_flow_state(raw_metrics, default_config)
        assert flow_state.status == Status.WARNING
