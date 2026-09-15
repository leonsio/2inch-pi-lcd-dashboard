# Docker module

The `docker` module reads Docker Engine status directly through a local Unix socket. It does not require the Docker Python package.

## Enable the module

```yaml
docker:
  socket: /var/run/docker.sock
  containers: {}
```

## Parameters

| Parameter | Type | Default/example | Purpose |
| --- | --- | --- | --- |
| `socket` | absolute path string | `/var/run/docker.sock` | Docker Engine Unix socket. |
| `containers` | mapping | `{}` | Optional named container cards. |

The shared `REQUEST_TIMEOUT` value controls Docker socket/API request timeout.

## Container parameters

Each key under `containers` becomes `docker.<alias>`. Aliases use lowercase letters, digits and underscores.

### Short form

```yaml
docker:
  socket: /var/run/docker.sock
  containers:
    mqtt: mosquitto
```

The value is the Docker container name to look up. The title is derived from the alias (`MQTT`).

### Long form

```yaml
docker:
  socket: /var/run/docker.sock
  containers:
    homeassistant:
      name: homeassistant
      title: Home Assistant
```

| Parameter | Required | Example | Purpose |
| --- | --- | --- | --- |
| `name` | yes | `homeassistant` | Docker container name. |
| `title` | no | `Home Assistant` | Custom dashboard title. |

## Available cards

| Card | Display |
| --- | --- |
| `docker` | Number of running containers versus total containers |
| `docker_ring` | Running/total ratio as a ring |
| `docker.<alias>` | State of a configured container |

Container cards can show states such as `RUNNING`, `EXITED`, `PAUSED`, `RESTARTING` or `CREATED`. A configured container that is absent from Docker is shown as `NOT FOUND`.

## Polling

- **medium**: daemon reachability and `/containers/json?all=1`
- **slow**: Docker Engine version metadata

With default scheduler settings these run every 60 and 600 seconds.

## Complete example

```yaml
docker:
  socket: /var/run/docker.sock
  containers:
    homeassistant:
      name: homeassistant
      title: Home Assistant
    mqtt: mosquitto
    nginx:
      name: nginx
      title: Reverse Proxy

PAGES:
  - name: docker
    layout:
      row1cell1: docker
      row1cell2: docker_ring
      row1cell3: docker.homeassistant
      row2cell1: docker.mqtt
      row2cell2: docker.nginx
```

## Permissions

The dashboard process must have permission to open the configured Unix socket. For the standard `/var/run/docker.sock`, this generally means running with sufficient privileges or using an account that has access to the Docker socket.

Giving a process access to the Docker socket effectively gives it significant control over Docker and often the host. Grant this permission only to the dashboard service account when appropriate.