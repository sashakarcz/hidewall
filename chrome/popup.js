document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('yeetButton').addEventListener('click', function () {
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      const currentURL = tabs[0].url;
      const modifiedURL = 'https://hidewall.io/yeet?y=' + encodeURIComponent(currentURL);
      chrome.tabs.create({ url: modifiedURL });
    });
  });
});
