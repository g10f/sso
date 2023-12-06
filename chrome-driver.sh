#!/bin/bash
platform=linux64

url=$(curl https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | \
 jq -r ".channels.Stable.downloads.chromedriver[] | select(.platform == \"${platform}\") | .url")
#echo $url
curl "$url" -O
unzip chromedriver-"$platform".zip
sudo mv chromedriver-"$platform"/chromedriver /usr/bin/chromedriver
rm -r chromedriver-"$platform"
rm chromedriver-"$platform".zip
