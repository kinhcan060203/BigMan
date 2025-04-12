.PHONY: install test clean build docs
# Run services
run:
	docker compose -f ./deployment/docker-compose.yml up -d

# Stop services
down:
	docker compose  -f ./deployment/docker-compose.yml down

# Delete services
delete:
	docker compose  -f ./deployment/docker-compose.yml down -v

# Build the Python package
build:
	docker buildx build -t save-video:v1.5.0 -f deployment/Dockerfile . 

push-deploy:
	docker push save-video:v1.5.0 -f deployment/Dockerfile . 