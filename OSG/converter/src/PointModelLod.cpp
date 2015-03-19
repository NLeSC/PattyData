#include "PointModelLod.h"
#include <osg/PagedLOD>
#include <osgDB/fstream>
#include <liblas/liblas.hpp>
#include <osgDB/WriteFile>
#include "PointStreamGeometry.h"
#include "PointQuadTree.h"
#include <osg/Geode>
#include "QuadTreeUtils.h"

using namespace osgRC;

struct LodInfo {
    osg::Geode *lodGeode;
    osg_ibr::PointStreamGeometry *lodGeometry;
    osg::DrawArrays *drawArrayStream;
    PointQuadTree::VertexArray *vertexArray;
    PointQuadTree::ColorArray *colorArray;
};

void PointModelLod::convertModel(const char *filename, const char *outputPrefix, bool reposition, float colorScale, uint32_t depth, osg::StateSet *stateset, osg::Vec3d offset) {
    // construct osg graph
    osg::PagedLOD *lod = new osg::PagedLOD();
    lod->setNodeMask(0xffffffdf); // do not render shadows for the points in our viewer
    lod->setStateSet(stateset);
    std::ostringstream rootFileName;
    rootFileName << outputPrefix << ".osgb";
    lod->setName(rootFileName.str());
    std::vector<LodInfo> lodInfo;
    lodInfo.resize(depth);
    for(std::vector<LodInfo>::iterator lodInfoIt = lodInfo.begin(); lodInfoIt != lodInfo.end(); ++lodInfoIt){
        LodInfo& lodInfoRef = *lodInfoIt;
        lodInfoRef.lodGeode = new osg::Geode();
        lodInfoRef.lodGeometry = new osg_ibr::PointStreamGeometry();
        lodInfoRef.lodGeometry->setDataVariance(osg::Object::STATIC);
        lodInfoRef.vertexArray = new PointQuadTree::VertexArray(osg::Array::BIND_PER_VERTEX);
        lodInfoRef.colorArray = new PointQuadTree::ColorArray(osg::Array::BIND_PER_VERTEX);
        lodInfoRef.drawArrayStream = new osg::DrawArrays(osg::PrimitiveSet::POINTS, 0, 0);
        lodInfoRef.lodGeometry->setVertexArray(lodInfoRef.vertexArray);
        lodInfoRef.lodGeometry->setColorArray(lodInfoRef.colorArray);
        lodInfoRef.lodGeometry->addPrimitiveSet(lodInfoRef.drawArrayStream);
        lodInfoRef.lodGeometry->setUseDisplayList(false);
        lodInfoRef.lodGeometry->setUseVertexBufferObjects(true);
        lodInfoRef.lodGeometry->setUpdateCallback(NULL); // remove the update callback so it does not get saved
        lodInfoRef.lodGeode->addDrawable(lodInfoRef.lodGeometry);

        float minDistance = 0.0f;
        float maxDistance = 1.0f;
        rootFileName.str(std::string());
        rootFileName << outputPrefix << "_L"<< lod->getNumChildren() <<".osgb";
        lodInfoRef.lodGeode->setName(rootFileName.str());
        lod->addChild(lodInfoRef.lodGeode, minDistance, maxDistance, rootFileName.str());
    }
    osg::Vec3d bbCenter = offset;
    if(reposition){
        osg::BoundingBoxd newBbox;
        std::ifstream ifs;
        ifs.open(filename, std::ios::in | std::ios::binary);

        if(!ifs.is_open()){
            std::cout << "Warning could not open file" << std::endl;
            return;
        }
        liblas::ReaderFactory f;
        liblas::Reader reader = f.CreateWithStream(ifs);
        liblas::Header const& header = reader.GetHeader();
        // scale the bounds back
        newBbox.expandBy(header.GetMinX(), header.GetMinY(), header.GetMinZ());
        newBbox.expandBy(header.GetMaxX(), header.GetMaxY(), header.GetMaxZ());
        bbCenter = newBbox.center();
    }
    // read a data file
    std::ifstream ifs;
    ifs.open(filename, std::ios::in | std::ios::binary);

    if(!ifs.is_open()){
        std::cout << "Warning could not open file" << std::endl;
        return;
    }

    liblas::ReaderFactory f;
    liblas::Reader reader = f.CreateWithStream(ifs);

    liblas::Header const& header = reader.GetHeader();
    uint32_t i = 0;
    PointQuadTree::Point point;

    while(reader.ReadNextPoint() || i < header.GetPointRecordsCount())
    {
        liblas::Point const& p = reader.GetPoint();
        osg::Vec3d originalLocation(p.GetX(), p.GetY(), p.GetZ());
        point.location.set(p.GetX(), p.GetY(), p.GetZ());
        point.color.set(p.GetColor().GetRed()*colorScale,
                        p.GetColor().GetGreen()*colorScale,
                        p.GetColor().GetBlue()*colorScale);
        i++;
        // calculate the level to place it in
        int level = std::round((double)depth-(double)QuadTreeUtils::randomExponential(2.0));
        level = osg::clampBetween(level, 0, (int)depth-1);
        LodInfo &lodInfoRef = lodInfo[level];
        // translate the point to bb center
        point.location = originalLocation-bbCenter;

        lodInfoRef.vertexArray->push_back(point.location);
        lodInfoRef.colorArray->push_back(point.color);
        lodInfoRef.drawArrayStream->setCount(lodInfoRef.drawArrayStream->getCount()+1);
    }
    for(std::vector<LodInfo>::iterator lodInfoIt = lodInfo.begin(); lodInfoIt != lodInfo.end(); ++lodInfoIt){
        LodInfo& lodInfoRef = *lodInfoIt;
        QuadTreeUtils::randomizePoints<PointQuadTree::VertexArray, PointQuadTree::ColorArray>(lodInfoRef.lodGeometry);
    }
    const osg::BoundingSphere &bs = lod->getBound();
    lod->setCenterMode(osg::LOD::UNION_OF_BOUNDING_SPHERE_AND_USER_DEFINED);
    lod->setCenter(bs.center());
    lod->setRadius(bs.radius());
    float lodStart = 0.0f;
    for(int children = lod->getNumChildren()-1; children >= 0; children--){
        float lodEnd = bs.radius()*(float)(lod->getNumChildren() - children)*2.4f;
        lod->setRange(children, 0, lodEnd);
        lodInfo[children].lodGeometry->setLodStart(lodStart);
        lodInfo[children].lodGeometry->setLodEnd(lodEnd);
        lodStart = lodEnd;
    }
    // prume empty nodes
    for(int children = lodInfo.size()-1; children >= 0; children--){
        if(lodInfo[children].vertexArray->getNumElements() == 0) {
            lod->removeChild(children);
        }
    }
    osgDB::writeNodeFile(*lod, lod->getName());
    // write children
    osgDB::ReaderWriter::Options* opt = osgDB::Registry::instance()->getOptions();
    if(!opt){
        opt = new osgDB::ReaderWriter::Options();
        osgDB::Registry::instance()->setOptions(opt);
    }
    opt->setOptionString("Compressor=zlib");
    for(unsigned int i = 0; i < lod->getNumChildren(); i++){
        osg::Node *node = lod->getChild(i);
        osgDB::writeNodeFile(*node, node->getName());
    }
    if(reposition){
        // also output the offset needed to get back into the low-resolution background
        std::ostringstream offsetFileName;
        offsetFileName << outputPrefix << "_offset.txt";
        std::ofstream file;
        file.precision(15);
        file.open(offsetFileName.str());
        osg::Vec3d newOffset = -offset + bbCenter;
        file << "Vector offset:" << newOffset[0] << " " << newOffset[1] << " " << newOffset[2] << std::endl;
        file.close();
    }
    // also export an .prototype.xml file to go with it
    std::ostringstream prototypeFilename;
    prototypeFilename << outputPrefix << ".prototype.xml";
    std::ofstream file;
    file.open(prototypeFilename.str());
    file << "<prototype>" << std::endl;
    file << "   <description>" << outputPrefix << "</description>" << std::endl;
    file << "   <group>Dummy</group>" << std::endl;
    file << "   <file>" << lod->getName() << "</file>" << std::endl;
    file << "   <useBoxSelection/>" << std::endl;
    file << "   <noCache/>" << std::endl;
    file << "</prototype>" << std::endl;
    file.close();
}