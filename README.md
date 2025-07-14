# Wavelog Gateway

A lightweight Python application that connects to a ham radio rig via `rigctld` and forwards radio status (frequency, mode, power) to your public or private [Wavelog](https://www.wavelog.org) instance via its API.

## Features

- Connects to ham radio rigs (e.g., Icom, Yaesu) via `rigctld`
- Periodically reads rig’s frequency, mode, and power level
- Detects changes in frequency, mode, or power and sends updates to your Wavelog instance
- Dockerized for easy deployment and runs securely as a non-root user

## Why

While there is an official project, [WaveLogGate](https://github.com/wavelog/WaveLogGate), maintained by the Wavelog team, I found it challenging to containerize. Additionally, both WaveLogGate and FLRig are GUI applications, which makes running them in Docker more complex. I wanted a lightweight, Docker-friendly, headless alternative that’s easy to deploy and maintain. This project began as a personal challenge to build a simple solution that integrates well into container-based setups.

## Setup

> **Disclaimer:** This project has been tested only on Linux. While it is _expected_ to work on other operating systems, those environments have not been tested.
> **Note:** Docker is the recommended way to run this project. Running it without Docker is possible but not covered in this README.

### Requirements

- Docker
- A rigctld server accessible over the network
- Wavelog instance and its API credentials

### Environment variables

| Variable            | Description                       |
|---------------------|-----------------------------------|
| `RIGCTL_ADDRESS`    | Hostname/IP of rigctld server     |
| `RIGCTL_PORT`       | Port of rigctld server            |
| `WAVELOG_API_KEY`   | API key from Wavelog              |
| `WAVELOG_STATION_ID`| Station ID from Wavelog           |
| `WAVELOG_URL`       | Base URL for Wavelog (e.g., `https://your.wavelog.instance/`) |

## Usage

> **Note:** Prebuilt images are available on Docker Hub: [tviitkar/wavelog-gateway](https://hub.docker.com/r/tviitkar/wavelog-gateway)

### Run with Docker

Build the Docker image:

```bash
docker build -t wavelog-gateway .
```

Run the container:

```bash
docker run --rm \
  -e RIGCTL_ADDRESS=your_rigctld_ip \
  -e RIGCTL_PORT=4532 \
  -e WAVELOG_API_KEY=your_api_key \
  -e WAVELOG_STATION_ID=your_station_id \
  -e WAVELOG_URL=https://your.wavelog.instance/ \
  wavelog-gateway
```

### Docker Compose

Example `docker-compose.yml`:

```yaml
services:
  wavelog-gateway:
    image: tviitkar/wavelog-gateway:latest
    container_name: wavelog-gateway
    network_mode: host
    environment:
      - RIGCTL_ADDRESS=127.0.0.1
      - RIGCTL_PORT=4532
      - WAVELOG_URL=https://your.wavelog.instance/
      - WAVELOG_STATION_ID=your-station-id
      - WAVELOG_API_KEY=your-wavelog-api-key
    restart: unless-stopped
```

Start the service:

```bash
docker compose up -d
```

## Container behaviour

If the connection to `rigctld` is lost, the application will log a warning and exit. When run with a Docker restart policy such as `restart: unless-stopped`, the container will automatically restart, attempting to re-establish the connection. This design enables the container to self-heal from temporary connection failures, improving reliability and minimizing downtime without manual intervention.

## Notes

- I have also created a Docker image for `rigctld`. For details, visit [https://github.com/tviitkar/rigctld](https://github.com/tviitkar/rigctld).

- Because the connection between this Python application and `rigctld` uses Telnet, which is not secure, it’s strongly recommended to run both `rigctld` and `wavelog-gateway` on the same host or within a trusted private network.

- The `.devcontainer` directory is for personal development use only at this time; the Docker image used is in a private repository. This may change and be made public in the future. For now, it’s safe to ignore.

## References

- [Wavelog](https://github.com/wavelog)
- [WaveLogGate](https://github.com/wavelog/WaveLogGate)
- [rigctld documentation](https://hamlib.sourceforge.net/html/rigctld.1.html)
