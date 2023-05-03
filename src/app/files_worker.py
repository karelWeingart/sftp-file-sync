from app.structures.FileWrapper import FileWrapper
import os
import logging
import queue
from typing import List, Iterator
from app.utils import set_modified_date

logger = logging.getLogger("app")
class FilesWorker:
    total_size = 0.0
    file_count = 0
    folders_checked = []

    def __init__(self, root_path: str, subfolders_for_sync: List[str], updated_files_queue: queue.Queue, threshold_epoch: float, put_timeout: int = 200) -> None:
        self.base_source_path = root_path
        self.base_target_path = root_path
        self.updated_files_queue = updated_files_queue
        self.subfolders_for_sync = subfolders_for_sync
        self.threshold_epoch = threshold_epoch
        self.put_timeout = put_timeout

    def get_files(self):
        logger.info("start gathering files needed to sync")
        if os.path.islink(self.base_source_path):
            logger.error("root file path is symlink. stopping process")
            return
        # pattern = re.compile(".*\.{0:s}$".format(ext))
        for file in self._get_files_os_scandir(self.base_source_path):
            try:
                self.updated_files_queue.put(file, timeout=self.put_timeout)
            except queue.Full:
                logger.warning(f"[SCAN_INFO] file not put into queue. Modified date will be set. File: {file}")
                set_modified_date(file.full_source_path)


    def _get_files_os_scandir(self, dir_name: str, level: int=0) -> Iterator[FileWrapper]:
        for item in os.scandir(dir_name):
            if item.is_symlink():
                logger.info(f"[SCAN_INFO] this folder {item.path} is symlink. Its ignored")
                continue
            if item.is_dir() and level == 0 and item.path in self.subfolders_for_sync:
                self.folders_checked.append(item.path)
                logger.info(
                    f"[SCAN_INFO] this folder {item.path} is included in the scan. All subitems will be processed"
                )
                yield from self._get_files_os_scandir(item.path, level=level + 1)
            elif item.is_dir() and level > 0:
                logger.info(
                    f"[SCAN_INFO] this folder {item.path} is subfolder that is included in the scan"
                )
                yield from self._get_files_os_scandir(item.path, level=level + 1)
            elif item.is_file() and item.stat().st_mtime > self.threshold_epoch:
                self.total_size += item.stat().st_size
                self.file_count += 1
                file = FileWrapper(item, self.base_source_path, self.base_target_path)
                logger.info(f"[SCAN_INFO] this file {file} will be processed.")
                yield file
