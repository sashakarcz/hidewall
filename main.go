package main

import (
	"bufio"
	"bytes"
	"compress/gzip"
	"context"
	"fmt"
	"html"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/andybalholm/brotli"
	"github.com/gorilla/mux"
	"golang.org/x/time/rate"
)

// Configuration constants
const (
	DefaultPort = 80
	DefaultHost = "0.0.0.0"

	// Template and static file names
	TemplateIndex           = "templates/index.html"
	JavaScriptServiceWorker = "service-worker.js"

	// URL paths for routes
	StaticURLPath   = "/static/"
	AppRouteRoot    = "/"
	AppRouteJS      = "/" + JavaScriptServiceWorker
	AppRouteBypass  = "/yeet"

	// User-Agent strings
	UserAgentGooglebot  = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
	UserAgentGeneric    = "Mozilla/5.0 (PlayStation; PlayStation 5/6.50) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
	UserAgentTwitterbot = "Twitterbot/1.0"

	// Request timeout
	RequestTimeout = 10 * time.Second

	// Response size limit (10MB)
	MaxResponseSize = 10 * 1024 * 1024

	// Rate limiting
	RateLimitRequests = 10
	RateLimitWindow   = 1 * time.Minute
)

// Global variables
var (
	blockedSites []string
	port         int
	host         string
)

// HidewallApp represents the main application structure
type HidewallApp struct {
	router      *mux.Router
	rateLimiter *rateLimiter
}

// rateLimiter implements per-IP rate limiting
type rateLimiter struct {
	visitors map[string]*rate.Limiter
	mu       sync.RWMutex
}

// newRateLimiter creates a new rate limiter
func newRateLimiter() *rateLimiter {
	return &rateLimiter{
		visitors: make(map[string]*rate.Limiter),
	}
}

// getLimiter returns the rate limiter for a given IP
func (rl *rateLimiter) getLimiter(ip string) *rate.Limiter {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	limiter, exists := rl.visitors[ip]
	if !exists {
		limiter = rate.NewLimiter(rate.Every(RateLimitWindow/RateLimitRequests), RateLimitRequests)
		rl.visitors[ip] = limiter
	}

	return limiter
}

// cleanup removes old entries periodically
func (rl *rateLimiter) cleanup() {
	ticker := time.NewTicker(5 * time.Minute)
	go func() {
		for range ticker.C {
			rl.mu.Lock()
			rl.visitors = make(map[string]*rate.Limiter)
			rl.mu.Unlock()
		}
	}()
}

// NewHidewallApp creates a new instance of the application
func NewHidewallApp() *HidewallApp {
	rl := newRateLimiter()
	rl.cleanup()

	app := &HidewallApp{
		router:      mux.NewRouter(),
		rateLimiter: rl,
	}
	app.setupRoutes()
	return app
}

// setupRoutes configures all the HTTP routes
func (app *HidewallApp) setupRoutes() {
	// Apply security middleware to all routes
	app.router.Use(app.securityHeadersMiddleware)
	app.router.Use(app.rateLimitMiddleware)

	app.router.HandleFunc(AppRouteRoot, app.indexHandler).Methods("GET")
	app.router.HandleFunc(AppRouteJS, app.serviceWorkerHandler).Methods("GET")
	app.router.HandleFunc(AppRouteBypass, app.bypassPaywallHandler).Methods("GET")

	// Serve static files from the static directory
	staticFileServer := http.FileServer(http.Dir("./static/"))
	app.router.PathPrefix(StaticURLPath).Handler(http.StripPrefix(StaticURLPath, staticFileServer))

	// Also serve manifest.json and favicon.ico from static directory
	app.router.HandleFunc("/manifest.json", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "static/manifest.json")
	}).Methods("GET")
	app.router.HandleFunc("/favicon.ico", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "static/favicon.ico")
	}).Methods("GET")
}

// securityHeadersMiddleware adds security headers to all responses
func (app *HidewallApp) securityHeadersMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("X-XSS-Protection", "1; mode=block")
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
		w.Header().Set("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
		next.ServeHTTP(w, r)
	})
}

