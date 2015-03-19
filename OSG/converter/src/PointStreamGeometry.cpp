#include "PointStreamGeometry.h"
#include <osgDB/ObjectWrapper>
#include <osg/Version>
using namespace osg_ibr;

struct UpdateShowPercentage : public osg::Drawable::UpdateCallback
{
    UpdateShowPercentage() {}

    UpdateShowPercentage(const UpdateCallback&, const osg::CopyOp&) {}

    virtual void update(osg::NodeVisitor*, osg::Drawable* drw) {
        PointStreamGeometry* geom = dynamic_cast<PointStreamGeometry*>(drw);
        if(geom){
            float showPercentage = geom->getShowPercentage();
            if(showPercentage < 1.0f){
                geom->setShowPercentage(showPercentage+0.01f);
            } else {
                // remove the callback when fully loaded
                geom->setUpdateCallback(NULL);
            }
        }
    }
};
#if 1
PointStreamGeometry::PointStreamGeometry()
: Geometry(),
_lodStart(FLT_MAX),
_lodEnd(-FLT_MAX),
_showPercentage(0.0f)
{
	setUpdateCallback(new UpdateShowPercentage());
}

PointStreamGeometry::PointStreamGeometry(const PointStreamGeometry& copy, const osg::CopyOp& copyop)
: Geometry(copy, copyop),
_lodStart(copy._lodStart),
_lodEnd(copy._lodEnd),
_showPercentage(copy._showPercentage)
{
	setUpdateCallback(new UpdateShowPercentage());
}
void PointStreamGeometry::drawImplementation(osg::RenderInfo& renderInfo) const {
	osg::State& state = *renderInfo.getState();

	// get distance To center
	bool pointStreaming = _lodStart != FLT_MAX && _lodEnd != FLT_MAX;
	float pointStreamingPercentage = 1.0f;
	if (pointStreaming){
        float lodScale = 1.0f;
        if(renderInfo.getView()->getCamera()){
            lodScale = renderInfo.getView()->getCamera()->getLODScale();
        }
		osg::Vec3 center = getBound().center();
		osg::Vec3 position = osg::Vec3(0, 0, 0)*osg::Matrix::inverse(state.getModelViewMatrix());
		float distance = (position - center).length() * lodScale;
		if (distance >= _lodEnd) return;
		if (distance >= _lodStart) {
			pointStreamingPercentage = 1.0f - (distance - _lodStart) / (_lodEnd - _lodStart);
			pointStreamingPercentage = osg::clampBelow(pointStreamingPercentage, _showPercentage);
		}
	}
	if (pointStreamingPercentage >= 1.0f) {
		osg::Geometry::drawImplementation(renderInfo);
	}
	else {
		std::vector<GLsizei> org_size;
		for (unsigned int primitiveSetNum = 0; primitiveSetNum != _primitives.size(); ++primitiveSetNum) {
			osg::PrimitiveSet* primitiveset = _primitives[primitiveSetNum].get();
			osg::DrawArrays* DrawArraysSet = dynamic_cast<osg::DrawArrays*>(primitiveset);
			GLsizei Count = DrawArraysSet->getCount();
			org_size.push_back(Count);
			DrawArraysSet->setCount(pointStreamingPercentage * Count);
		}
		osg::Geometry::drawImplementation(renderInfo);
		for (unsigned int primitiveSetNum = 0; primitiveSetNum != _primitives.size(); ++primitiveSetNum) {
			osg::PrimitiveSet* primitiveset = _primitives[primitiveSetNum].get();
			osg::DrawArrays* DrawArraysSet = dynamic_cast<osg::DrawArrays*>(primitiveset);
			DrawArraysSet->setCount(org_size[primitiveSetNum]);
		}
	}
}
void DrawArraysStream::draw(osg::State& state, bool useVertexBufferObjects, float drawPercentage) const {
	osg::DrawArrays::draw(state, useVertexBufferObjects);
}
void PointStreamGeometry::drawStreamPrimitivesImplementation(osg::RenderInfo& renderInfo) const {
}
#else

void DrawArraysStream::draw(osg::State& state, bool, float drawPercentage) const {
#if defined(OSG_GLES1_AVAILABLE) || defined(OSG_GLES2_AVAILABLE)
    GLenum mode = _mode;
    if(_mode==GL_QUADS)
    {
        state.drawQuads(_first, _count, _numInstances);
        return;
    } else if(mode==GL_POLYGON)
    {
        mode = GL_TRIANGLE_FAN;
    } else if(mode==GL_QUAD_STRIP)
    {
        mode = GL_TRIANGLE_STRIP;
    }

    if(_numInstances>=1) state.glDrawArraysInstanced(mode, _first, _count, _numInstances);
    else glDrawArrays(mode, _first, _count);
#else
    if(_numInstances>=1) state.glDrawArraysInstanced(_mode, _first, _count*osg::clampBetween(drawPercentage,0.0f,1.0f), _numInstances);
    else glDrawArrays(_mode, _first, _count*osg::clampBetween(drawPercentage, 0.0f, 1.0f));
#endif
}

