IMAGE_NAME = videomind
CONTAINER_NAME = videomind-app

.PHONY: build run stop

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run -d --name $(CONTAINER_NAME) -p 8501:8501 --env-file .env $(IMAGE_NAME)

stop:
	docker stop $(CONTAINER_NAME) && docker rm $(CONTAINER_NAME)