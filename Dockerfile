FROM python:3.11 
WORKDIR /code
COPY . .

CMD [ "python", "./server.py" ]