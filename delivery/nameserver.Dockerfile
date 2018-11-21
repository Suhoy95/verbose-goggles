# Consider this docker-file only with ../docker-compose.yml configuration
FROM python:3.7

WORKDIR /app
COPY requirements.txt /app
RUN pip3 install -r requirements.txt

COPY src /app/src
COPY certs /app/certs
COPY vg_nameserver.py /app

EXPOSE 8000

CMD python vg_nameserver.py \
    --hostname nameserver \
    --port 8000 \
    --treejson tree.json \
    --ca_cert certs/rootCA.crt \
    --keyfile certs/nameserver/nameserver.key \
    --certfile certs/nameserver/nameserver.crt
