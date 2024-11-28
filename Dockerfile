# Use the official Python image
FROM python:3.12

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install necessary packages
RUN pip install python-for-android kivy sqlalchemy pg8000

# Command to run your application or build your APK
CMD ["python", "-m", "pythonforandroid", "apk", "--private", "/app", "--package", "org.example.chatapp", "--name", "ChatApp", "--version", "0.1", "--bootstrap", "sdl2", "--requirements", "python3,kivy,sqlalchemy,pg8000"]
