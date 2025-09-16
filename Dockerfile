# ---- Stage 1: Download Vector ----
    FROM alpine:3.19 AS downloader

    ARG VECTOR_VERSION=0.49.0
    ARG VECTOR_ARCH=x86_64-unknown-linux-musl
    
    WORKDIR /tmp
    
    # Install curl and tar for downloading
    RUN apk add --no-cache curl tar
    
    # Download and extract Vector
    RUN curl -L https://packages.timber.io/vector/${VECTOR_VERSION}/vector-${VECTOR_ARCH}.tar.gz \
        | tar -xz -C /tmp
    
    # ---- Stage 2: Build final image ----
    FROM alpine:3.19
    
    # Set working directory
    WORKDIR /app
    
    # Copy Vector binary from downloader stage
    COPY --from=downloader /tmp/vector-x86_64-unknown-linux-musl/bin/vector /usr/local/bin/vector
    
    # Create necessary directories
    RUN mkdir -p /app/input /app/output /app/data /etc/vector /var/lib/vector
    
    # Create a dedicated user for Vector
    RUN addgroup -g 1000 vector && \
        adduser -D -s /bin/sh -u 1000 -G vector vector
    
    # Set permissions for the vector user
    RUN chown -R vector:vector /app /etc/vector /var/lib/vector
    
    # Switch to vector user
    USER vector
    
    # Default command (can be overridden in docker-compose)
    CMD ["vector"]