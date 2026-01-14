#!/bin/bash
IMAGE_NAME="lucera"
CONTAINER_NAME="lucera_runner"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' 

function show_usage {
    echo "Lucera Workflow Automation"
    echo "--------------------------"
    echo "Usage: ./lucera.sh [command] [arguments]"
    echo ""
    echo "Commands:"
    echo "  build           Build the Docker image"
    echo "  run <file>      Process a video file (auto-builds if needed)"
    echo "  stop            Stop the currently running container"
    echo "  clean           Remove the Docker image and cached containers"
    echo "  help            Show this help message"
}
function get_abs_path {
    python3 -c "import os,sys; print(os.path.abspath(sys.argv[1]))" "$1"
}

case "$1" in
    build)
        echo -e "${GREEN}Building Docker image '${IMAGE_NAME}'...${NC}"
        docker build -t $IMAGE_NAME .
        ;;

    run)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please provide a video file path.${NC}"
            echo "Usage: ./lucera.sh run path/to/video.mp4"
            exit 1
        fi

        VIDEO_PATH="$2"
        ABS_PATH=$(get_abs_path "$VIDEO_PATH")
        DIR_NAME=$(dirname "$ABS_PATH")
        FILE_NAME=$(basename "$ABS_PATH")

        # Check if image exists, if not build it
        if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
            echo -e "Image not found. Building first..."
            docker build -t $IMAGE_NAME .
        fi

        echo -e "${GREEN}Processing: $FILE_NAME${NC}"
        echo "Mounting: $DIR_NAME -> /data"
        docker run --rm --name $CONTAINER_NAME \
            -v "$DIR_NAME":/data \
            $IMAGE_NAME \
            /data/"$FILE_NAME"
        ;;

    stop)
        echo -e "${GREEN}Stopping container '${CONTAINER_NAME}'...${NC}"
        docker stop $CONTAINER_NAME 2>/dev/null || echo "Container was not running."
        ;;

    clean)
        echo -e "${GREEN}Cleaning up...${NC}"
        docker rm -f $CONTAINER_NAME 2>/dev/null
        docker rmi $IMAGE_NAME 2>/dev/null
        echo "Cleanup complete."
        ;;

    *)
        show_usage
        exit 1
        ;;
esac
