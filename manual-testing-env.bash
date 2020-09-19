#!/bin/bash   
# 
# Created Date: Tuesday, September 1st 2020, 8:18:49 pm
# Author: Domingos Rodrigues
# 
# Copyright (c) 2020 Your Company
# 
# Modified copy of script dockcross from https://github.com/dockcross/dockcross
# set -x

if [ ! "${BASH_VERSION}" ]; then
    echo "Please do not use sh to run this script ($0); use bash $0" 1>&2
    exit 1
fi

DEFAULT_DOCKER_IMG=geerlingguy/docker-centos7-ansible
DEFAULT_DOCKER_TAG=python3

DEFAULT_ANSIBLE_IMAGE=${DEFAULT_DOCKER_IMG}:${DEFAULT_DOCKER_TAG}
DEFAULT_ANSIBLE_CONFIG=$HOME/.ansible-docker

DEFAULT_DOCKER_ARGS=
CONTAINER_NAME=veredas-ldap-container

err() {
    echo -e >&2 ERROR: "$@"
}

die() {
    err "$@"
    exit 1
}

has() {
    local kind=$1
    local name=$2

    type -t "$kind":"$name" | grep -q function
}

command:update-image() {
    perform "docker pull $FINAL_IMAGE"
}

perform() {
    command=$1
    output=$($command 2>&1)
    result=$?
    if [[ $result -eq 0 ]]; then
        echo -e "\033[32mOK\033[0m"
    else
        echo -e "\033[31mERROR!\033[0m"
        echo -e "$output" >&2
        exit $result
    fi
}

command:stop() {
    echo "Stopping container $CONTAINER_NAME"
    perform "docker stop $CONTAINER_NAME"
}

command:remove() {
    echo "Removing container $CONTAINER_NAME"
    perform "docker rm $CONTAINER_NAME"
}

command:clean() {
    command:stop
    command:remove
}

command:help() {
    cat >&2 <<EOFHELP
Usage: $0 [--args|-a] [--] command [args...]

By defult, run the given *command* inside the  geerlingguy/docker-centos7-ansible Docker container
with the following options:

    --args|-a    Extra args to the *docker run* command (e.g. '--network host' )
    --image|-i   Docker based ansible image to use

Additionaly, there is a special built-in command:

    $0  update-image :   Pull the latest docker image .
    $0  clean        :   Remove container instance ($CONTAINER_NAME)
EOFHELP
    exit 1
}

#
# Process options
#
special_update_command=''
while [[ $# != 0 ]]; do
    case $1 in
        --)
            shift
            break
            ;;
        --args|-a)
            ARG_ARGS="$2"
            shift 2
            ;;
        --image|-i)
            ARG_IMAGE="$2"
            shift 2
            ;;
        --config|-c)
            ARG_CONFIG="$2"
            shift 2
            ;;
        update|update-image|clean)
            special_update_command="$1"
            break
            ;;
        --help|-h)
            command:help
            exit
            ;;
        -*)
            err Unknown option \""$1"\"
            command:help
            exit
            ;;
        *)
            break
            ;;
    esac
done

# config
FINAL_CONFIG=${ARG_CONFIG-${DEFAULT_ANSIBLE_CONFIG}}
# shellcheck source=/dev/null
[[ -f "${FINAL_CONFIG}" ]] && source "${FINAL_CONFIG}"

# docker image
FINAL_IMAGE=${ARG_IMAGE-${DEFAULT_ANSIBLE_IMAGE}}

# handle special command
if [ "x${special_update_command}" != "x" ]; then
    case $special_update_command in
        update|update-image)
            command:update-image
            exit $?
            ;;
        clean)
            command:clean
            exit $?
            ;;
    esac
fi

# echo "Debug: ${ARG_ARGS}"
# create docker instance
if [ ! "$(docker ps -q -f name=${CONTAINER_NAME})" ]; then
    if [ "$(docker ps -aq -f status=exited -f name=${CONTAINER_NAME})" ]; then
        # cleanup
        echo "cleanup"
        docker stop ${CONTAINER_NAME}
        docker rm ${CONTAINER_NAME}
    fi
    # run your container
    echo "run your container"
    cat <<EOFCMD
docker run -ti \
--detach --privileged \
--name "${CONTAINER_NAME}" \
-v /sys/fs/cgroup:/sys/fs/cgroup:ro \
-v "$(pwd)":/etc/ansible/roles/role_under_test:ro \
${ARG_ARGS-${DEFAULT_DOCKER_ARGS}} "${FINAL_IMAGE}"
EOFCMD
    # shellcheck disable=SC2086
    docker run -ti \
        --detach --privileged \
        --name "${CONTAINER_NAME}" \
        -v /sys/fs/cgroup:/sys/fs/cgroup:ro \
        -v "$(pwd)":/etc/ansible/roles/role_under_test:ro \
        ${ARG_ARGS-${DEFAULT_DOCKER_ARGS}} "${FINAL_IMAGE}"
fi

docker exec --tty \
    -w /etc/ansible/roles/role_under_test \
    ${CONTAINER_NAME} \
    env TERM=xterm "$@"
run_exit_code=$?

exit $run_exit_code
