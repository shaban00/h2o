# Stage 1: Base build stage
FROM python:3.11-slim AS builder
 
# Install build dependencies (C compiler, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create the app directory
RUN mkdir /app

# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Upgrade pip and install dependencies
RUN pip install --upgrade pip

# Copy the requirements file first (better caching)
COPY web/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim

# Install runtime dependencies (for uWSGI)
RUN apt-get update && apt-get install -y \
    libpcre3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and set up the app directory
RUN useradd -m -r h2o && \
   mkdir /app && \
   chown -R h2o /app

# Copy the Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Set the working directory
WORKDIR /app

# Copy application code
COPY --chown=h2o:h2o web/ .

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER h2o

# Expose the application port
EXPOSE 8000

# Start the application using uWSGI
CMD ["uwsgi", "--http", "0.0.0.0:8000", "--module", "config.wsgi:application", "--master", "--processes", "2", "--threads", "4", "--harakiri", "120"]
