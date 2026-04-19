FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Final stage: tiny container that copies build output to the shared volume
FROM alpine:3.20

# Copy the built files from the builder stage
COPY --from=builder /app/dist /build-output

# On startup, copy files to the mounted volume and exit
CMD ["cp", "-r", "/build-output/.", "/dist/"]
