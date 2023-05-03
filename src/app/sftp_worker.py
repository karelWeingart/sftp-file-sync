import pysftp
import sys
import os

from app.structures.FileWrapper import EStatus
import threading
import logging
from app.utils import set_modified_date
from app.structures import FileWrapper
import queue
import time
from typing import TypeVar, List

logger = logging.getLogger("app")

QueueType = TypeVar("QueueType", bound=queue.Queue)


class SftpConnectionPoolHelper(threading.Thread):
    def __init__(self, host: str, username: str, password: str) -> None:
        super(SftpConnectionPoolHelper, self).__init__()
        self.daemon = True
        self._host = host
        self._username = username
        self._password = password
        self._pause_between_attempts = 3

    def _init_connection_pool(self) -> None:
        logger.info(f"[SFTP_INIT] creating {SftpHandler.sftp_connection_pool.maxsize} connections")
        for i in range(SftpHandler.sftp_connection_pool.maxsize):
            logger.info(f"[SFTP_INIT] connection {i} will be created")
            try:
                _connection = self._get_connection()
                SftpHandler.sftp_connection_pool.put(_connection)
                logger.info(f"[SFTP_INIT] connection {i} created")
            except Exception as e:
                logger.error(f"[SFTP_INIT] connection {i} failed due to {e}")
            finally:
                time.sleep(self._pause_between_attempts)
        logger.info(f"[SYNC_INFO] created {SftpHandler.sftp_connection_pool.maxsize} connections")

    def _get_connection(self) -> pysftp.Connection:
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        cnopts.compression = True
        connection = pysftp.Connection(host=self._host, username=self._username, password=self._password, cnopts=cnopts)
        return connection

    def run(self):
        self._init_connection_pool()

    def get_connection(self):
        return self._get_connection()


class SftpWorker(threading.Thread):

    def __init__(self, file: FileWrapper,
                 conn: pysftp.Connection,
                 base_target_path: str,
                 sftp_connection_helper: SftpConnectionPoolHelper) -> None:
        super(SftpWorker, self).__init__()
        self._file = file
        self._conn = conn
        self.base_target_path = base_target_path
        self._sftp_connection_helper = sftp_connection_helper

    def run(self) -> None:
        self._validate_connection()
        try:
            if not self._conn.exists(self.base_target_path + self._file.relative_dirs):
                logger.info(
                    f"[SYNC_INFO]{self.getName()}:: folder {self.base_target_path + self._file.relative_dirs} must be "
                    f"created in target.")
                self._conn.makedirs(self.base_target_path + self._file.relative_dirs)
            self._conn.cwd(self.base_target_path + self._file.relative_dirs)
            self._conn.put(self._file.full_source_path, self._file.filename)
            self._file.end_file_processing(EStatus.SUCCESSFUL)
            logger.info(
                f"[SYNC_INFO]{self.getName()}:: upload of file {self._file.full_source_path} ends in {self._file.duration}::status={self._file.status}")
        except:
            e = sys.exc_info()
            self._file.end_file_processing(EStatus.FAILED)
            logger.warning(
                f"[SYNC_INFO]{self.getName()}::file {self._file.full_source_path} not sent to destination, following "
                f"exception occured: {e}::status={self._file.status}")
            set_modified_date(self._file.full_source_path)
        finally:
            SftpHandler.sftp_connection_pool.put(self._conn)
            SftpHandler.running_sftp_workers.remove(self.getName())

    def _validate_connection(self):
        try:
            attrs = self._conn.lstat(self.base_target_path)
            logger.info(f"[SYNC_INFO] connection is ok")
        except Exception as e:
            logger.error(f"[SYNC_INFO] connection is broken - attempt for reconnect will be done")
            self._conn = self._sftp_connection_helper.get_connection()


class SftpHandler(threading.Thread):
    running_sftp_workers: List[str] = []
    sftp_connection_pool: QueueType

    def __init__(self,
                 base_target_path: str,
                 updated_files_queue: queue.Queue,
                 pool_size: int) -> None:
        super(SftpHandler, self).__init__()

        self.base_target_path = base_target_path
        self.updated_files_queue = updated_files_queue
        SftpHandler.sftp_connection_pool = queue.Queue(maxsize=pool_size)
        self.scanning_finished = False
        self.host = os.getenv("SFTP_HOST")
        self.username = os.getenv("SFTP_USER")
        self.password = os.getenv("SFTP_PASSWORD")
        logger.info("[SFTP_INIT] start init of  connection pool")
        self._connection_helper = SftpConnectionPoolHelper(self.host, self.username, self.password)
        self._connection_helper.start()

    def run(self) -> None:
        logger.info(f"[SYNC_INFO] files gathered so far: {self.updated_files_queue.qsize()}")
        while self.updated_files_queue.qsize() > 0 or not self.scanning_finished:
            logger.info(f"[SYNC_INFO] status of sync job -  are there active cons? {self._is_connection_pool_active()}")
            if self.updated_files_queue.qsize() > 0 and SftpHandler.sftp_connection_pool.qsize() > 0:
                for i in range(min(self.updated_files_queue.qsize(), SftpHandler.sftp_connection_pool.qsize())):
                    _file = self.updated_files_queue.get()
                    self.updated_files_queue.task_done()
                    _conn = SftpHandler.sftp_connection_pool.get()
                    SftpHandler.sftp_connection_pool.task_done()
                    _worker = SftpWorker(_file, _conn, self.base_target_path, self._connection_helper)
                    logger.info(f"[SYNC_INFO] processing of file start.")
                    SftpHandler.running_sftp_workers.append(_worker.getName())
                    _worker.start()
            logger.info(f"[SYNC_INFO] this amount of files is registered: {self.updated_files_queue.qsize()}, "
                        f" this amount of available connections: {SftpHandler.sftp_connection_pool.qsize()}"
                        f" this amount of workers runs: {len(SftpHandler.running_sftp_workers)}")
            time.sleep(1)
        while len(SftpHandler.running_sftp_workers) > 0:
            logger.info(
                f"[SYNC_INFO] waiting for sftp workers to finish. Waiting for {len(SftpHandler.running_sftp_workers)} workers")
            time.sleep(10)

    def _is_connection_pool_active(self) -> bool:
        return (self.sftp_connection_pool.qsize() + len(self.running_sftp_workers)) > 0
