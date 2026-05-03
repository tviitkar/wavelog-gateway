FROM python:3.13.5-alpine

ENV PYTHONUNBUFFERED=1

RUN adduser -D ham

RUN pip3 install --no-cache-dir \
    aiohttp==3.12.13 \
    pydantic==2.13.3 \
    pydantic-settings==2.14.0

WORKDIR /app
COPY --chown=ham:ham wavelog-gateway/ .

USER ham

CMD [ "python", "main.py" ]
