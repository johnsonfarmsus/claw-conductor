#!/usr/bin/env python3
"""
Claw Conductor Orchestrator - Main Controller

Coordinates the full autonomous development workflow:
1. Task decomposition
2. Dependency analysis
3. Parallel execution
4. Result consolidation
5. Discord reporting
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from router import Router, Task as RoutingTask
from decomposer import Decomposer
from project_manager import ProjectManager
from worker_pool import WorkerPool
from consolidator import Consolidator


class Orchestrator:
    """Main orchestration controller for Claw Conductor"""

    def __init__(self, config_path: str = None):
        """
        Initialize orchestrator with configuration

        Args:
            config_path: Path to agent-registry.json
        """
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / 'config' / 'agent-registry.json')

        self.router = Router(config_path)
        self.decomposer = Decomposer(config_path)
        self.project_manager = ProjectManager()
        self.consolidator = Consolidator()

        # Load user config
        with open(config_path, 'r') as f:
            registry = json.load(f)
        self.config = registry.get('user_config', {})

        # Initialize worker pool
        max_workers = self.config.get('max_parallel_tasks', 5)
        self.worker_pool = WorkerPool(max_workers, self.router)

        # Active projects
        self.projects: Dict[str, dict] = {}

    def execute_request(self, request: str, project_name: str = None,
                       workspace: str = None, github_user: str = None) -> dict:
        """
        Execute a complex development request

        Args:
            request: User's development request
            project_name: Optional project name (auto-generated if None)
            workspace: Optional workspace path (default: /root/projects/{name})
            github_user: Optional GitHub username for repo creation

        Returns:
            dict: Execution result with project info, tasks, and status
        """
        print(f"🎯 Orchestrator received request: {request[:100]}...")

        # Phase 1: Initialize project
        project = self._initialize_project(request, project_name, workspace, github_user)
        project_id = project['project_id']
        self.projects[project_id] = project

        print(f"📁 Project initialized: {project['name']} ({project_id})")

        # Phase 2: Decompose request into tasks
        print(f"🔍 Decomposing request into subtasks...")
        tasks = self.decomposer.decompose(request)

        if not tasks:
            return {
                'success': False,
                'error': 'Failed to decompose request into tasks',
                'project': project
            }

        print(f"📋 Decomposed into {len(tasks)} tasks:")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task['description'][:60]}... "
                  f"(complexity: {task['complexity']}, category: {task['category']})")

        # Add tasks to project
        project['tasks'] = tasks
        project['total_tasks'] = len(tasks)

        # Phase 3: Build dependency graph
        dependencies = self._build_dependency_graph(tasks)
        project['dependencies'] = dependencies

        print(f"🔗 Dependency graph built")

        # Phase 4: Route tasks to models
        print(f"🎯 Routing tasks to optimal models...")
        for task in tasks:
            routing_task = RoutingTask(
                description=task['description'],
                category=task['category'],
                complexity=task['complexity']
            )
            model_id, details = self.router.route_task(routing_task)
            task['assigned_model'] = model_id
            task['routing_details'] = details
            print(f"   • {task['description'][:50]}... → {model_id}")

        # Phase 5: Execute tasks in parallel
        print(f"⚡ Executing tasks in parallel (max {self.worker_pool.max_workers} concurrent)...")

        for task in tasks:
            self.worker_pool.schedule_task(task, project)

        # Wait for all tasks to complete
        self.worker_pool.wait_all()

        # Phase 6: Consolidate results
        print(f"📦 Consolidating results...")
        consolidation_result = self.consolidator.consolidate(project)

        # Phase 7: Update project status
        project['status'] = 'completed' if consolidation_result['success'] else 'failed'
        project['completed_at'] = datetime.now(timezone.utc).isoformat()
        project['consolidation'] = consolidation_result

        # Save final project state
        self.project_manager.save_project_state(project)

        # Return result
        return {
            'success': project['status'] == 'completed',
            'project': project,
            'github_repo': project.get('github_repo'),
            'tasks_completed': len([t for t in tasks if t['status'] == 'completed']),
            'tasks_failed': len([t for t in tasks if t['status'] == 'failed']),
            'execution_time': self._calculate_total_time(project)
        }

    def _initialize_project(self, request: str, project_name: Optional[str],
                           workspace: Optional[str], github_user: Optional[str]) -> dict:
        """Initialize project workspace and metadata"""

        # Generate project name if not provided
        if project_name is None:
            # Extract project name from request or use timestamp
            project_name = self._extract_project_name(request)

        # Create project
        project = self.project_manager.create_project(
            name=project_name,
            description=request,
            workspace=workspace,
            github_user=github_user
        )

        return project

    def _extract_project_name(self, request: str) -> str:
        """Extract a reasonable project name from request"""
        # Simple heuristic: look for common patterns
        request_lower = request.lower()

        if 'dispatch' in request_lower:
            return 'dispatch-suite'
        elif 'calculator' in request_lower:
            return 'calculator'
        elif 'todo' in request_lower or 'task' in request_lower:
            return 'task-manager'
        elif 'blog' in request_lower:
            return 'blog-system'
        else:
            # Use timestamp-based name
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
            return f'project-{timestamp}'

    def _build_dependency_graph(self, tasks: List[dict]) -> dict:
        """Build dependency graph from tasks"""
        graph = {}

        for i, task in enumerate(tasks):
            task_id = task.get('task_id', f'task-{i+1:03d}')
            task['task_id'] = task_id  # Ensure task_id is set

            dependencies = task.get('dependencies', [])
            graph[task_id] = dependencies

        return graph

    def _calculate_total_time(self, project: dict) -> float:
        """Calculate total execution time in seconds"""
        if 'started_at' not in project or 'completed_at' not in project:
            return 0.0

        start = datetime.fromisoformat(project['started_at'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(project['completed_at'].replace('Z', '+00:00'))

        return (end - start).total_seconds()

    def get_project_status(self, project_id: str) -> dict:
        """Get current status of a project"""
        if project_id not in self.projects:
            return {'error': 'Project not found'}

        project = self.projects[project_id]

        tasks = project.get('tasks', [])
        return {
            'project_id': project_id,
            'name': project['name'],
            'status': project['status'],
            'progress': {
                'total': len(tasks),
                'completed': len([t for t in tasks if t.get('status') == 'completed']),
                'failed': len([t for t in tasks if t.get('status') == 'failed']),
                'in_progress': len([t for t in tasks if t.get('status') == 'running']),
                'pending': len([t for t in tasks if t.get('status') == 'pending'])
            },
            'workers_active': self.worker_pool.get_active_count()
        }


def main():
    """Example usage"""
    orchestrator = Orchestrator()

    # Example request
    request = """
    Build a simple calculator web application with:
    - Basic arithmetic operations (add, subtract, multiply, divide)
    - Clean, modern UI
    - Responsive design
    - Unit tests
    """

    result = orchestrator.execute_request(
        request=request,
        project_name='calculator-app',
        github_user='jfasteroid'
    )

    if result['success']:
        print(f"\n✅ Project completed successfully!")
        print(f"   GitHub: {result['github_repo']}")
        print(f"   Tasks: {result['tasks_completed']}/{result['tasks_completed'] + result['tasks_failed']}")
        print(f"   Time: {result['execution_time']:.0f}s")
    else:
        print(f"\n❌ Project failed")
        print(f"   Tasks completed: {result['tasks_completed']}")
        print(f"   Tasks failed: {result['tasks_failed']}")


if __name__ == '__main__':
    main()
