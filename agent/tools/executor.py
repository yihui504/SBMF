"""
Parallel Executor for Agent Tools

Provides parallel execution capabilities for agent operations
to improve performance.
"""
import time
import threading
from typing import Any, Callable, List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field


@dataclass
class ExecutionTask:
    """A task to execute"""
    id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    timeout: Optional[float] = None


@dataclass
class ExecutionResult:
    """Result of an execution task"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class ParallelExecutor:
    """
    Parallel executor for agent operations

    Executes multiple tasks in parallel using thread pools,
    with support for timeout and error handling.
    """

    def __init__(self, max_workers: int = 4, default_timeout: float = 30.0):
        """
        Initialize parallel executor

        Args:
            max_workers: Maximum number of worker threads
            default_timeout: Default timeout for tasks in seconds
        """
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self._executor: Optional[ThreadPoolExecutor] = None

    def __enter__(self):
        """Context manager entry"""
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    # ================================================================
    # Batch Execution
    # ================================================================

    def execute_batch(self, tasks: List[ExecutionTask]) -> List[ExecutionResult]:
        """
        Execute a batch of tasks in parallel

        Args:
            tasks: List of tasks to execute

        Returns:
            List of execution results
        """
        if not self._executor:
            # Create temporary executor for this batch
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                return self._execute_with_executor(executor, tasks)

        return self._execute_with_executor(self._executor, tasks)

    def _execute_with_executor(self, executor: ThreadPoolExecutor,
                               tasks: List[ExecutionTask]) -> List[ExecutionResult]:
        """Execute tasks with a specific executor"""
        futures: Dict[Future, str] = {}
        task_map: Dict[str, ExecutionTask] = {}

        # Submit all tasks
        for task in tasks:
            future = executor.submit(self._execute_single, task)
            futures[future] = task.id
            task_map[task.id] = task

        # Collect results
        results = []
        for future in as_completed(futures):
            task_id = futures[future]
            task = task_map[task_id]

            try:
                result_data, exec_time = future.result(
                    timeout=task.timeout or self.default_timeout
                )
                results.append(ExecutionResult(
                    task_id=task_id,
                    success=True,
                    result=result_data,
                    execution_time_ms=exec_time
                ))
            except TimeoutError:
                results.append(ExecutionResult(
                    task_id=task_id,
                    success=False,
                    error="Execution timeout"
                ))
            except Exception as e:
                results.append(ExecutionResult(
                    task_id=task_id,
                    success=False,
                    error=str(e)
                ))

        return results

    def _execute_single(self, task: ExecutionTask) -> Tuple[Any, float]:
        """Execute a single task and return result with timing"""
        start_time = time.time()
        result = task.func(*task.args, **task.kwargs)
        elapsed = (time.time() - start_time) * 1000
        return result, elapsed

    # ================================================================
    # Map Operations
    # ================================================================

    def map(self, func: Callable, items: List[Any],
            timeout: Optional[float] = None) -> List[Any]:
        """
        Apply a function to a list of items in parallel

        Args:
            func: Function to apply
            items: List of items
            timeout: Optional timeout

        Returns:
            List of results (not ExecutionResult objects)
        """
        tasks = [
            ExecutionTask(
                id=f"map_{i}",
                func=func,
                args=(item,)
            )
            for i, item in enumerate(items)
        ]

        exec_results = self.execute_batch(tasks)
        return [r.result for r in exec_results if r.success]

    def map_with_kwargs(self, func: Callable,
                        items: List[Tuple[tuple, dict]]) -> List[ExecutionResult]:
        """
        Apply a function to items with args and kwargs in parallel

        Args:
            func: Function to apply
            items: List of (args, kwargs) tuples

        Returns:
            List of execution results
        """
        tasks = [
            ExecutionTask(
                id=f"map_{i}",
                func=func,
                args=args,
                kwargs=kwargs
            )
            for i, (args, kwargs) in enumerate(items)
        ]

        return self.execute_batch(tasks)

    # ================================================================
    # Utility Methods
    # ================================================================

    def execute_parallel(self, funcs: List[Callable]) -> List[Any]:
        """
        Execute multiple functions in parallel

        Args:
            funcs: List of functions to execute

        Returns:
            List of results in order of completion
        """
        tasks = [
            ExecutionTask(
                id=f"func_{i}",
                func=func
            )
            for i, func in enumerate(funcs)
        ]

        results = self.execute_batch(tasks)
        return [r.result for r in results if r.success]

    def execute_sequential(self, funcs: List[Callable]) -> List[Any]:
        """
        Execute functions sequentially (for comparison)

        Args:
            funcs: List of functions to execute

        Returns:
            List of results
        """
        results = []
        for func in funcs:
            results.append(func())
        return results


# ================================================================
# Convenience Functions
# ================================================================

def execute_parallel(funcs: List[Callable],
                     max_workers: int = 4) -> List[Any]:
    """
    Convenience function to execute functions in parallel

    Args:
        funcs: List of functions
        max_workers: Maximum worker threads

    Returns:
        List of results
    """
    with ParallelExecutor(max_workers=max_workers) as executor:
        return executor.execute_parallel(funcs)


__all__ = [
    "ExecutionTask",
    "ExecutionResult",
    "ParallelExecutor",
    "execute_parallel",
]
