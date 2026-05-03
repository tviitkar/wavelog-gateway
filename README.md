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
- Wavelog instance

### Security

Always use HTTPS when communicating with public or internet-facing servers. Since the `WAVELOG_API_KEY` is transmitted in the body of the JSON payload, using `http://` sends your credentials in plain text. This makes your API key vulnerable to interception by anyone monitoring traffic between your gateway and the Wavelog server.

If you are hosting your Wavelog instance on a local, trusted LAN, `http://` may be acceptable if you are confident in your network security. However, please be aware that even on a local network, any device capable of intercepting traffic (e.g., via a compromised router or a malicious actor on the network) could capture the unencrypted API key. For the highest level of security in all environments, HTTPS is strongly recommended.

### Environment variables

| Variable            | Description                                                   |
|---------------------|---------------------------------------------------------------|
| `RIGCTL_ADDRESS`    | Hostname/IP of rigctld server                                 |
| `RIGCTL_PORT`       | Port of rigctld server                                        |
| `WAVELOG_API_KEY`   | API key from Wavelog                                          |
| `WAVELOG_STATION_ID`| Station ID from Wavelog                                       |
| `WAVELOG_URL`       | Base URL for Wavelog (e.g., `https://your.wavelog.instance/`) |

## Usage

> **Note:** You can pull the latest prebuilt image from the [GitHub Container Registry](https://github.com/tviitkar/wavelog-gateway/pkgs/container/wavelog-gateway).

### Docker CLI

To run the container directly, use the following command:

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

For a more persistent and reproducible setup, add the service to your docker-compose.yml file:

```yaml
services:
  wavelog-gateway:
    image: ghcr.io/tviitkar/wavelog-gateway:latest
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

## References

- [Wavelog](https://github.com/wavelog)
- [WaveLogGate](https://github.com/wavelog/WaveLogGate)
