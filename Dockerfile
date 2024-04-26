FROM python:3.6-slim-buster

# Install PostgreSQL development libraries and build essentials
RUN apt-get update && \
    apt-get install -y libpq-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY . .

EXPOSE 4000

CMD ["flask", "run", "--host=0.0.0.0", "--port=4000"]
