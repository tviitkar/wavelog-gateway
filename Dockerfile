FROM --platform=$BUILDPLATFORM python:3.13.5-alpine

ENV PYTHONUNBUFFERED=1

RUN adduser -D ham

RUN pip3 install --no-cache-dir \
    aiohttp==3.12.13 \
    telnetlib3==2.0.4

WORKDIR /app
COPY --chown=ham:ham wavelog-gateway/ .

USER ham

CMD [ "python", "main.py" ]
