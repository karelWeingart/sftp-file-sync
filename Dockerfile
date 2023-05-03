# docker image for file sync: sources are copied to 'src' folder
# This app needs at least three variables to be passed to the container through -e flag
# SFTP_HOST: hostname or ip address of destination server. Set this in parameter store.
# SFTP_USER: user name used to login to the destination server. Set this in parameter store.
# SFTP_PASSWORD: password used to login to the destination server. Set this in parameter store.
# all other vars are set with default values.
FROM python:3.9-slim-bullseye
ENV SFTP_HOST=MUST_BE_SET
ENV SFTP_USER=MUST_BE_SET
ENV SFTP_PASSWORD=MUST_BE_SET
ENV SFTP_POOL_SIZE=10
ENV SFTP_WARM_UP_TIME=60
ENV ROOT_FOLDER /apps/web/data
ENV SUBFOLDERS="${ROOT_FOLDER}/htdocs"
ENV DEFAULT_TIMEDELTA_IN_HOURS=24
ENV PROCESSED_FILES_QUEUE_SIZE=1000

ENV RUN_USER sync_user
RUN apt-get update  && \
    apt-get upgrade -y

# create user/group (keep -u option values constant in all images), creating directories
RUN groupadd -g 1234 web && \
    useradd -g web -m $RUN_USER -u 1010 && \
    install -d -m 0777 -o $RUN_USER -g web /apps && \
    install -d -m 0755 -o $RUN_USER -g web /src

# switch to non root user. Since now all runs under $RUN_USER
USER $RUN_USER

COPY ./requirements.txt ./

# directory for python sources + required libs installed
RUN pip install -r requirements.txt

#folder into which source dir will be mounted (may be ommited)
RUN mkdir -p /apps/web/data


COPY ./src src/

ENTRYPOINT python /src/main.py "--SFTP_HOST=$SFTP_HOST" \
        "--SFTP_USER=$SFTP_USER" \
        "--SFTP_PASSWORD=$SFTP_PASSWORD" \
        "--SFTP_WARM_UP_TIME=$SFTP_WARM_UP_TIME" \
        "--ROOT_FOLDER=$ROOT_FOLDER" \
        "--SUBFOLDERS=$SUBFOLDERS" \
        "--SFTP_POOL_SIZE=$SFTP_POOL_SIZE" \
        "--DEFAULT_TIMEDELTA_IN_HOURS=$DEFAULT_TIMEDELTA_IN_HOURS" \
        "--PROCESSED_FILES_QUEUE_SIZE=$PROCESSED_FILES_QUEUE_SIZE" 

