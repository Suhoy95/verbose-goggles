# Consider this docker-file only with ../docker-compose.yml configuration
FROM python:3.7

WORKDIR /app
COPY requirements.txt /app
RUN pip3 install -r requirements.txt
RUN mkdir storage

COPY src /app/src
COPY certs /app/certs
COPY vg_storage.py /app

EXPOSE 8001-8007

CMD python vg_storage.py \
    --ca_cert certs/rootCA.crt \
    --rootpath storage