#pragma once

#include <osg/Geometry>
#include "osg_ibr.h"

namespace osg_ibr {
    IBRBB_EXPORT class DrawArraysStream : public osg::DrawArrays {
    public:

        DrawArraysStream(GLenum mode = 0):
            DrawArrays(mode) {}

        DrawArraysStream(GLenum mode, GLint first, GLsizei count, int numInstances = 0):
        DrawArrays(mode, first, count, numInstances) {}

        DrawArraysStream(const DrawArrays& da, const osg::CopyOp& copyop = osg::CopyOp::SHALLOW_COPY):
            DrawArrays(da, copyop) {}

        META_Object(osg_ibr, DrawArraysStream);

        virtual void draw(osg::State& state, bool useVertexBufferObjects, float drawPercentage) const;

    protected:
        virtual ~DrawArraysStream() {}
    };

    IBRBB_EXPORT class PointStreamGeometry : public osg::Geometry{
    public:
        PointStreamGeometry();
        PointStreamGeometry(const PointStreamGeometry& copy, const osg::CopyOp& copyop = osg::CopyOp::SHALLOW_COPY);

        META_Object(osg_ibr, PointStreamGeometry);

        void drawImplementation(osg::RenderInfo& renderInfo) const;

        void drawStreamPrimitivesImplementation(osg::RenderInfo& renderInfo) const;

        void setLodStart(float v) { _lodStart = v; }
        float getLodStart() const { return _lodStart; }

        void setLodEnd(float v) { _lodEnd = v; }
        float getLodEnd() const { return _lodEnd; }

        void setShowPercentage(float v) { _showPercentage = v; }
        float getShowPercentage() const { return _showPercentage; }

    private:
        float _lodStart, _lodEnd;
        float _showPercentage;
    };

}