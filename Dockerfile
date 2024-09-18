FROM python:3.9-slim-bullseye

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

CMD [ "python3", "run.py" ]