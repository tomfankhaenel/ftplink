FROM python:3.9-alpine

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY ftp_server.py /app/
RUN mkdir -p /app/ftp && \
    adduser -h /app/ftp -D ftpuser && \
    chown ftpuser -R /app
USER ftpuser
EXPOSE 2121 60000-60010
CMD ["python", "ftp_server.py"]
