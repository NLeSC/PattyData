#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <osg/Array>
#include <osg/BoundingBox>

namespace osgRC {

    class PointQuadTree {
    public:
        typedef osg::Vec3Array VertexArray;
        typedef osg::Vec3ubArray ColorArray;

        struct Point {
            osg::Vec3 location;
            osg::Vec3ub color;
        };

        PointQuadTree(uint32_t depth, const char *fileNamePrefix);

        PointQuadTree() = delete;
        PointQuadTree(const PointQuadTree&) = delete;
        PointQuadTree& operator=(const PointQuadTree&) = delete;

        const osg::BoundingBoxd &getBoundingBox() const { return _bbox; }

        bool addFile(const char *filename);
        void buildTree(osg::StateSet *stateset, bool reposition, float colorScale);
        void writeNodes();

    private:
        void pruneNodes();
        void insertPoint(const Point &point, osg::Node *node);
        void adjustLodRanges();

        uint32_t _depth;
        std::vector<osg::ref_ptr<osg::Node>> _lodNodes;
        std::vector<char> _nodeUsed; // to prune unused nodes
        osg::BoundingBoxd _bbox;
        std::vector<std::string> _fileNames;
        uint32_t _totalPoints;
    };
}