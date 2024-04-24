# Hidewall

[![Publish Docker image](https://github.com/sashakarcz/hidewall/actions/workflows/docker-image.yml/badge.svg)](https://github.com/sashakarcz/hidewall/actions/workflows/docker-image.yml)

## About

Hidewall is what powers `hidewall.io`, a web service to bypass most paywalls. Hidewall is a Python Flask app that uses Requests, BeautifulSoup, and web caches to access content that is blocked behind a soft paywall. I have built in support for NordVPN for when grabbing content from a WebCache. Set `USEVPN=true` in the Docker Compose file, and then add your credentials to use NordVPN.

You can run this locally via Docker, or use the public version at [`https://hidewall.io`](https://hidewall.io)

## How to use

Hide wall has a simple web UI where you may enter your requested URL that is blocked by a paywall. You can also pass the URL you want to `https://hidewall.io/yeet?y=`.

### Android
This can be installed as a Progressive Web App (PWA). If you visit [`https://hidewall.io`](https://hidewall.io), you will be prompted to "Add Hidewalls to Home screen". This will download a PWA version that you can use to share blocked content to.

### iOS
A Shortcut is offered for iOS [here](https://www.icloud.com/shortcuts/3d97b3293a944f8fa83ba987a8bd5a92).

### Chrome Extension
Now in the [Chrome Store](https://chromewebstore.google.com/detail/hidewalls/klkgmappdodkpjhkmlnanbhdmefpnehk)!

## How to Build


### Clone this repo:

```
git clone https://github.com/sashakarcz/hidewall.git
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
Feel free to open a bug here, or email me at [`sasha@starnix.net`](mailto:sasha@starnix.net?subject=[GitHub]%20Hidewall)

## Contributing
Please fork me!

## License
MIT License

## Project status
Active
