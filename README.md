# Hidewall

## About

Hidewall is what powers `hidewall.io`, a web service to bypass most paywalls. You can run this locally via Docker, or use the public version at `https://hidewall.io`

## How to use

Hide wall has a *very basic* web UI where you may enter your requested URL that is blocked by a paywall. You can also pass the URL you want to `https://hidewall.io/search?query=`.

A Shortcut is offered for iOS [here](https://www.icloud.com/shortcuts/3d97b3293a944f8fa83ba987a8bd5a92).


## How to Build


### Clone this repo:

```
git clone https://git.starnix.net/sasha/hidewall.git
```

## Build the Docker image
Install [Docker](https://docs.docker.com/get-docker/). After Docker is installed, build the container image.


```
cd hidewall
docker build -t hidewall .
```

### Launch hidewall via `docker compose`

Start the docker container via `docker compose`:

```
docker compose up -d
```

The app will be accessable on port `8069` of the Docker host. Included in the Docker Compse file, is a Traefik label. The setup and configuration of Traefik is outside the scope of this README

## Support
Feel free to open a bug here, or email me at `sasha@starnix.net`

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
Please fork me!

## License
MIT License

## Project status
Active
