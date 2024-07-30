FROM python:3.9-slim-buster

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
        libpq-dev \
        build-essential \
        wget \
        gnupg \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome signing key and repository
RUN curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/google-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list

# Install Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt selenium==4.16.0

# Copy the rest of the application code
COPY . .

# Expose port and set environment variables
EXPOSE 4000
ENV FLASK_ENV=development

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=4000"]
