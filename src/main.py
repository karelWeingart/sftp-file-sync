# this script is installed on webtools instance in source region (now it is Virginia)
# dependencies to be installed: boto3, pysftp, threading (see installPyModules.sh in packer folder)
# this script cannot handle deleted files
# these env vars must be set before running this script:
# SFTP_HOST: hostname or ip address of destination server.
# SFTP_USER: user name used to login to the destination server.
# SFTP_PASSWORD: password used to login to the destination server.


import sys
import logging
from datetime import datetime

from app.synchronizer import Synchronizer
from app.utils import EnvVars
from argparse import Namespace


logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)



def main():
    current_start_time = datetime.now()
    args = EnvVars.parse_opts()
    
    sync_task = Synchronizer(args, current_start_time)
    sync_task.start_sync()
    sys.exit(0)

if __name__ == "__main__":
    main()

