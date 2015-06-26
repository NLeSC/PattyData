FROM ubuntu:14.04
VOLUME ["/data"]
RUN apt-get update && apt-get install -y qtcreator wget
WORKDIR /opt
RUN wget http://vcg.isti.cnr.it/nexus/download/nexus-2.0-src.tgz && tar -zxf nexus-2.0-src.tgz
WORKDIR /opt/nexus-2.0-src/nxsbuild
RUN perl -pi -e 's@../../../../vcg@../vcg@g' nxsbuild.pro
RUN qmake -recursive nxsbuild.pro && make -j
RUN cp ../bin/* /usr/bin
CMD nxsbuild
