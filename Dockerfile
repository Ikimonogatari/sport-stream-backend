FROM python:3.9-slim-buster

# Install PostgreSQL development libraries and build essentials
RUN apt-get update && \
    apt-get install -y libpq-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
# Install Google Chrome
RUN apt-get update && apt-get install -y wget
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get update && apt-get install -y google-chrome-stable
    
RUN pip install -r requirements.txt

# Install ChromeDriver and Selenium version 4
RUN pip install --no-cache-dir selenium==4.16.0

COPY . .

EXPOSE 4000

ENV FLASK_ENV=development
CMD ["flask", "run", "--host=0.0.0.0", "--port=4000"]
