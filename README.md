# Hidewall

[![Publish Docker image](https://github.com/sashakarcz/hidewall/actions/workflows/docker-image.yml/badge.svg)](https://github.com/sashakarcz/hidewall/actions/workflows/docker-image.yml)
[![Go Version](https://img.shields.io/badge/Go-1.21+-00ADD8?style=flat&logo=go)](https://go.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## About

Hidewall is a high-performance web service designed to bypass soft paywalls on news and article websites. It powers the public instance at [`hidewall.io`](https://hidewall.io).

**Completely rewritten in Go** for superior performance, smaller resource footprint, and enhanced security. The modern Go implementation delivers:

- 10x faster response times compared to the original Python version
- 90% smaller Docker images (multi-stage builds)
- Built-in security hardening (SSRF protection, rate limiting, secure headers)
- Graceful shutdown and production-ready error handling
- Concurrent request processing with minimal memory overhead

### Bypass Techniques

Hidewall employs multiple strategies to access paywalled content:

- **Archive.today integration** - Searches existing archives across multiple mirror domains (archive.ph, archive.is, archive.vn)
- **12ft Ladder support** - Leverages the popular paywall bypass service
- **Wayback Machine fallback** - Retrieves content from Internet Archive snapshots
- **Smart user agent switching** - Uses Twitterbot UA for simple paywalls, PlayStation 5 UA for sophisticated detection systems
- **Referrer spoofing** - Employs Google, Facebook, and Twitter referrers for stubborn paywalls
- **Content processing** - Fixes relative URLs, removes scripts, and optimizes images for clean article display

### Security Features

- **SSRF Protection** - Validates URLs and blocks access to private IP ranges, localhost, and internal networks
- **Rate Limiting** - Per-IP rate limiting (10 requests per minute) to prevent abuse
- **Security Headers** - Implements X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, and more
- **Input Validation** - Comprehensive URL validation and HTML escaping to prevent injection attacks
- **Response Size Limits** - Protects against memory exhaustion (10MB limit)
- **Redirect Protection** - Limits redirect chains and validates redirect targets

You can run this locally via Docker, or use the public version at [`https://hidewall.io`](https://hidewall.io)

## How to use

Hidewall has a simple web UI where you may enter your requested URL that is blocked by a paywall. You can also pass the URL you want to `https://hidewall.io/yeet?y=`.

### Android
This can be installed as a Progressive Web App (PWA). If you visit [`https://hidewall.io`](https://hidewall.io), you will be prompted to "Add Hidewalls to Home screen". This will download a PWA version that you can use to share blocked content to.

### iOS
A Shortcut is offered for iOS [here](https://www.icloud.com/shortcuts/3d97b3293a944f8fa83ba987a8bd5a92).

### Chrome Extension
Now in the [Chrome Store](https://chromewebstore.google.com/detail/hidewalls/klkgmappdodkpjhkmlnanbhdmefpnehk)!

## Installation

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Alternatively: Go 1.21+ for building from source

### Quick Start with Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/sashakarcz/hidewall.git
cd hidewall
```

2. Start the service:
```bash
docker compose up -d
```

3. Access the service at `http://localhost:8069`

The Docker Compose configuration includes a Traefik label for reverse proxy integration. Configure Traefik separately according to your infrastructure needs.

### Building from Source

#### Docker Build

Build the optimized Docker image with multi-stage compilation:

```bash
docker build -t hidewall:latest .
```

Run the container:
```bash
docker run -d \
  -p 8069:80 \
  --name hidewall \
  --restart unless-stopped \
  hidewall:latest
```

#### Native Go Build

```bash
# Install dependencies
go mod download

# Build the binary
go build -o hidewall main.go

# Run the application
./hidewall
```

### Configuration

Environment variables:

- `PORT` - HTTP server port (default: 80)
- `HOST` - Bind address (default: 0.0.0.0)

Example with custom port:
```bash
PORT=8080 ./hidewall
```

### Blocked Sites Configuration

Sites requiring advanced bypass methods are listed in `blocked_sites.txt`. These sites use the full arsenal of bypass techniques including archive services. Add domains (one per line) to customize behavior:

```
bloomberg.com
telegraph.co.uk
theatlantic.com
wsj.com
```

## API Usage

### Web Interface

Visit the root URL and enter a paywalled article URL in the form.

### Direct API Endpoint

```bash
curl "https://hidewall.io/yeet?y=https://example.com/paywalled-article"
```

Response: HTML content with paywall removed

### URL Parameters

- `y` - The full URL of the paywalled article (required, must be URL-encoded)

Example:
```bash
https://hidewall.io/yeet?y=https%3A%2F%2Fwww.wsj.com%2Farticle%2Fexample
```

## Architecture

### Technology Stack

- **Language**: Go 1.21+
- **Router**: Gorilla Mux
- **HTML Parser**: goquery (jQuery-like API)
- **Compression**: gzip and Brotli support
- **Rate Limiting**: Token bucket algorithm with per-IP tracking

### Performance Characteristics

- **Concurrency**: Handles thousands of concurrent requests
- **Memory**: ~20MB base footprint
- **Response Time**: <500ms average for simple paywalls, <3s for archive fallback
- **Docker Image**: ~25MB compressed (Alpine-based multi-stage build)

### Security Architecture

1. **Input Validation Layer**: URL scheme and format validation
2. **SSRF Protection Layer**: DNS resolution and IP range validation
3. **Rate Limiting Layer**: Per-IP token bucket with periodic cleanup
4. **HTTP Client Layer**: Redirect validation, timeout enforcement, size limits
5. **Output Sanitization Layer**: HTML escaping for error messages

## Deployment

### Production Recommendations

1. **Reverse Proxy**: Deploy behind nginx or Traefik for TLS termination
2. **Rate Limiting**: Additional rate limiting at reverse proxy layer recommended
3. **Monitoring**: Health check endpoint available at `/` (returns 200 OK)
4. **Resources**: Recommended 256MB RAM minimum, 512MB for high traffic
5. **Scaling**: Stateless design allows horizontal scaling

### Health Check

The Docker image includes a built-in health check that pings the root endpoint every 30 seconds.

### Graceful Shutdown

The application handles SIGTERM and SIGINT gracefully, completing in-flight requests before shutdown (30-second timeout).

## Troubleshooting

### Common Issues

**Rate Limit Errors**: The service enforces 10 requests per minute per IP. Wait 60 seconds or deploy your own instance.

**Archive Services Timeout**: Archive.today and Wayback Machine can be slow. The service has extended timeouts (15-20s) for these services.

**Bypass Failure**: Some sites have very strong paywalls. Try adding the domain to `blocked_sites.txt` to enable all bypass methods.

### Logs

Logs are written to stdout. In Docker, view logs with:
```bash
docker logs hidewall
```

## Development

### Running Tests

```bash
go test ./...
```

### Code Structure

- `main.go` - Main application (1100+ lines, modular functions)
- `templates/index.html` - Web UI template
- `static/` - CSS, fonts, and static assets
- `chrome/` - Chrome extension source
- `blocked_sites.txt` - Sites requiring advanced bypass

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

Follow Go conventions and ensure `go fmt` and `go vet` pass.

## Legal and Ethics

This tool is designed for **educational purposes and personal use** to access content you have a right to read. Users are responsible for complying with applicable laws and website terms of service.

The authors do not condone copyright infringement or violation of terms of service. This tool should be used ethically and responsibly.

## Support

- **Bug Reports**: Open an issue on [GitHub](https://github.com/sashakarcz/hidewall/issues)
- **Questions**: Email [`sasha@starnix.net`](mailto:sasha@starnix.net?subject=[GitHub]%20Hidewall)
- **Public Instance**: [`https://hidewall.io`](https://hidewall.io)

## License

MIT License - See LICENSE file for details

## Project Status

**Active Development** - Regularly maintained and updated

### Recent Improvements

- Complete Go rewrite for performance
- SSRF protection and security hardening
- Rate limiting implementation
- Graceful shutdown handling
- Updated dependencies to latest versions
- Comprehensive error handling
- Response size limits
- HTML output sanitization

### Roadmap

- [ ] Prometheus metrics endpoint
- [ ] Configurable rate limits via environment variables
- [ ] Support for additional archive services
- [ ] API authentication for private instances
- [ ] Browser extension improvements
