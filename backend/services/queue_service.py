from typing import Any, Dict, Optional
import queue
import threading
from datetime import datetime

class QueueService:
    def __init__(self):
        self.task_queue = queue.Queue()
        self.processing_queue = {}
        self.lock = threading.Lock()

    def add_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """Add a new task to the queue"""
        try:
            task = {
                'id': task_id,
                'data': task_data,
                'status': 'pending',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            self.task_queue.put(task)
            return True
        except Exception:
            return False

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task from queue"""
        try:
            if not self.task_queue.empty():
                task = self.task_queue.get()
                with self.lock:
                    self.processing_queue[task['id']] = task
                return task
            return None
        except Exception:
            return None

    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update status of a task in processing queue"""
        try:
            with self.lock:
                if task_id in self.processing_queue:
                    self.processing_queue[task_id]['status'] = status
                    self.processing_queue[task_id]['updated_at'] = datetime.now()
                    return True
            return False
        except Exception:
            return False

    def remove_task(self, task_id: str) -> bool:
        """Remove task from processing queue"""
        try:
            with self.lock:
                if task_id in self.processing_queue:
                    del self.processing_queue[task_id]
                    return True
            return False
        except Exception:
            return False

    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get status of a specific task"""
        try:
            with self.lock:
                if task_id in self.processing_queue:
                    return self.processing_queue[task_id]['status']
            return None
        except Exception:
            return None