// rateLimitMiddleware implements rate limiting per IP
func (app *HidewallApp) rateLimitMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ip := getClientIP(r)
		limiter := app.rateLimiter.getLimiter(ip)

		if !limiter.Allow() {
			http.Error(w, "Rate limit exceeded. Please try again later.", http.StatusTooManyRequests)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// getClientIP extracts the real client IP from the request
func getClientIP(r *http.Request) string {
	// Check X-Forwarded-For header first (for proxied requests)
	xff := r.Header.Get("X-Forwarded-For")
	if xff != "" {
		ips := strings.Split(xff, ",")
		if len(ips) > 0 {
			return strings.TrimSpace(ips[0])
		}
	}

	// Check X-Real-IP header
	xri := r.Header.Get("X-Real-IP")
	if xri != "" {
		return xri
	}

	// Fallback to RemoteAddr
	ip, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return ip
}

// ServeHTTP implements the http.Handler interface
func (app *HidewallApp) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	app.router.ServeHTTP(w, r)
}

// indexHandler renders the main index page
func (app *HidewallApp) indexHandler(w http.ResponseWriter, r *http.Request) {
	// Try to serve the template file, fallback to simple HTML if it doesn't exist
	if _, err := os.Stat(TemplateIndex); err == nil {
		http.ServeFile(w, r, TemplateIndex)
	} else {
		log.Printf("Template file not found: %s, serving fallback HTML", TemplateIndex)
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		html := `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hidewall - Paywall Bypass</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { text-align: center; }
        input[type="url"] { width: 60%; padding: 10px; margin: 10px; }
        button { padding: 10px 20px; background: #007cba; color: white; border: none; cursor: pointer; }
        button:hover { background: #005a87; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hidewall</h1>
        <p>Bypass soft paywalls on websites</p>
        <form action="/yeet" method="get">
            <input type="url" name="y" placeholder="Enter URL to bypass paywall..." required>
            <br>
            <button type="submit">Bypass Paywall</button>
        </form>
    </div>
</body>
</html>`
		w.Write([]byte(html))
	}
}

// serviceWorkerHandler serves the service worker JavaScript file
func (app *HidewallApp) serviceWorkerHandler(w http.ResponseWriter, r *http.Request) {
	// Try to serve the service worker file, fallback to simple version if it doesn't exist
	if _, err := os.Stat(JavaScriptServiceWorker); err == nil {
		w.Header().Set("Content-Type", "application/javascript")
		http.ServeFile(w, r, JavaScriptServiceWorker)
	} else {
		log.Printf("Service worker file not found: %s, serving fallback", JavaScriptServiceWorker)
		w.Header().Set("Content-Type", "application/javascript")
		js := `// Simple service worker for Hidewall
self.addEventListener('install', function(event) {
    console.log('Service Worker installing');
});

self.addEventListener('activate', function(event) {
    console.log('Service Worker activating');
});`
		w.Write([]byte(js))
	}
}

