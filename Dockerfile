FROM debian
#ENV TERM=linux
#ARG DEBIAN_FRONTEND=noninteractive
ENV TZ="America/Chicago"
RUN echo $TZ > /etc/timezone
RUN apt-get update
RUN apt-get -qq install python3 python3-pip libev-dev curl
# Install your thing you need
# RUN apt -qq install somelibrary

LABEL version="1.0"
LABEL org.opencontainers.image.authors="sasha@starnix.net"

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copy the current directory contents into the container at /app
COPY yeet.py /app

# Expose the port the app runs on
EXPOSE 80

# Run the application
CMD ["python3", "yeet.py"]

