export PRJ_ROOT=$(git rev-parse --show-toplevel)
docker-compose -f ${PRJ_ROOT}/docker/docker-compose.yml build