// bypassPaywallHandler handles requests to bypass paywalls
func (app *HidewallApp) bypassPaywallHandler(w http.ResponseWriter, r *http.Request) {
	queryURL := strings.TrimSpace(r.URL.Query().Get("y"))

	if queryURL == "" {
		log.Println("Bypass request received with no URL provided.")
		http.Error(w, "Error: No URL provided.", http.StatusBadRequest)
		return
	}

	if !isValidURL(queryURL) {
		log.Printf("Bypass request received with invalid URL: %s", queryURL)
		http.Error(w, "Error: Invalid URL format. Please provide a valid HTTP or HTTPS URL.", http.StatusBadRequest)
		return
	}

	// Remove query parameters from the URL before checking against blocked sites
	cleanURL := removeQueryAndFragment(queryURL)

	// Default to Twitterbot for most sites (works for simple paywall bypass)
	// Use Generic user agent only for problematic sites that don't work with Twitterbot
	userAgent := UserAgentTwitterbot
	if isBlockedSite(cleanURL) {
		userAgent = UserAgentGeneric
		log.Printf("Using Generic user agent for problematic site: %s", cleanURL)
	} else {
		log.Printf("Using Twitterbot user agent for: %s", cleanURL)
	}

	content, err := fetchAndProcessURL(cleanURL, userAgent)
	if err != nil {
		handleFetchError(w, err, cleanURL)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write([]byte(content))
}

// isValidURL validates if a given string is a well-formed HTTP or HTTPS URL
// and protects against SSRF attacks
func isValidURL(urlStr string) bool {
	// Parse the URL
	parsedURL, err := url.Parse(urlStr)
	if err != nil {
		return false
	}

	// Only allow http and https schemes
	if parsedURL.Scheme != "http" && parsedURL.Scheme != "https" {
		return false
	}

	// Ensure hostname is present
	hostname := parsedURL.Hostname()
	if hostname == "" {
		return false
	}

	// Prevent SSRF attacks - block private IP ranges and localhost
	if isPrivateOrLocalhost(hostname) {
		log.Printf("Blocked attempt to access private/localhost URL: %s", urlStr)
		return false
	}

	// Validate URL structure with simpler regex to prevent ReDoS
	if len(urlStr) > 2048 {
		return false
	}

	// Basic validation that it looks like a URL
	if !strings.HasPrefix(urlStr, "http://") && !strings.HasPrefix(urlStr, "https://") {
		return false
	}

	return true
}

// isPrivateOrLocalhost checks if a hostname resolves to a private or localhost IP
func isPrivateOrLocalhost(hostname string) bool {
	// Check for localhost patterns
	if hostname == "localhost" || hostname == "0.0.0.0" || strings.HasSuffix(hostname, ".local") {
		return true
	}

	// Resolve the hostname to IP addresses
	ips, err := net.LookupIP(hostname)
	if err != nil {
		// If we can't resolve it, be conservative and block it
		return true
	}

	// Check each resolved IP
	for _, ip := range ips {
		if isPrivateIP(ip) {
			return true
		}
	}

	return false
}

// isPrivateIP checks if an IP address is private, loopback, or link-local
func isPrivateIP(ip net.IP) bool {
	// Check for loopback
	if ip.IsLoopback() {
		return true
	}

	// Check for link-local
	if ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() {
		return true
	}

	// Check for private IPv4 ranges
	privateIPBlocks := []string{
		"10.0.0.0/8",
		"172.16.0.0/12",
		"192.168.0.0/16",
		"169.254.0.0/16", // Link-local
		"127.0.0.0/8",    // Loopback
		"224.0.0.0/4",    // Multicast
		"240.0.0.0/4",    // Reserved
	}

	for _, cidr := range privateIPBlocks {
		_, block, _ := net.ParseCIDR(cidr)
		if block != nil && block.Contains(ip) {
			return true
		}
	}

	// Check for private IPv6 ranges
	if ip.To4() == nil {
		// IPv6 unique local addresses (fc00::/7)
		if len(ip) == 16 && (ip[0]&0xfe) == 0xfc {
			return true
		}
	}

	return false
}

// removeQueryAndFragment removes query parameters and fragments from URL
func removeQueryAndFragment(urlStr string) string {
	if idx := strings.Index(urlStr, "?"); idx != -1 {
		urlStr = urlStr[:idx]
	}
	if idx := strings.Index(urlStr, "#"); idx != -1 {
		urlStr = urlStr[:idx]
	}
	return urlStr
}

// isBlockedSite checks if the URL is in the blocked sites list
func isBlockedSite(urlStr string) bool {
	for _, site := range blockedSites {
		if strings.Contains(urlStr, site) {
			return true
		}
	}
	return false
}

// decompressContent decompresses gzip or brotli compressed content
func decompressContent(body []byte, encoding string) ([]byte, error) {
	switch encoding {
	case "gzip":
		reader, err := gzip.NewReader(bytes.NewReader(body))
		if err != nil {
			return body, fmt.Errorf("gzip decompression failed: %w", err)
		}
		defer reader.Close()
		return io.ReadAll(reader)
	case "br":
		reader := brotli.NewReader(bytes.NewReader(body))
		return io.ReadAll(reader)
	default:
		return body, nil
	}
}

// processHTMLContent processes the HTML content to bypass paywalls and clean up
func processHTMLContent(doc *goquery.Document, baseURL string) {
	// Parse base URL for resolving relative URLs
	parsedBaseURL, err := url.Parse(baseURL)
	if err != nil {
		log.Printf("Error parsing base URL: %v", err)
		return
	}

	// Fix image sources
	doc.Find("img").Each(func(i int, s *goquery.Selection) {
		// Handle data-gl-src attribute
		if dataSrc, exists := s.Attr("data-gl-src"); exists {
			absoluteURL := resolveURL(parsedBaseURL, dataSrc)
			s.SetAttr("src", absoluteURL)
			s.RemoveAttr("data-gl-src")
		}

		// Handle data-gl-srcset attribute
		if dataSrcset, exists := s.Attr("data-gl-srcset"); exists {
			absoluteURL := resolveURL(parsedBaseURL, dataSrcset)
			s.SetAttr("srcset", absoluteURL)
			s.RemoveAttr("data-gl-srcset")
		}

		// Handle regular src attribute
		if src, exists := s.Attr("src"); exists && !strings.HasPrefix(src, "http") {
			absoluteURL := resolveURL(parsedBaseURL, src)
			s.SetAttr("src", absoluteURL)
		}

		// Handle srcset attribute
		if srcset, exists := s.Attr("srcset"); exists && !strings.HasPrefix(srcset, "http") {
			absoluteURL := resolveURL(parsedBaseURL, srcset)
			s.SetAttr("srcset", absoluteURL)
		}
	})

	// Handle srcset for figures (e.g., for NYTimes)
	doc.Find("figure").Each(func(i int, figure *goquery.Selection) {
		var srcsetImg string
		figure.Find("source").Each(func(j int, source *goquery.Selection) {
			if srcset, exists := source.Attr("srcset"); exists {
				// Get the first URL in srcset
				srcsetCandidates := strings.Split(srcset, ",")
				if len(srcsetCandidates) > 0 {
					parts := strings.Fields(strings.TrimSpace(srcsetCandidates[0]))
					if len(parts) > 0 {
						srcsetImg = parts[0]
						return // break out of the loop
					}
				}
			}
		})

		if srcsetImg != "" {
			imgTag := figure.Find("img")
			absoluteURL := resolveURL(parsedBaseURL, srcsetImg)
			if imgTag.Length() > 0 {
				imgTag.SetAttr("src", absoluteURL)
			} else {
				// Create new img tag
				figure.AppendHtml(fmt.Sprintf(`<img src="%s">`, absoluteURL))
			}
		}
	})

	// Remove script tags
	doc.Find("script").Remove()

	// Remove aside elements
	doc.Find("aside").Remove()

	// Ensure slideshow links are absolute
	doc.Find("a[href]").Each(func(i int, s *goquery.Selection) {
		if href, exists := s.Attr("href"); exists {
			if strings.HasPrefix(href, "/picture-gallery") {
				absoluteURL := resolveURL(parsedBaseURL, href)
				s.SetAttr("href", absoluteURL)
			}
		}
	})
}

// resolveURL resolves a relative URL against a base URL
func resolveURL(baseURL *url.URL, relativeURL string) string {
	parsed, err := url.Parse(relativeURL)
	if err != nil {
		return relativeURL // Return as-is if parsing fails
	}
	return baseURL.ResolveReference(parsed).String()
}

// fetchAndProcessURL fetches content from URL and processes it
func fetchAndProcessURL(urlStr, userAgent string) (string, error) {
	// Try multiple bypass methods for problematic sites (those in blocked_sites.txt)
	if isBlockedSite(urlStr) {
		
		// Method 1: Try archive.today (search existing archives)
		log.Printf("Trying Archive.today for problematic site: %s", urlStr)
		content, err := fetchArchiveToday(urlStr)
		if err == nil {
			return content, nil
		}
		log.Printf("Archive.today failed: %v", err)

		// Method 2: Try 12ft Ladder (with better validation)
		log.Printf("Trying 12ft Ladder for problematic site: %s", urlStr)
		ladderURL := "https://12ft.io/" + urlStr
		content, err = fetchURLWithTimeout(ladderURL, UserAgentGeneric, 15*time.Second)
		if err == nil {
			return content, nil
		}
		log.Printf("12ft Ladder failed: %v", err)

		// Method 3: Try Wayback Machine
		log.Printf("Trying Wayback Machine for problematic site: %s", urlStr)
		content, err = fetchWaybackMachine(urlStr)
		if err == nil {
			return content, nil
		}
		log.Printf("Wayback Machine failed: %v", err)

		// Method 4: Google referrer with search engine bot
		log.Printf("Trying Google referrer method for problematic site: %s", urlStr)
		content, err = fetchURLWithReferrer(urlStr, UserAgentGooglebot, "https://www.google.com")
		if err == nil {
			return content, nil
		}
		log.Printf("Google referrer failed: %v", err)

		log.Printf("All bypass methods failed for: %s", urlStr)
		return "", fmt.Errorf("all bypass methods failed")
	}

	// For regular sites or fallback: use the selected user agent (usually Twitterbot)
	return fetchURL(urlStr, userAgent)
}

// fetchArchiveToday tries to get content from archive.today by searching existing archives
func fetchArchiveToday(originalURL string) (string, error) {
	// List of archive.today domains to try
	archiveDomains := []string{
		"https://archive.today/",
		"https://archive.ph/",
		"https://archive.is/",
		"https://archive.vn/",
	}

	for _, domain := range archiveDomains {
		log.Printf("Trying %s for: %s", domain, originalURL)

		// Search for existing archives by appending the URL
		searchURL := domain + originalURL

		client := createSecureHTTPClient(10 * time.Second)

		req, err := http.NewRequest("GET", searchURL, nil)
		if err != nil {
			continue
		}

		// Use a real browser user agent to avoid blocking
		req.Header.Set("User-Agent", UserAgentGeneric)
		req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
		req.Header.Set("Accept-Language", "en-US,en;q=0.5")

		resp, err := client.Do(req)
		if err != nil {
			log.Printf("Request to %s failed: %v", domain, err)
			continue
		}
		defer resp.Body.Close()

		if resp.StatusCode == 429 {
			log.Printf("Rate limited by %s", domain)
			continue
		}

		if resp.StatusCode >= 400 {
			log.Printf("HTTP error %d from %s", resp.StatusCode, domain)
			continue
		}

		// Limit response size
		body, err := io.ReadAll(io.LimitReader(resp.Body, MaxResponseSize))
		if err != nil {
			continue
		}

		// Parse HTML with goquery
		doc, err := goquery.NewDocumentFromReader(bytes.NewReader(body))
		if err != nil {
			continue
		}

		// Check if this is a valid archived page
		pageText := doc.Text()
		pageHTML := string(body)
		
		// Skip if it's an error page, search page, or archive.today's home page
		if strings.Contains(pageText, "No results found") ||
		   strings.Contains(pageText, "Enter a URL to search") ||
		   strings.Contains(pageText, "This page shows only") ||
		   strings.Contains(pageHTML, "id=\"search_form\"") ||
		   strings.Contains(pageText, "archive.today") && len(pageText) < 2000 {
			log.Printf("Got archive.today search page, not actual content from %s", domain)
			continue
		}

		// Check if we got actual article content (should be substantial)
		if len(pageText) < 1000 {
			log.Printf("Page too short from %s, likely not the actual article", domain)
			continue
		}

		log.Printf("Successfully found archived content on %s", domain)
		
		// Process the content
		processHTMLContent(doc, originalURL)
		html, err := doc.Html()
		if err != nil {
			continue
		}

		return html, nil
	}

	return "", fmt.Errorf("no existing archives found on archive.today domains")
}

// createSecureHTTPClient creates an HTTP client with security settings
func createSecureHTTPClient(timeout time.Duration) *http.Client {
	return &http.Client{
		Timeout: timeout,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			// Limit redirect chain to 10
			if len(via) >= 10 {
				return fmt.Errorf("too many redirects")
			}
			// Validate redirect target to prevent open redirects to private networks
			if isPrivateOrLocalhost(req.URL.Hostname()) {
				return fmt.Errorf("redirect to private or localhost address blocked")
			}
			return nil
		},
	}
}

