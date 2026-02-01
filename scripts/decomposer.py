#!/usr/bin/env python3
"""
Task Decomposition Engine

Analyzes complex development requests and breaks them into
independent, actionable subtasks with dependencies.
"""

import json
from pathlib import Path
from typing import List, Dict


class Decomposer:
    """Decompose complex requests into subtasks"""

    # Standard task categories from capability system
    CATEGORIES = [
        "code-generation-new-features",
        "bug-detection-fixes",
        "multi-file-refactoring",
        "unit-test-generation",
        "debugging-complex-issues",
        "api-development",
        "security-vulnerability-detection",
        "security-fixes",
        "documentation-generation",
        "code-review",
        "frontend-development",
        "backend-development",
        "database-operations",
        "codebase-exploration",
        "dependency-management",
        "legacy-modernization",
        "error-correction",
        "performance-optimization",
        "test-coverage-analysis",
        "algorithm-implementation",
        "boilerplate-generation"
    ]

    def __init__(self, config_path: str):
        """
        Initialize decomposer

        Args:
            config_path: Path to agent-registry.json
        """
        with open(config_path, 'r') as f:
            registry = json.load(f)
        self.config = registry.get('user_config', {})
        self.agents = registry.get('agents', {})

    def decompose(self, request: str) -> List[Dict]:
        """
        Decompose request into subtasks

        For MVP, uses rule-based decomposition.
        TODO: Use AI model (Perplexity or primary) for intelligent decomposition

        Args:
            request: User's development request

        Returns:
            List of task dictionaries with structure:
            {
                'description': str,
                'category': str,
                'complexity': int (1-5),
                'dependencies': List[str],  # task_ids
                'file_targets': List[str],
                'status': 'pending'
            }
        """
        # For MVP: Simple pattern-based decomposition
        # TODO: Replace with AI-powered decomposition

        request_lower = request.lower()
        tasks = []

        # Detect project type
        is_web_app = any(word in request_lower for word in
                         ['web', 'website', 'app', 'application', 'ui', 'frontend'])
        has_database = any(word in request_lower for word in
                           ['database', 'db', 'store', 'persist', 'save'])
        has_api = any(word in request_lower for word in
                      ['api', 'endpoint', 'rest', 'graphql'])
        has_auth = any(word in request_lower for word in
                       ['auth', 'login', 'user', 'account'])
        needs_tests = any(word in request_lower for word in
                          ['test', 'testing'])

        task_id_counter = 1

        # Task 1: Database (if needed)
        if has_database:
            tasks.append({
                'task_id': f'task-{task_id_counter:03d}',
                'description': 'Design and implement database schema',
                'category': 'database-operations',
                'complexity': 3,
                'dependencies': [],
                'file_targets': ['src/db/schema.sql', 'src/models/*'],
                'status': 'pending'
            })
            task_id_counter += 1

        # Task 2: Authentication (if needed, depends on database)
        if has_auth:
            deps = ['task-001'] if has_database else []
            tasks.append({
                'task_id': f'task-{task_id_counter:03d}',
                'description': 'Implement authentication system',
                'category': 'security-fixes',
                'complexity': 4,
                'dependencies': deps,
                'file_targets': ['src/auth/*', 'src/middleware/auth.js'],
                'status': 'pending'
            })
            task_id_counter += 1

        # Task 3: API (if needed)
        if has_api:
            deps = []
            if has_database:
                deps.append('task-001')
            if has_auth:
                deps.append('task-002')

            tasks.append({
                'task_id': f'task-{task_id_counter:03d}',
                'description': 'Create REST API endpoints',
                'category': 'api-development',
                'complexity': 3,
                'dependencies': deps,
                'file_targets': ['src/api/*', 'src/routes/*'],
                'status': 'pending'
            })
            task_id_counter += 1

        # Task 4: Frontend (if web app)
        if is_web_app:
            deps = []
            if has_api:
                deps.append(f'task-{task_id_counter-1:03d}')

            tasks.append({
                'task_id': f'task-{task_id_counter:03d}',
                'description': 'Build frontend user interface',
                'category': 'frontend-development',
                'complexity': 3,
                'dependencies': deps,
                'file_targets': ['src/components/*', 'src/pages/*', 'public/*'],
                'status': 'pending'
            })
            task_id_counter += 1

        # Task 5: Tests (if needed)
        if needs_tests or len(tasks) > 2:  # Auto-add tests for complex projects
            # Tests depend on all previous tasks
            deps = [t['task_id'] for t in tasks]

            tasks.append({
                'task_id': f'task-{task_id_counter:03d}',
                'description': 'Write unit tests and integration tests',
                'category': 'unit-test-generation',
                'complexity': 2,
                'dependencies': deps,
                'file_targets': ['tests/*', 'src/**/*.test.js'],
                'status': 'pending'
            })
            task_id_counter += 1

        # Task 6: Documentation
        if len(tasks) > 1:  # Add docs for multi-task projects
            tasks.append({
                'task_id': f'task-{task_id_counter:03d}',
                'description': 'Generate project documentation',
                'category': 'documentation-generation',
                'complexity': 2,
                'dependencies': [t['task_id'] for t in tasks],
                'file_targets': ['README.md', 'docs/*'],
                'status': 'pending'
            })
            task_id_counter += 1

        # Fallback: If no tasks detected, create generic task
        if not tasks:
            tasks.append({
                'task_id': 'task-001',
                'description': request,
                'category': 'code-generation-new-features',
                'complexity': self.config.get('default_complexity_if_unknown', 3),
                'dependencies': [],
                'file_targets': ['src/*'],
                'status': 'pending'
            })

        return tasks

    def decompose_with_ai(self, request: str, model_id: str = None) -> List[Dict]:
        """
        Use AI model to decompose request (future enhancement)

        Args:
            request: User's development request
            model_id: Optional model to use (default: Perplexity if available)

        Returns:
            List of task dictionaries
        """
        # TODO: Implement AI-powered decomposition
        # For now, fall back to rule-based
        return self.decompose(request)


if __name__ == '__main__':
    # Test decomposition
    decomposer = Decomposer('../config/agent-registry.json')

    test_request = """
    Build a towing dispatch system with:
    - Customer portal for requesting service
    - Driver dashboard for accepting jobs
    - Admin panel for managing users
    - Real-time location tracking
    - Database for storing jobs and users
    """

    tasks = decomposer.decompose(test_request)

    print(f"Decomposed into {len(tasks)} tasks:")
    for task in tasks:
        deps_str = f" (depends on: {', '.join(task['dependencies'])})" if task['dependencies'] else ""
        print(f"  {task['task_id']}: {task['description']}{deps_str}")
        print(f"           Category: {task['category']}, Complexity: {task['complexity']}")
