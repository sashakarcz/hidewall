self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Modify this URL as needed
  const targetURL = 'https://hidewall.io/yeet?y=';

  // Check if the request matches a specific condition
  if (request.url.includes('url=')) {
    const urlSearchParams = new URLSearchParams(request.url.split('?')[1]);
    const linkParam = urlSearchParams.get('url');
    
    if (linkParam) {
      const redirectURL = targetURL + encodeURIComponent(linkParam);
      event.respondWith(Response.redirect(redirectURL, 302));
    }
  }
});