// fetchURLWithTimeout fetches URL with a specific timeout
func fetchURLWithTimeout(urlStr, userAgent string, timeout time.Duration) (string, error) {
	client := createSecureHTTPClient(timeout)

	req, err := http.NewRequest("GET", urlStr, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.5")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")
	req.Header.Set("Connection", "keep-alive")

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("HTTP error %d", resp.StatusCode)
	}

	// Limit response size to prevent memory exhaustion
	body, err := io.ReadAll(io.LimitReader(resp.Body, MaxResponseSize))
	if err != nil {
		return "", fmt.Errorf("failed to read response body: %w", err)
	}

	// Decompress content if needed
	contentEncoding := resp.Header.Get("Content-Encoding")
	decompressedBody, err := decompressContent(body, contentEncoding)
	if err != nil {
		log.Printf("Decompression error: %v", err)
		decompressedBody = body
	}

	// Parse HTML with goquery
	doc, err := goquery.NewDocumentFromReader(bytes.NewReader(decompressedBody))
	if err != nil {
		return "", fmt.Errorf("failed to parse HTML: %w", err)
	}

	// Check if this is a 12ft Ladder error page or processing page
	if strings.Contains(urlStr, "12ft.io") {
		pageText := doc.Text()
		if strings.Contains(pageText, "Cleaning Webpage") || 
		   strings.Contains(pageText, "You can talk 3x faster") ||
		   strings.Contains(pageText, "12ft.io") ||
		   len(pageText) < 500 {
			return "", fmt.Errorf("12ft Ladder failed to process the page")
		}
	}

	// Check if this is an Outline.com error page
	if strings.Contains(urlStr, "outline.com") {
		pageText := doc.Text()
		if strings.Contains(pageText, "couldn't parse") ||
		   strings.Contains(pageText, "Sorry, Outline") ||
		   len(pageText) < 500 {
			return "", fmt.Errorf("Outline.com failed to process the page")
		}
	}

	// Process HTML content
	processHTMLContent(doc, urlStr)

	// Return the modified HTML
	html, err := doc.Html()
	if err != nil {
		return "", fmt.Errorf("failed to generate HTML: %w", err)
	}

	return html, nil
}

