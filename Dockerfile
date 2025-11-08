# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Install netcat (nc) for health checks and wait-for-db script
# We need to update package lists first.
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory in the container
WORKDIR /app

# 4. Copy the dependencies file
COPY requirements.txt .

# 5. Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the application's source code and startup script
COPY . .
COPY startup.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# 7. Expose port 8080 (Cloud Run default, but will use $PORT env var at runtime)
EXPOSE 8080

# 8. Set default PORT environment variable (Cloud Run will override this)
ENV PORT=8080

# 9. Define the command to run your application using the startup script
# The script will use the $PORT environment variable provided by Cloud Run
CMD ["start.sh"]