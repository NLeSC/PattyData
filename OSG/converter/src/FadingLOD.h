#pragma once

#include "osg_ibr.h"
#include <osg/PagedLOD>
#include <osg/StateSet>


/////////////// adding FadingPagedLOD:
namespace osg_ibr {
    class IBRBB_EXPORT FadingLOD : public osg::LOD
    {
    public:
        FadingLOD() {}
        FadingLOD(const osg::LOD& plod, const osg::CopyOp& copyop = osg::CopyOp::SHALLOW_COPY): osg::LOD(plod, copyop) {}
        FadingLOD(const osg_ibr::FadingLOD& plod, const osg::CopyOp& copyop = osg::CopyOp::SHALLOW_COPY): osg::LOD(plod, copyop) {}
        META_Object(osg_ibr, FadingLOD);
        virtual bool removeChildren(unsigned int pos, unsigned int numChildrenToRemove = 1);
    };
}
