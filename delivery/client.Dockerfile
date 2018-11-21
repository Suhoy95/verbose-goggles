# Consider this docker-file only with ../docker-compose.yml configuration
FROM python:3.7

WORKDIR /app
COPY requirements.txt /app
RUN pip3 install -r requirements.txt
RUN mkdir storage
RUN mkdir /app/tmp

COPY src /app/src
COPY certs /app/certs
COPY vg_client.py /app

CMD python vg_client.py \
    --local tmp \
    --loglevel DEBUG \
    --ns_hostname nameserver \
    --ns_port 8000 \
    --ca_cert certs/rootCA.crt \
    --keyfile certs/client/client.key \
    --certfile certs/client/client.crt