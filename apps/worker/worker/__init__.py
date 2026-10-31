"""CPU worker process for the shared detection queue."""

from worker.consumer import process_job

__all__ = ["process_job"]
