"""
Fuzzing Agent

Agent for coordinating fuzzing operations.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import time

from agent.runtime import AgentRuntime, AgentConfig
from fuzzing.fuzzer import Fuzzer, FuzzerConfig, FuzzResult, FuzzerState
from fuzzing.mutation import MutationStrategy, Mutator
from fuzzing.feedback import FeedbackAnalyzer
from fuzzing.corpus import TestCorpus, CorpusMinimizer


@dataclass
class FuzzingSession:
    """
    A fuzzing session result
    """
    session_id: str
    total_iterations: int
    total_executions: int
    crashes_found: int
    unique_crashes: int
    hangs_found: int
    duration: float
    coverage_gain: float = 0.0
    corpus_size: int = 0
    crashes: List[FuzzResult] = None
    recommendations: List[str] = None

    def __post_init__(self):
        if self.crashes is None:
            self.crashes = []
        if self.recommendations is None:
            self.recommendations = []

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "total_iterations": self.total_iterations,
            "total_executions": self.total_executions,
            "crashes_found": self.crashes_found,
            "unique_crashes": self.unique_crashes,
            "hangs_found": self.hangs_found,
            "duration": self.duration,
            "coverage_gain": self.coverage_gain,
            "corpus_size": self.corpus_size,
            "crashes": [c.to_dict() for c in self.crashes],
            "recommendations": self.recommendations,
        }


class FuzzingAgent:
    """
    Fuzzing Agent

    Coordinates intelligent fuzzing with feedback-driven mutation.
    """

    def __init__(self, config: Optional[FuzzerConfig] = None):
        """
        Initialize fuzzing agent

        Args:
            config: Fuzzer configuration
        """
        self.config = config or FuzzerConfig()

        # Initialize agent runtime
        agent_config = AgentConfig(
            agent_id="fuzzing_agent",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(agent_config)

        # Initialize fuzzer
        self.fuzzer = Fuzzer(config)

        # Initialize components
        self.mutator = Mutator(config=self.config.__dict__)
        self.feedback = FeedbackAnalyzer() if self.config.enable_feedback else None
        self.minimizer = CorpusMinimizer()

        # Session history
        self._sessions: List[FuzzingSession] = []

    def fuzz(self, initial_inputs: List[Dict[str, Any]],
            execute_func: callable,
            max_iterations: Optional[int] = None) -> FuzzingSession:
        """
        Run fuzzing session

        Args:
            initial_inputs: Seed inputs
            execute_func: Function to execute tests
            max_iterations: Override max iterations

        Returns:
            Fuzzing session result
        """
        self.runtime.start()

        try:
            # Override config if specified
            if max_iterations:
                original_max = self.fuzzer.config.max_iterations
                self.fuzzer.config.max_iterations = max_iterations

            # Run fuzzer
            crashes = self.fuzzer.run(initial_inputs, execute_func)

            # Restore original config
            if max_iterations:
                self.fuzzer.config.max_iterations = original_max

            # Create session result
            stats = self.fuzzer.get_stats()

            # Generate recommendations
            recommendations = self._generate_recommendations(stats)

            session = FuzzingSession(
                session_id=f"session_{int(time.time())}",
                total_iterations=stats["iteration"],
                total_executions=stats["total_executions"],
                crashes_found=stats["crash_count"],
                unique_crashes=stats["unique_crash_count"],
                hangs_found=stats["hang_count"],
                duration=stats["duration"],
                corpus_size=stats["corpus_size"],
                crashes=crashes,
                recommendations=recommendations,
            )

            self._sessions.append(session)

            # Store in memory
            self.runtime.remember(
                f"fuzz_session_{session.session_id}",
                session.to_dict(),
                "long_term"
            )

            return session

        finally:
            self.runtime.stop()

    def minimize_crash(self, crash_input: Dict[str, Any],
                       execute_func: callable) -> Dict[str, Any]:
        """
        Minimize a crashing test case

        Args:
            crash_input: Crashing input
            execute_func: Function to test inputs

        Returns:
            Minimized crashing input
        """
        self.runtime.start()

        try:
            minimized = self.minimizer.minimize(crash_input, execute_func)
            return minimized

        finally:
            self.runtime.stop()

    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """Generate recommendations based on fuzzer results"""
        recommendations = []

        if stats["crash_count"] == 0:
            recommendations.append("No crashes found - consider increasing mutation rate")
            recommendations.append("Try different initial inputs")

        if stats["unique_crash_count"] > 0:
            recommendations.append(f"Found {stats['unique_crash_count']} unique crashes - prioritize analysis")

        if stats["hang_count"] > 5:
            recommendations.append("Many timeouts detected - consider reducing input complexity")

        if stats["executions_per_second"] < 10:
            recommendations.append("Low execution speed - consider parallel execution")

        if stats["corpus_size"] == 0:
            recommendations.append("No corpus growth - inputs may be too stable")

        return recommendations

    def get_session_history(self) -> List[FuzzingSession]:
        """Get all fuzzing sessions"""
        return self._sessions

    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            "agent_stats": self.runtime.get_stats(),
            "fuzzer_stats": self.fuzzer.get_stats(),
            "mutator_stats": self.mutator.get_stats(),
            "feedback_stats": self.feedback.get_stats() if self.feedback else {},
            "total_sessions": len(self._sessions),
        }


__all__ = [
    "FuzzingSession",
    "FuzzingAgent",
]