// fetchWaybackMachine tries to get content from Internet Archive
func fetchWaybackMachine(originalURL string) (string, error) {
	// Try to get the latest snapshot
	waybackURL := "https://web.archive.org/web/2/" + originalURL

	client := createSecureHTTPClient(20 * time.Second) // Wayback can be slow

	req, err := http.NewRequest("GET", waybackURL, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create wayback request: %w", err)
	}

	req.Header.Set("User-Agent", UserAgentGeneric)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("wayback request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("wayback HTTP error %d", resp.StatusCode)
	}

	// Limit response size
	body, err := io.ReadAll(io.LimitReader(resp.Body, MaxResponseSize))
	if err != nil {
		return "", fmt.Errorf("failed to read wayback response: %w", err)
	}

	// Parse HTML with goquery
	doc, err := goquery.NewDocumentFromReader(bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("failed to parse wayback HTML: %w", err)
	}

	// Process the content
	processHTMLContent(doc, originalURL)
	html, err := doc.Html()
	if err != nil {
		return "", fmt.Errorf("failed to generate HTML from wayback: %w", err)
	}

	return html, nil
}

// fetchURLWithReferrer fetches URL with a specific referrer header
func fetchURLWithReferrer(urlStr, userAgent, referrer string) (string, error) {
	client := createSecureHTTPClient(RequestTimeout)

	req, err := http.NewRequest("GET", urlStr, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers including referrer
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.5")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")
	req.Header.Set("Connection", "keep-alive")
	req.Header.Set("Upgrade-Insecure-Requests", "1")
	req.Header.Set("Cache-Control", "max-age=0")
	req.Header.Set("Referer", referrer)
	
	// Don't send cookies for paywall bypass (as suggested in GitHub repo)
	// req.Header.Set("Cookie", "") // This is default behavior anyway

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("HTTP error %d", resp.StatusCode)
	}

	// Limit response size
	body, err := io.ReadAll(io.LimitReader(resp.Body, MaxResponseSize))
	if err != nil {
		return "", fmt.Errorf("failed to read response body: %w", err)
	}

	// Decompress content if needed
	contentEncoding := resp.Header.Get("Content-Encoding")
	decompressedBody, err := decompressContent(body, contentEncoding)
	if err != nil {
		log.Printf("Decompression error: %v", err)
		decompressedBody = body
	}

	// Parse HTML with goquery
	doc, err := goquery.NewDocumentFromReader(bytes.NewReader(decompressedBody))
	if err != nil {
		return "", fmt.Errorf("failed to parse HTML: %w", err)
	}

	// Process HTML content
	processHTMLContent(doc, urlStr)

	// Return the modified HTML
	html, err := doc.Html()
	if err != nil {
		return "", fmt.Errorf("failed to generate HTML: %w", err)
	}

	return html, nil
}

