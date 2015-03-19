///////////////////////////////////////////////////////////////////////////////////////////////////
#include <osg/TexGen>
#include <osgDB/Registry>
#include <osgDB/ObjectWrapper>
#include <osg/MatrixTransform>
#include <osgUtil/CullVisitor>
#include <osgViewer/Renderer>


#include <osg/Multisample>

#include "FadingLOD.h"

bool osg_ibr::FadingLOD::removeChildren(unsigned int pos,unsigned int numChildrenToRemove) {
	if ((pos) && (pos + numChildrenToRemove == _children.size())) {
		if (pos+1<_rangeList.size()) _rangeList.erase(_rangeList.begin()+pos+1, osg::minimum(_rangeList.begin()+(pos+1+numChildrenToRemove), _rangeList.end()) );
	    return Group::removeChildren(pos,numChildrenToRemove);
	}
	return osg::LOD::removeChildren(pos, numChildrenToRemove);
}

bool FadingLOD_readLocalData(osg::Object&, osgDB::Input&) { return false; }

bool FadingLOD_writeLocalData(const osg::Object&, osgDB::Output&) { return true; }

REGISTER_DOTOSGWRAPPER(FadingLOD)
(
	new osg_ibr::FadingLOD,
	"FadingLOD",
	"Object Node LOD Group",
	&FadingLOD_readLocalData,
	&FadingLOD_writeLocalData
);
REGISTER_OBJECT_WRAPPER2( osg_ibr_FadingLOD, new osg_ibr::FadingLOD, osg_ibr::FadingLOD, "osg_ibr::FadingLOD", "osg::Object osg::Node osg::Group osg::LOD" ) {}
