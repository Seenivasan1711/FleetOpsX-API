docker run -d \
  --name fleetopsx-postgres \
  -e POSTGRES_USER=fleetopsx \
  -e POSTGRES_PASSWORD=fleetopsx \
  -e POSTGRES_DB=fleetopsx \
  -p 5432:5432 \
  postgres:15