// fetchURL is the core HTTP fetching function
func fetchURL(urlStr, userAgent string) (string, error) {
	client := createSecureHTTPClient(RequestTimeout)

	req, err := http.NewRequest("GET", urlStr, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.5")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")
	req.Header.Set("Connection", "keep-alive")
	req.Header.Set("Upgrade-Insecure-Requests", "1")
	req.Header.Set("Cache-Control", "max-age=0")
	
	// Add referrer for Facebook redirects
	if strings.Contains(urlStr, "facebook.com/l.php") {
		req.Header.Set("Referer", "https://facebook.com/")
	}

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("HTTP error %d", resp.StatusCode)
	}

	// Limit response size
	body, err := io.ReadAll(io.LimitReader(resp.Body, MaxResponseSize))
	if err != nil {
		return "", fmt.Errorf("failed to read response body: %w", err)
	}

	// Decompress content if needed
	contentEncoding := resp.Header.Get("Content-Encoding")
	decompressedBody, err := decompressContent(body, contentEncoding)
	if err != nil {
		log.Printf("Decompression error: %v", err)
		decompressedBody = body
	}

	// Parse HTML with goquery
	doc, err := goquery.NewDocumentFromReader(bytes.NewReader(decompressedBody))
	if err != nil {
		return "", fmt.Errorf("failed to parse HTML: %w", err)
	}

	// Process HTML content
	processHTMLContent(doc, urlStr)

	// Return the modified HTML
	html, err := doc.Html()
	if err != nil {
		return "", fmt.Errorf("failed to generate HTML: %w", err)
	}

	return html, nil
}

