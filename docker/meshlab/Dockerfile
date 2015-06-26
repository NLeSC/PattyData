# This is a comment
FROM ubuntu:14.04
MAINTAINER Oscar Martinez Rubi <o.rubi@esciencecenter.nl>
RUN apt-get update -y
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:zarquon42/meshlab
RUN apt-get install -y meshlab
RUN apt-get install -y -q xvfb
ENV DISPLAY :99

# Install Xvfb init script
ADD xvfb_init /etc/init.d/xvfb
RUN chmod a+x /etc/init.d/xvfb
ADD xvfb-daemon-run /usr/bin/xvfb-daemon-run
RUN chmod a+x /usr/bin/xvfb-daemon-run
ADD mymeshlabserver /usr/bin/mymeshlabserver
RUN chmod a+x /usr/bin/mymeshlabserver

VOLUME ["/data"]
CMD mymeshlabserver
