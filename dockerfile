# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Make port 5006 available to the world outside this container
EXPOSE 5006

# Define environment variable
ENV NAME FileSelectorApp

# Define environment variable to allow WebSocket origins
ENV BOKEH_ALLOW_WS_ORIGIN=34.238.220.120:5006

# Run the file selector application
CMD ["panel", "serve", "app.py", "--address", "0.0.0.0", "--port", "5006", "--allow-websocket-origin=0.0.0.0:5006"]