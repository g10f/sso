#CHROME_DRIVER_VERSION
if [ -z "$CHROME_DRIVER_VERSION" ]; then
    CHROME_MAJOR_VERSION=$(google-chrome --version | sed -E "s/.* ([0-9]+)(\.[0-9]+){3}.*/\1/")
    CHROME_DRIVER_VERSION=$(wget --no-verbose -O - "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}");
fi
echo "Using chromedriver version: ""$CHROME_DRIVER_VERSION"
wget --no-verbose -O /tmp/chromedriver_linux64.zip https://chromedriver.storage.googleapis.com/"$CHROME_DRIVER_VERSION"/chromedriver_linux64.zip
rm -rf /opt/selenium/chromedriver
unzip /tmp/chromedriver_linux64.zip -d /opt/selenium
rm /tmp/chromedriver_linux64.zip
mv /opt/selenium/chromedriver /opt/selenium/chromedriver-"$CHROME_DRIVER_VERSION"
chmod 755 /opt/selenium/chromedriver-"$CHROME_DRIVER_VERSION"
sudo ln -fs /opt/selenium/chromedriver-"$CHROME_DRIVER_VERSION" /usr/bin/chromedriver
