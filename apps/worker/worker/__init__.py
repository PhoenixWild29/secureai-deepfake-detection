"""CPU worker process for the shared detection queue."""

from secureai_shared.reporting import install_error_log_redaction
from worker.consumer import process_job

install_error_log_redaction()

__all__ = ["process_job"]