// handleFetchError handles errors from fetchAndProcessURL
func handleFetchError(w http.ResponseWriter, err error, urlStr string) {
	errStr := err.Error()
	log.Printf("Error fetching '%s': %v", urlStr, err)

	// Create a nicely formatted error page that matches the site's design
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	
	var statusCode int
	var errorTitle string
	var errorMessage string
	
	if strings.Contains(errStr, "all bypass methods failed") {
		statusCode = http.StatusServiceUnavailable
		errorTitle = "Paywall Bypass Failed"
		errorMessage = fmt.Sprintf(`
			<p>Unfortunately, we couldn't bypass the paywall for this site right now.</p>
			<div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #00ade6;">
				<strong style="color: #00ade6;">URL:</strong> <span style="font-family: monospace; word-break: break-all;">%s</span>
			</div>
			<p>We tried multiple methods including archive services, but none were successful. This could be because:</p>
			<ul style="text-align: left; padding-left: 20px; margin: 20px 0;">
				<li>The site has a very strong paywall</li>
				<li>The article is too new to be archived</li>
				<li>Archive services are currently rate-limiting us</li>
				<li>The site has updated their paywall detection</li>
			</ul>
			<p>You might try:</p>
			<ul style="text-align: left; padding-left: 20px; margin: 20px 0;">
				<li>Waiting a few minutes and trying again</li>
				<li>Checking if the article is available on <a href="https://archive.today" target="_blank" style="color: #00ade6;">archive.today</a> manually</li>
				<li>Looking for the article on <a href="https://web.archive.org" target="_blank" style="color: #00ade6;">Wayback Machine</a></li>
				<li>Using your browser's reading mode if available</li>
			</ul>
		`, html.EscapeString(urlStr))
	} else if strings.Contains(errStr, "HTTP error") {
		statusCode = http.StatusBadGateway
		errorTitle = "Site Access Error"
		errorMessage = fmt.Sprintf(`
			<p>We couldn't access the website you requested.</p>
			<div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #00ade6;">
				<strong style="color: #00ade6;">URL:</strong> <span style="font-family: monospace; word-break: break-all;">%s</span>
			</div>
			<p>The site returned an error when we tried to fetch it. Please check that the URL is correct and the site is accessible.</p>
		`, html.EscapeString(urlStr))
	} else if strings.Contains(errStr, "timeout") {
		statusCode = http.StatusGatewayTimeout
		errorTitle = "Request Timeout"
		errorMessage = fmt.Sprintf(`
			<p>The request to fetch the content took too long.</p>
			<div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #00ade6;">
				<strong style="color: #00ade6;">URL:</strong> <span style="font-family: monospace; word-break: break-all;">%s</span>
			</div>
			<p>This might be a temporary issue. Please try again in a few moments.</p>
		`, html.EscapeString(urlStr))
	} else {
		statusCode = http.StatusInternalServerError
		errorTitle = "Unexpected Error"
		errorMessage = fmt.Sprintf(`
			<p>An unexpected error occurred while processing your request.</p>
			<div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #00ade6;">
				<strong style="color: #00ade6;">URL:</strong> <span style="font-family: monospace; word-break: break-all;">%s</span>
			</div>
			<p>Please try again, or contact support if the problem persists.</p>
		`, html.EscapeString(urlStr))
	}

	html := fmt.Sprintf(`<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>%s - Hidewalls</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/static/fonts/material-design-iconic-font/css/material-design-iconic-font.min.css">
    <link rel="stylesheet" href="/static/css/style.css">
    <meta name="robots" content="noindex, follow">
    <style>
        .error-content {
            margin-top: 30px;
        }
        .error-content ul li {
            margin-bottom: 8px;
        }
        .error-content a {
            color: #00ade6;
            text-decoration: none;
        }
        .error-content a:hover {
            text-decoration: underline;
        }
        .back-form {
            margin-top: 40px;
        }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="inner">
            <h3>%s</h3>
            <div class="error-content">
                %s
            </div>
            <form method="GET" action="/" class="back-form">
                <button type="submit">← Try Another URL</button>
            </form>
        </div>
    </div>
</body>
</html>`, errorTitle, errorTitle, errorMessage)

	w.WriteHeader(statusCode)
	w.Write([]byte(html))
}

