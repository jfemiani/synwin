export PRJ_ROOT=$(git rev-parse --show-toplevel)
export DC_UID=$(id -u)
export DC_GID=$(id -g)
docker-compose -f ${PRJ_ROOT}/docker/docker-compose.yml run --rm --name synwin_machine synwin
