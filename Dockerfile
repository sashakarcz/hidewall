# Multi-stage build for Go application
FROM golang:1.23-alpine AS builder

LABEL version="5.0"
LABEL org.opencontainers.image.authors="sasha@starnix.net"
LABEL description="Hidewall - Go version for paywall bypass"

# Set working directory
WORKDIR /app

# Install git (needed for go modules)
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o hidewall .

# Final stage - minimal runtime image
FROM alpine:latest

# Install ca-certificates for HTTPS requests and timezone data
RUN apk --no-cache add ca-certificates tzdata

# Set timezone
RUN cp /usr/share/zoneinfo/America/Chicago /etc/localtime && \
    echo "America/Chicago" > /etc/timezone

# Create non-root user for security
RUN adduser -D -s /bin/sh hidewall

# Set working directory
WORKDIR /app

# Copy the binary from builder stage
COPY --from=builder /app/hidewall .

# Copy static files, templates, and config
COPY --chown=hidewall:hidewall static/ ./static/
COPY --chown=hidewall:hidewall templates/ ./templates/
COPY --chown=hidewall:hidewall service-worker.js ./
COPY --chown=hidewall:hidewall blocked_sites.txt ./

# Switch to non-root user
USER hidewall

# Expose port
EXPOSE 80

# Set environment variables
ENV PORT=80
ENV HOST=0.0.0.0

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Run the application
CMD ["sh", "-c", "echo 'Starting hidewall on' $HOST:$PORT && ./hidewall"]
