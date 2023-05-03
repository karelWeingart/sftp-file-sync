from queue import Queue
from app.files_worker import FilesWorker
from app.sftp_worker import SftpHandler
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Tuple, Any
import argparse
import time




logger = logging.getLogger("app")
class Synchronizer:

    TIMESTAMP_LOG_FILE_NAME = ".file-sync-last-run"


    def __init__(self, args: argparse.Namespace, current_start_time: float) -> None:
        self.args = args
        self.current_start_time = current_start_time
        self.newly_updated_files = Queue(self.args.PROCESSED_FILES_QUEUE_SIZE)
        self.last_run_timestamp = self._get_last_run_timestamp()
        self.local_files_worker = FilesWorker(args.ROOT_FOLDER,args.SUBFOLDERS.split(","),self.newly_updated_files, self.last_run_timestamp)
        self.sftp_handler = SftpHandler(self.args.ROOT_FOLDER, self.newly_updated_files, self.args.SFTP_POOL_SIZE)

    def start_sync(self) -> None:
        logger.info("[PROCESS_INFO] start sftp handler")
        self.sftp_handler.start()
        logger.info(f"[PROCESS_INFO] waiting for {self.args.SFTP_WARM_UP_TIME} seconds for establishing connections.")
        time.sleep(self.args.SFTP_WARM_UP_TIME)
        logger.info(f"[PROCESS_INFO] connections established in {self.args.SFTP_WARM_UP_TIME} seconds."
                    f" {SftpHandler.sftp_connection_pool.qsize()} connections in pool.")
        self.local_files_worker.get_files()
        self.sftp_handler.scanning_finished = True
        self.sftp_handler.join()
        self._save_start_time_timestamp()


    @contextmanager
    def opened_w_error(self, mode: str = "r") -> Tuple[Any, Any]:
        try:
            f = open(f"{self.args.ROOT_FOLDER}/{Synchronizer.TIMESTAMP_LOG_FILE_NAME}", mode)
        except IOError as err:
            yield None, err
        else:
            try:
                yield f, None
            finally:
                f.close()

    def _get_last_run_timestamp(self) -> float:
        unix_time_float = 0.0
        unix_time_string = None
        with self.opened_w_error() as (fp, err):
            if err:
                logger.error(f"[PROCESS_INFO] there was problem with reading file at {self.args.ROOT_FOLDER}/"
                             f"{Synchronizer.TIMESTAMP_LOG_FILE_NAME}"
                                   f" with this error {err}")
            else:
                unix_time_string = fp.readline()
        if unix_time_string is not None:
            unix_time_float = float(unix_time_string)
            logger.info(f"[PROCESS_INFO] last time when this job was finished is: {unix_time_float} "
                        f"which translates to: {datetime.utcfromtimestamp(unix_time_float).strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            unix_time_calculated = datetime.now() - timedelta(hours=self.args.DEFAULT_TIMEDELTA_IN_HOURS)
            logger.warning(
                f"[PROCESS_INFO] the timestamp of last run wasnt found - check that {self.args.ROOT_FOLDER}/"
                f"{Synchronizer.TIMESTAMP_LOG_FILE_NAME} file exists and " +
                f"contains correct value. This job now will process files {self.args.DEFAULT_TIMEDELTA_IN_HOURS} hours old. "
                f"{unix_time_calculated.strftime('%Y-%m-%d %H:%M:%S')}")
            unix_time_float=unix_time_calculated.timestamp()
        return unix_time_float

    def _save_start_time_timestamp(self) -> None:
        with open(f"{self.args.ROOT_FOLDER}/{Synchronizer.TIMESTAMP_LOG_FILE_NAME}", 'w') as f:
            f.write(str(self.current_start_time.timestamp()))