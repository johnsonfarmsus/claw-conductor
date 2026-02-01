#!/usr/bin/env python3
"""
Worker Pool

Manages parallel task execution with dependency awareness
and file conflict detection.
"""

import time
from typing import List, Dict, Optional, Callable
from datetime import datetime, timezone


class WorkerPool:
    """Parallel task execution pool"""

    def __init__(self, max_workers: int, router):
        """
        Initialize worker pool

        Args:
            max_workers: Maximum concurrent workers (default: 5)
            router: Router instance for model selection
        """
        self.max_workers = max_workers
        self.router = router
        self.workers: List[Dict] = []  # Active workers
        self.task_queue: List[tuple] = []  # (task, project) tuples
        self.completed_tasks: Dict[str, Dict] = {}  # task_id -> result

    def schedule_task(self, task: Dict, project: Dict):
        """
        Add task to queue and try to start it

        Args:
            task: Task dictionary
            project: Project dictionary
        """
        print(f"📥 Scheduling task: {task['task_id']} - {task['description'][:50]}...")
        self.task_queue.append((task, project))
        self._try_start_next()

    def _try_start_next(self):
        """Try to start next task if worker available"""
        if len(self.workers) >= self.max_workers:
            return

        # Find next executable task
        for task, project in list(self.task_queue):
            if self._can_execute(task, project):
                self._execute_task(task, project)
                self.task_queue.remove((task, project))
                break

    def _can_execute(self, task: Dict, project: Dict) -> bool:
        """
        Check if task can be executed now

        Args:
            task: Task to check
            project: Project containing the task

        Returns:
            bool: True if task can run now
        """
        # Check dependencies
        for dep_id in task.get('dependencies', []):
            if dep_id not in self.completed_tasks:
                return False
            if not self.completed_tasks[dep_id].get('success', False):
                # Dependency failed
                return False

        # Check file conflicts with running tasks in same project
        task_files = set(task.get('file_targets', []))
        for worker in self.workers:
            if worker['project_id'] == project['project_id']:
                worker_files = set(worker['task'].get('file_targets', []))
                if self._files_overlap(task_files, worker_files):
                    return False

        return True

    def _files_overlap(self, files1: set, files2: set) -> bool:
        """
        Check if two file sets have overlapping targets

        Args:
            files1: First set of file patterns
            files2: Second set of file patterns

        Returns:
            bool: True if files overlap
        """
        # Simple check: exact matches or wildcard overlaps
        for f1 in files1:
            for f2 in files2:
                if f1 == f2:
                    return True
                # Check for directory overlaps (e.g., "src/*" and "src/api/*")
                if f1.endswith('/*') and f2.startswith(f1[:-2]):
                    return True
                if f2.endswith('/*') and f1.startswith(f2[:-2]):
                    return True
        return False

    def _execute_task(self, task: Dict, project: Dict):
        """
        Execute a task by spawning OpenClaw Task

        Args:
            task: Task to execute
            project: Project context
        """
        print(f"🚀 Starting task: {task['task_id']} on {task['assigned_model']}")

        # Update task status
        task['status'] = 'running'
        task['started_at'] = datetime.now(timezone.utc).isoformat()

        # Create worker
        worker = {
            'worker_id': f"worker-{len(self.workers) + 1}",
            'task': task,
            'task_id': task['task_id'],
            'project_id': project['project_id'],
            'model': task['assigned_model'],
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        self.workers.append(worker)

        # Simulate task execution (replace with actual OpenClaw Task tool call)
        # TODO: Replace with real OpenClaw Task integration
        result = self._simulate_task_execution(task, project)

        # Complete task
        self._on_task_complete(worker, result)

    def _simulate_task_execution(self, task: Dict, project: Dict) -> Dict:
        """
        Simulate task execution for testing

        TODO: Replace with actual OpenClaw Task tool call:
        ```python
        from openclaw import Task as OpenClawTask

        result = OpenClawTask(
            description=f"Execute: {task['description']}",
            prompt=f'''
            You are working on project: {project['name']}
            Workspace: {project['workspace']}

            Task: {task['description']}
            Category: {task['category']}
            Complexity: {task['complexity']}

            Files to create/modify: {', '.join(task['file_targets'])}

            Complete this task and commit your changes.
            ''',
            subagent_type="general-purpose",
            model=task['assigned_model']
        )
        ```

        Args:
            task: Task to execute
            project: Project context

        Returns:
            dict: Execution result
        """
        # Simulate work (2-5 seconds per task)
        import random
        time.sleep(random.uniform(0.5, 2.0))  # Faster for testing

        # Simulate 95% success rate
        success = random.random() > 0.05

        if success:
            return {
                'success': True,
                'files_modified': task.get('file_targets', []),
                'output': f"Task {task['task_id']} completed successfully",
                'error': None
            }
        else:
            return {
                'success': False,
                'files_modified': [],
                'output': '',
                'error': f"Simulated failure for task {task['task_id']}"
            }

    def _on_task_complete(self, worker: Dict, result: Dict):
        """
        Handle task completion

        Args:
            worker: Worker that completed
            result: Task result
        """
        task = worker['task']
        task_id = task['task_id']

        # Update task
        task['status'] = 'completed' if result['success'] else 'failed'
        task['completed_at'] = datetime.now(timezone.utc).isoformat()
        task['result'] = result

        # Calculate execution time
        start = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(task['completed_at'].replace('Z', '+00:00'))
        task['execution_time'] = (end - start).total_seconds()

        # Store result
        self.completed_tasks[task_id] = result

        # Remove worker
        self.workers.remove(worker)

        # Print result
        if result['success']:
            print(f"✅ Task completed: {task_id} in {task['execution_time']:.1f}s")
        else:
            print(f"❌ Task failed: {task_id} - {result.get('error', 'Unknown error')}")

        # Try to start next task
        self._try_start_next()

    def wait_all(self):
        """Wait for all tasks to complete"""
        print(f"⏳ Waiting for all tasks to complete...")

        while self.workers or self.task_queue:
            time.sleep(0.1)  # Poll interval

        print(f"✅ All tasks completed")

    def get_active_count(self) -> int:
        """Get number of active workers"""
        return len(self.workers)

    def get_pending_count(self) -> int:
        """Get number of pending tasks"""
        return len(self.task_queue)


if __name__ == '__main__':
    # Test worker pool
    from router import Router

    router = Router('../config/agent-registry.json')
    pool = WorkerPool(max_workers=3, router=router)

    # Create mock project
    project = {
        'project_id': 'test-project',
        'name': 'test-project',
        'workspace': '/tmp/test'
    }

    # Create mock tasks
    tasks = [
        {
            'task_id': 'task-001',
            'description': 'Task 1',
            'category': 'code-generation-new-features',
            'complexity': 3,
            'dependencies': [],
            'file_targets': ['src/file1.js'],
            'assigned_model': 'mistral-devstral-2512',
            'status': 'pending'
        },
        {
            'task_id': 'task-002',
            'description': 'Task 2 (depends on 1)',
            'category': 'code-generation-new-features',
            'complexity': 3,
            'dependencies': ['task-001'],
            'file_targets': ['src/file2.js'],
            'assigned_model': 'llama-3.3-70b',
            'status': 'pending'
        },
        {
            'task_id': 'task-003',
            'description': 'Task 3 (parallel with 1)',
            'category': 'frontend-development',
            'complexity': 2,
            'dependencies': [],
            'file_targets': ['src/ui/*'],
            'assigned_model': 'mistral-devstral-2512',
            'status': 'pending'
        }
    ]

    # Schedule tasks
    for task in tasks:
        pool.schedule_task(task, project)

    # Wait for completion
    pool.wait_all()

    print(f"\nCompleted: {len(pool.completed_tasks)} tasks")
