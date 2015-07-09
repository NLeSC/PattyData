FROM ubuntu:14.04
VOLUME ["/data"]
RUN apt-get update && apt-get install -y qtcreator wget subversion
WORKDIR /opt
RUN svn checkout svn://svn.code.sf.net/p/vcg/code/trunk/vcglib vcglib
RUN wget http://vcg.isti.cnr.it/nexus/download/Nexus_3.0.tar.gz && tar -zxf Nexus_3.0.tar.gz
WORKDIR /opt/Nexus_3.0/nxsbuild
RUN perl -pi -e 's@../../../../vcg@../../vcg@g' nxsbuild.pro
RUN qmake -recursive nxsbuild.pro && make -j
RUN cp ../bin/* /usr/bin
WORKDIR /data
CMD nxsbuild
