#pragma once

#include <cstdint>
#include <osg/StateSet>

namespace osgRC {

    class PointModelLod {
    public:
        static void convertModel(const char *filename, const char *outputPrefix, bool reposition, float colorScale, uint32_t depth, osg::StateSet *stateset, osg::Vec3d bbCenter);
    };

}
