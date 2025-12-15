import sys
from typing import Optional, Any


class Logger:
    """Enhanced logging utility with multiple severity levels and structured output."""

    @classmethod
    def info(cls, msg: str, context: Optional[dict] = None):
        """General information messages."""
        formatted_msg = f"[INFO] {msg}"
        if context:
            formatted_msg += f" | Context: {context}"
        print(formatted_msg)

    @classmethod
    def error(
        cls,
        msg: str,
        exception: Optional[Exception] = None,
        context: Optional[dict] = None,
    ):
        """Critical errors that stop execution."""
        error_msg = f"\033[91m[ERROR]\033[0m {msg}"
        if exception:
            error_msg += f" | Exception: {type(exception).__name__}: {str(exception)}"
        if context:
            error_msg += f" | Context: {context}"
        print(error_msg)

    @classmethod
    def warning(cls, msg: str, context: Optional[dict] = None):
        """Recoverable issues or potential problems."""
        warning_msg = f"\033[93m[WARNING]\033[0m {msg}"
        if context:
            warning_msg += f" | Context: {context}"
        print(warning_msg)

    @classmethod
    def debug(cls, msg: str, context: Optional[dict] = None):
        """Detailed debugging information."""
        debug_msg = f"[DEBUG] {msg}"
        if context:
            debug_msg += f" | Context: {context}"
        print(debug_msg)

    @classmethod
    def success(cls, msg: str, context: Optional[dict] = None):
        """Successful operation completion."""
        success_msg = f"\033[92m[SUCCESS]\033[0m {msg}"
        if context:
            success_msg += f" | Context: {context}"
        print(success_msg)

    @classmethod
    def dry_run(cls, msg: str, context: Optional[dict] = None):
        """Dry run simulation messages."""
        dry_msg = f"\033[93m[DRY RUN - SIMULATION]\033[0m {msg}"
        if context:
            dry_msg += f" | Context: {context}"
        print(dry_msg)

    @classmethod
    def progress(
        cls, operation: str, current: int, total: int, item: Optional[str] = None
    ):
        """Progress tracking for long-running operations."""
        percentage = (current / total) * 100 if total > 0 else 0
        msg = f"{operation}: {current}/{total} ({percentage:.1f}%)"
        if item:
            msg += f" - {item}"
        print(f"[PROGRESS] {msg}")
