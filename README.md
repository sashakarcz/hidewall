# Hidewall

## About

Hidewall is what powers `hidewall.io`, a web service to bypass most paywalls. You can run this locally via Docker, or use the public version at `https://hidewall.io`

## How to use

Hide wall has a *very basic* web UI where you may enter your requested URL that is blocked by a paywall. You can also pass the URL you want to `https://hidewall.io/yeet?y=`.

### iOS
A Shortcut is offered for iOS [here](https://www.icloud.com/shortcuts/3d97b3293a944f8fa83ba987a8bd5a92).

### Chrome Extension
Open the Chrome browser and go to chrome://extensions/. Enable "Developer mode" in the top right corner. Click the "Load unpacked" button and select the extension directory (the one containing manifest.json, named chrome).

Now, when you click the extension icon, the popup will appear with a "Yeet It!" button. Clicking the button will modify the current tab's URL by adding `https://hidewall.io/yeet?y=` to it and then open a new tab with the modified URL.

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
Feel free to open a bug here, or email me at `sasha@starnix.net`

## Roadmap
I want to add Chrome and Firefox extensions, and an easy way to use on Android.

## Contributing
Please fork me!

## License
MIT License

## Project status
Active