PointStreamGeometry::PointStreamGeometry()
: Geometry(),
_lodStart(FLT_MAX),
_lodEnd(-FLT_MAX),
_showPercentage(0.0f)
{
    setUpdateCallback(new UpdateShowPercentage());
}

PointStreamGeometry::PointStreamGeometry(const PointStreamGeometry& copy, const osg::CopyOp& copyop)
: Geometry(copy, copyop),
_lodStart(copy._lodStart),
_lodEnd(copy._lodEnd),
_showPercentage(copy._showPercentage)
{
    setUpdateCallback(new UpdateShowPercentage());
}

void PointStreamGeometry::drawImplementation(osg::RenderInfo& renderInfo) const {
    if(_containsDeprecatedData)
    {
        OSG_WARN<<"Geometry::drawImplementation() unable to render due to deprecated data, call geometry->fixDeprecatedData();"<<std::endl;
        return;
    }

    osg::State& state = *renderInfo.getState();

    bool checkForGLErrors = state.getCheckForGLErrors()==osg::State::ONCE_PER_ATTRIBUTE;
    if(checkForGLErrors) state.checkGLErrors("start of Geometry::drawImplementation()");

    drawVertexArraysImplementation(renderInfo);

    if(checkForGLErrors) state.checkGLErrors("Geometry::drawImplementation() after vertex arrays setup.");

    ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    //
    // draw the primitives themselves.
    //
    drawStreamPrimitivesImplementation(renderInfo);

    // unbind the VBO's if any are used.
    state.unbindVertexBufferObject();
    state.unbindElementBufferObject();

    if(checkForGLErrors) state.checkGLErrors("end of Geometry::drawImplementation().");
}

void PointStreamGeometry::drawStreamPrimitivesImplementation(osg::RenderInfo& renderInfo) const {
    osg::State& state = *renderInfo.getState();
    osg::ArrayDispatchers& arrayDispatchers = state.getArrayDispatchers();
    bool usingVertexBufferObjects = _useVertexBufferObjects && state.isVertexBufferObjectSupported();

    // get distance To center
    bool pointStreaming = _lodStart != FLT_MAX && _lodEnd != FLT_MAX;
    float pointStreamingPercentage = 1.0f;
    if(pointStreaming){
        float lodScale = renderInfo.getCameraStack().front()->getLODScale();
        if(renderInfo.getView()->getCamera()){
            lodScale = renderInfo.getView()->getCamera()->getLODScale();
        }
        osg::Vec3 center = getBound().center();
        osg::Vec3 position = osg::Vec3(0, 0, 0)*osg::Matrix::inverse(state.getModelViewMatrix());
        float distance = (position-center).length() * lodScale;
        distance = osg::clampBetween(distance, _lodStart, _lodEnd);
        pointStreamingPercentage = 1.0f - (distance - _lodStart) / (_lodEnd - _lodStart);
        pointStreamingPercentage = osg::clampBelow(pointStreamingPercentage, _showPercentage);
    }
    bool bindPerPrimitiveSetActive = arrayDispatchers.active(osg::Array::BIND_PER_PRIMITIVE_SET);
    if(!pointStreaming || pointStreamingPercentage > 0.0f){
        for(unsigned int primitiveSetNum = 0; primitiveSetNum!=_primitives.size(); ++primitiveSetNum)
        {
            // dispatch any attributes that are bound per primitive
            if(bindPerPrimitiveSetActive) arrayDispatchers.dispatch(osg::Array::BIND_PER_PRIMITIVE_SET, primitiveSetNum);

            const osg::PrimitiveSet* primitiveset = _primitives[primitiveSetNum].get();
            const DrawArraysStream* drawArraysStreamSet = dynamic_cast<const DrawArraysStream*>(primitiveset);
            if(pointStreaming && drawArraysStreamSet){
                drawArraysStreamSet->draw(state, usingVertexBufferObjects, pointStreamingPercentage);
            } else {
                primitiveset->draw(state, usingVertexBufferObjects);
            }
        }
    }
}
#endif
namespace DrawArraysStreamWrapper {

    REGISTER_OBJECT_WRAPPER(DrawArraysStream,
                            new osg_ibr::DrawArraysStream,
                            osg_ibr::DrawArraysStream,
                            "osg::Object osg::PrimitiveSet osg::DrawArrays osg_ibr::DrawArraysStream") {
    }
}
namespace PointStreamGeometryWrapper {
    REGISTER_OBJECT_WRAPPER(PointStreamGeometry,
                        new osg_ibr::PointStreamGeometry,
                        osg_ibr::PointStreamGeometry,
                        "osg::Object osg::Drawable osg::Geometry osg_ibr::PointStreamGeometry") {
        ADD_FLOAT_SERIALIZER(LodStart, FLT_MAX);
        ADD_FLOAT_SERIALIZER(LodEnd, -FLT_MAX);
    }
}
