FROM python:3.9-slim-bullseye

WORKDIR /app

COPY . .

RUN pip3 install .

CMD [ "python3", "run.py" ]