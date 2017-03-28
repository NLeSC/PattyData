# Convert ply to nexus mesh

# Requirements

Via appia server runs Centos 6.

## GCC 4.8.2

Qt requires g++>=4.8

```shell
rpm --import http://ftp.scientificlinux.org/linux/scientific/5x/x86_64/RPM-GPG-KEYs/RPM-GPG-KEY-cern
curl http://linuxsoft.cern.ch/cern/devtoolset/slc6-devtoolset.repo > /etc/yum.repos.d/slc6-devtoolset.repo
yum install -y devtoolset-2-binutils  devtoolset-2-gcc  devtoolset-2-gcc-c++ freetype fontconfig wget perl git
source /opt/rh/devtoolset-2/enable
```

## Qt 5.8.0

Nexus requires qt >=5.5

```shell
mkdir /src
cd src
wget http://download.qt.io/official_releases/qt/5.8/5.8.0/single/qt-everywhere-opensource-src-5.8.0.tar.gz
tar -zxf qt-everywhere-opensource-src-5.8.0.tar.gz
cd qt-everywhere-opensource-src-5.8.0 
./configure -prefix /opt/qt -skip qtgamepad -opensource -confirm-license -skip qtgamepad -nomake tests -nomake examples -no-opengl
gmake
gmake install
rm -rf qt-everywhere-opensource-src-5.8.0.tar.gz qt-everywhere-opensource-src-5.8.0
```

# Build

```shell
wget http://vcg.isti.cnr.it/nexus/download/nexus-4.1.2-src.tgz
tar xf nexus-4.1.2-src.tgz
cd nexus-4.1.2-src/nxsbuild
/opt/qt/bin/qmake nxsbuild.pro
make
cp ../bin/nxsbuild /usr/bin/
```
