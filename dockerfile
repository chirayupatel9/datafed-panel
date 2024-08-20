# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install panel param

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable
ENV NAME FileSelectorApp

# Run the file selector application
CMD ["panel", "serve", "filebrowser.py", "--address", "0.0.0.0", "--port", "8501"]
