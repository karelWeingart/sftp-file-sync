from enum import Enum
import time
from datetime import datetime

class EStatus(Enum):
    NOT_PROCESSED = "UPLOAD_NOT_PROCESSED"
    PROCESSING = "PROCESSING"
    SUCCESSFUL = "UPLOAD_SUCCESSFUL"
    FAILED = "UPLOAD_FAILED"





class FileWrapper:

    def __init__(self, file_entry, base_source_folder, base_target_folder) -> None:
        # self.file_entry=file_entry
        self.status = EStatus.NOT_PROCESSED
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0
        self.full_source_path = file_entry.path
        self.relative_path = file_entry.path.replace(base_source_folder, "")
        self.full_target_path = base_target_folder + self.relative_path
        self.filename = file_entry.name
        self.relative_dirs = self.relative_path.replace(self.filename, "")
        self.mtime = file_entry.stat().st_mtime
        self.size = file_entry.stat().st_size / 1024

    def _get_unix_time(self, timestamp) -> float:
        return time.mktime(timestamp.timetuple())

    def start_file_processing(self) -> None:
        self.status = EStatus.PROCESSING
        self.start_time = self._get_unix_time(datetime.now())



    def end_file_processing(self, status) -> None:
        self.status = status
        self.end_time = self._get_unix_time(datetime.now())
        self.duration = self.end_time - self.start_time

    def __str__(self) -> str:
        return f"filename={self.filename}::size={self.size}kB::" \
               f"relativepath={self.relative_path}::" \
               f"targetpath={self.full_target_path}::sourcepath={self.full_source_path}"

    def __unicode__(self) -> str:
        return f"filename={self.filename}::size={self.size}kB::" \
               f"relativepath={self.relative_path}::" \
               f"targetpath={self.full_target_path}::sourcepath={self.full_source_path}"