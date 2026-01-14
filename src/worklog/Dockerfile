FROM python:3.11-slim

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY . ./worklog/

# Run the bot
CMD ["python", "-m", "worklog.main"]
