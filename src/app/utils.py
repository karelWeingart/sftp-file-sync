import os
from datetime import datetime
import logging
import inspect, argparse

logger = logging.getLogger("app")


class EnvVars:
    SFTP_HOST = {"help": "IP or hostname of target sftp server", "type": str}
    SFTP_USER = {"help": "username used to connect to the target sftp server", "type": str}
    SFTP_PASSWORD = {"help": "username used to connect to the target sftp server", "type": str}
    SFTP_POOL_SIZE = {"help": "size of sftp connection pool. Defaults to 200", "type": int}
    SFTP_WARM_UP_TIME = {"help": "time given to sftp connection pool to establish the connections before sync start",
                         "type": int}
    ROOT_FOLDER = {"help": "root folder where the sync process starts. Defaults to /apps/web/data", "type": str}
    SUBFOLDERS = {"help": "list of subfolders (delimined by ,) which are included in the sync", "type": str}

    DEFAULT_TIMEDELTA_IN_HOURS = {"help": "how old files are checked "
                                          "ehrn .file-sync-last-run file is not found in $ROOT_FOLDER.", "type": int}
    PROCESSED_FILES_QUEUE_SIZE = {"help": "size of queue with files to be synced - "
                                          "if its exceeded then some files may not be processed.", "type": int}

    @staticmethod
    def parse_opts() -> argparse.Namespace:
        all_class_attributes = inspect.getmembers(EnvVars, lambda a: not (inspect.isroutine(a)))
        desired_class_attributes = {a[0]: a[1] for a in all_class_attributes if a[0].isupper()}
        arg_parser = argparse.ArgumentParser()
        for att_name, att_config in desired_class_attributes.items():
            full_att = f"--{att_name}"
            arg_parser.add_argument(full_att, required=True, help=att_config['help'], type=att_config['type'])
        args = arg_parser.parse_args()
        return args


def set_modified_date(filepath):
    timestamp = datetime.now().timestamp()
    if os.path.exists(filepath):
        os.utime(filepath, (timestamp, timestamp))
        logger.info(f"[SYNC_INFO] file {filepath} was set new modified date: {timestamp}")
    else:
        logger.info(f"[SYNC_INFO] file {filepath} was removed before it could be synchronized")
