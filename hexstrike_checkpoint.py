# File: hexstrike_checkpoint.py
"""
Checkpoint system that wraps existing command execution.
Does NOT modify EnhancedProcessManager or execute_command_with_recovery.
"""

import asyncio
import time
from typing import Callable, Optional, Dict, Any
from hexstrike_persistence import get_persistence


class CheckpointExecutor:
    """
    Wraps existing command execution with checkpoint capability.
    Calls existing functions, adds checkpointing around them.
    """

    def __init__(self, checkpoint_interval: int = 30):
        self.checkpoint_interval = checkpoint_interval
        self.persistence = get_persistence()

    async def execute_with_checkpoints(
        self,
        scan_id: str,
        execute_fn: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a function with periodic checkpointing.

        Args:
            scan_id: ID of the scan (from persistence layer)
            execute_fn: The existing execution function to call
            *args, **kwargs: Arguments for execute_fn
        """
        last_checkpoint = time.time()
        output_buffer = []

        # Wrapper to capture output
        original_result = None
        checkpoint_state = {'args': args, 'kwargs': kwargs, 'started': time.time()}

        try:
            # Start checkpoint loop in background
            async def checkpoint_loop():
                nonlocal last_checkpoint
                while original_result is None:
                    await asyncio.sleep(self.checkpoint_interval)
                    if original_result is None:
                        # Simple line-based estimate
                        progress = self._estimate_progress(output_buffer)
                        self.persistence.save_checkpoint(
                            scan_id=scan_id,
                            state=checkpoint_state,
                            output_snapshot=''.join(str(x) for x in output_buffer),
                            progress=progress
                        )
                        last_checkpoint = time.time()

            # Run checkpoint loop and execution concurrently
            checkpoint_task = asyncio.create_task(checkpoint_loop())

            # Call the EXISTING execution function
            # Note: We assume the execute_fn might be blocking, so we run in executor
            loop = asyncio.get_event_loop()
            original_result = await loop.run_in_executor(
                None, lambda: execute_fn(*args, **kwargs)
            )

            # Cancel checkpoint loop
            checkpoint_task.cancel()

            return original_result

        except Exception as e:
            # Save final checkpoint on error
            self.persistence.save_checkpoint(
                scan_id=scan_id,
                state={**checkpoint_state, 'error': str(e)},
                output_snapshot=''.join(str(x) for x in output_buffer),
                progress=self._estimate_progress(output_buffer)
            )
            raise

    def resume_from_checkpoint(self, scan_id: str) -> Optional[Dict]:
        """Get checkpoint data to resume a scan"""
        checkpoint = self.persistence.get_latest_checkpoint(scan_id)
        if checkpoint:
            return {
                'state': checkpoint['state'],
                'output_so_far': checkpoint['output_snapshot'],
                'progress': checkpoint['progress'],
                'checkpoint_time': checkpoint['created_at']
            }
        return None

    def _estimate_progress(self, output: list) -> int:
        """Estimate progress based on output (simple heuristic)"""
        if not output:
            return 0
        # Simple line-based estimate
        lines = len(output)
        # Cap at 95% (100% only on completion)
        return min(95, lines)


class ResilientScanWrapper:
    """
    High-level wrapper for resilient scan execution.
    Uses existing HexStrike execution but adds persistence.
    """

    def __init__(self):
        self.persistence = get_persistence()
        self.checkpoint_executor = CheckpointExecutor()

    def start_scan(self, project_id: str, tool: str, command: str,
                   parameters: dict = None, session_id: str = None) -> str:
        """Start a tracked scan"""
        return self.persistence.start_scan(
            project_id=project_id,
            tool=tool,
            command=command,
            parameters=parameters,
            session_id=session_id
        )

    def complete_scan(self, scan_id: str, result: dict):
        """Record scan completion"""
        self.persistence.complete_scan(
            scan_id=scan_id,
            stdout=result.get('stdout', ''),
            stderr=result.get('stderr', ''),
            return_code=result.get('return_code', -1),
            execution_time=result.get('execution_time', 0),
            recovery_info=result.get('recovery_info')
        )

    def can_resume(self, scan_id: str) -> bool:
        """Check if a scan can be resumed"""
        scan = self.persistence.get_scan(scan_id)
        if not scan:
            return False
        return scan['status'] == 'running' and self.checkpoint_executor.resume_from_checkpoint(scan_id) is not None

    def get_resume_data(self, scan_id: str) -> Optional[Dict]:
        """Get data needed to resume a scan"""
        scan = self.persistence.get_scan(scan_id)
        checkpoint = self.checkpoint_executor.resume_from_checkpoint(scan_id)
        if scan and checkpoint:
            return {
                'scan': scan,
                'checkpoint': checkpoint,
                'tool': scan['tool'],
                'command': scan['command'],
                'parameters': scan['parameters']
            }
        return None