// loadBlockedSites loads the list of blocked sites from file
func loadBlockedSites() {
	file, err := os.Open("blocked_sites.txt")
	if err != nil {
		log.Printf("Warning: blocked_sites.txt not found. No sites will be specifically treated as blocked.")
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" {
			blockedSites = append(blockedSites, line)
		}
	}

	if err := scanner.Err(); err != nil {
		log.Printf("Error reading blocked_sites.txt: %v", err)
	}
}

// initConfig initializes configuration from environment variables
func initConfig() {
	var err error
	
	// Get port from environment variable or use default
	portStr := os.Getenv("PORT")
	if portStr != "" {
		port, err = strconv.Atoi(portStr)
		if err != nil {
			log.Printf("Invalid PORT value: %s, using default %d", portStr, DefaultPort)
			port = DefaultPort
		}
	} else {
		port = DefaultPort
	}

	// Get host from environment variable or use default
	host = os.Getenv("HOST")
	if host == "" {
		host = DefaultHost
	}
}

func main() {
	// Initialize configuration
	initConfig()

	// Load blocked sites
	loadBlockedSites()

	// Create and configure the application
	app := NewHidewallApp()

	// Create server
	server := &http.Server{
		Addr:         fmt.Sprintf("%s:%d", host, port),
		Handler:      app,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Channel to listen for interrupt signals
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	// Start server in a goroutine
	go func() {
		log.Printf("Starting Hidewall server on %s:%d", host, port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	<-stop
	log.Println("Shutting down server gracefully...")

	// Create a deadline for shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Attempt graceful shutdown
	if err := server.Shutdown(ctx); err != nil {
		log.Printf("Server shutdown error: %v", err)
	}

	log.Println("Server stopped")
}
