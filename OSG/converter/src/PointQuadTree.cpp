#include "PointQuadTree.h"
#include "QuadTreeUtils.h"
#include <assert.h>
#include <osg/PagedLOD>
#include <osg/Geode>
#include <osgDB/WriteFile>
#include "PointStreamGeometry.h"
#include <liblas/liblas.hpp>

using namespace osgRC;

PointQuadTree::PointQuadTree(uint32_t depth, const char *fileNamePrefix): _depth(depth), _totalPoints(0) {
    assert(depth > 0);

    uint32_t nodesNeededTotal = QuadTreeUtils::nodesForLevel(depth);
    uint32_t pagedLodsNeeded = QuadTreeUtils::nodesForLevel(depth-1);

    assert(nodesNeededTotal > 0);
    assert(pagedLodsNeeded > 0);

    //std::cout << "Preparing " << pagedLodsNeeded << "PagedLODs and " << (nodesNeededTotal-pagedLodsNeeded)  << " Geodes." << std::endl;
    _lodNodes.reserve(nodesNeededTotal);
    // first we make the PagedLODs
    for(uint32_t i = 0; i < pagedLodsNeeded; i++){
        osg::PagedLOD *newPagedLOD = new osg::PagedLOD();
        newPagedLOD->setCenterMode(osg::LOD::USE_BOUNDING_SPHERE_CENTER);
        newPagedLOD->setDataVariance(osg::Object::STATIC);
        _lodNodes.emplace_back(newPagedLOD);
    }
    // the last level are lods with one geode inside them
    // then we make the Geodes
    for(uint32_t i = pagedLodsNeeded; i < nodesNeededTotal; i++){
        osg::Geode *geode = new osg::Geode();
        geode->setDataVariance(osg::Object::STATIC);
        _lodNodes.emplace_back(geode);
    }
    _nodeUsed.resize(nodesNeededTotal, 0);
    _nodeUsed[0] = 1;
    uint32_t currentIndex = 0;
    std::ostringstream fileName;
    std::ostringstream fileNameWithLevel;
    // construct the quadtree
    // also gives the nodes the names of the files they are saved too
    std::ostringstream rootFileName;
    rootFileName << fileNamePrefix << ".osgb";
    _lodNodes.front()->setName(rootFileName.str());
    _lodNodes.front()->setNodeMask(0xffffffdf); // do not render shadows for the points in our viewer
    //_lodNodes.front()->setStateSet(pointStateset);
    for(uint32_t level = 0; level < depth; level++){
        uint32_t nodes = QuadTreeUtils::nodesAtLevel(level);
        fileNameWithLevel.str(std::string());
        fileNameWithLevel << fileNamePrefix << "_L" << level << "_C";
        uint32_t childIndex = currentIndex + nodes; // the children are one level deeper
        for(uint32_t children = 0; children < nodes; children++){
            osg::PagedLOD *currentPagedLOD = static_cast<osg::PagedLOD*>(_lodNodes[currentIndex+children].get());
            float minDistance = 0.0f;
            float maxDistance = 1.0f;
            currentPagedLOD->addChild(new osg::Geode(), minDistance, maxDistance);
            fileName.str(std::string());
            fileName << fileNameWithLevel.str() << childIndex <<".osgb";
            _lodNodes[childIndex]->setName(fileName.str());
            currentPagedLOD->addChild(_lodNodes[childIndex].get(), minDistance, maxDistance, fileName.str());
            childIndex++;
            fileName.str(std::string());
            fileName << fileNameWithLevel.str() << childIndex <<".osgb";
            _lodNodes[childIndex]->setName(fileName.str());
            currentPagedLOD->addChild(_lodNodes[childIndex].get(), minDistance, maxDistance, fileName.str());
            childIndex++;
            fileName.str(std::string());
            fileName << fileNameWithLevel.str() << childIndex <<".osgb";
            _lodNodes[childIndex]->setName(fileName.str());
            currentPagedLOD->addChild(_lodNodes[childIndex].get(), minDistance, maxDistance, fileName.str());
            childIndex++;
            fileName.str(std::string());
            fileName << fileNameWithLevel.str() << childIndex <<".osgb";
            _lodNodes[childIndex]->setName(fileName.str());
            currentPagedLOD->addChild(_lodNodes[childIndex].get(), minDistance, maxDistance, fileName.str());
            childIndex++;
            currentPagedLOD->setNumChildrenThatCannotBeExpired(1);
        }
        currentIndex += nodes;
    }
}

bool PointQuadTree::addFile(const char *filename) {
    std::ifstream ifs;
    ifs.open(filename, std::ios::in | std::ios::binary);

    if(!ifs.is_open()){
        std::cout << "Warning could not open file" << std::endl;
        return false;
    }
    _fileNames.emplace_back(filename);
    liblas::ReaderFactory f;
    liblas::Reader reader = f.CreateWithStream(ifs);
    liblas::Header const& header = reader.GetHeader();
    _totalPoints += header.GetPointRecordsCount();
    // scale the bounds back
    _bbox.expandBy(header.GetMinX(), header.GetMinY(), header.GetMinZ());
    _bbox.expandBy(header.GetMaxX(), header.GetMaxY(), header.GetMaxZ());
    return true;
}

// prune unused nodes
void PointQuadTree::pruneNodes() {
    // walk up the tree marking al the parents that have children with nodes
    // rootnode is already marked
    for(uint32_t level = _depth-1; level > 0; level--){
        uint32_t levelStart = QuadTreeUtils::nodesForLevel(level-1);
        uint32_t levelEnd = QuadTreeUtils::nodesForLevel(level);
        for(uint32_t i = levelStart; i < levelEnd; i++){
            // mark the node used if the children are used
            uint32_t childIndex = levelEnd + 4*(i-levelStart);
            if(_nodeUsed[i] == 1 || _nodeUsed[childIndex] > 0 || _nodeUsed[childIndex+1] > 0 || _nodeUsed[childIndex+2] > 0 || _nodeUsed[childIndex+3] > 0){
                _nodeUsed[i] = 1;
                osg::PagedLOD *pagedLOD = dynamic_cast<osg::PagedLOD*>(_lodNodes[i].get());
                if(_nodeUsed[childIndex+3] == 0){
                    pagedLOD->removeChild(4);
                }
                if(_nodeUsed[childIndex+2] == 0){
                    pagedLOD->removeChild(3);
                }
                if(_nodeUsed[childIndex+1] == 0){
                    pagedLOD->removeChild(2);
                }
                if(_nodeUsed[childIndex+0] == 0){
                    pagedLOD->removeChild(1);
                }
            }
        }
    }
    // for level 0
    uint32_t childIndex = 1;
    osg::PagedLOD *pagedLOD = dynamic_cast<osg::PagedLOD*>(_lodNodes[0].get());
    if(_nodeUsed[childIndex+3] == 0){
        pagedLOD->removeChild(4);
    }
    if(_nodeUsed[childIndex+2] == 0){
        pagedLOD->removeChild(3);
    }
    if(_nodeUsed[childIndex+1] == 0){
        pagedLOD->removeChild(2);
    }
    if(_nodeUsed[childIndex+0] == 0){
        pagedLOD->removeChild(1);
    }
}

void PointQuadTree::insertPoint(const Point &point, osg::Node *node) {
    assert(node);

    // the node can be a Geode or a PagedLOD with a Geode as first child
    osg::Geode *insertGeode = NULL;
    osg::LOD *nodeLOD = dynamic_cast<osg::LOD*>(node);
    if(nodeLOD){
        // insert the point into the 
        if(nodeLOD->getNumChildren() > 0){
            insertGeode = dynamic_cast<osg::Geode*>(nodeLOD->getChild(0));
        }
    }
    if(!insertGeode){
        insertGeode = dynamic_cast<osg::Geode*>(node);
    }
    if(insertGeode){
        osg_ibr::PointStreamGeometry *geometry = NULL;
        if(insertGeode->getNumDrawables() > 0){
            geometry = dynamic_cast<osg_ibr::PointStreamGeometry*>(insertGeode->getDrawable(0));
        }
        VertexArray* vectices = NULL;
        ColorArray* colors = NULL;
        osg::DrawArrays* primitiveSet = NULL;
        if(!geometry){
            geometry = new osg_ibr::PointStreamGeometry();
            vectices = new VertexArray(osg::Array::BIND_PER_VERTEX);
            colors = new ColorArray(osg::Array::BIND_PER_VERTEX);
            primitiveSet = new osg::DrawArrays(osg::PrimitiveSet::POINTS, 0, 0);
            geometry->setVertexArray(vectices);
            geometry->setColorArray(colors);
            geometry->addPrimitiveSet(primitiveSet);
            geometry->setUseDisplayList(false);
            geometry->setUseVertexBufferObjects(true);
            geometry->setUpdateCallback(NULL); // remove the update callback so it does not get saved
            insertGeode->addDrawable(geometry);
        } else {
            vectices = dynamic_cast<VertexArray*>(geometry->getVertexArray());
            colors = dynamic_cast<ColorArray*>(geometry->getColorArray());
            primitiveSet = dynamic_cast<osg::DrawArrays*>(geometry->getPrimitiveSet(0));
            assert(vectices != NULL);
            assert(colors != NULL);
            assert(primitiveSet != NULL);
        }
        vectices->push_back(point.location);
        colors->push_back(point.color);
        primitiveSet->setCount(primitiveSet->getCount()+1);
        return;
    }
    std::cout << "Error, failed to insert point" << std::endl;
}

void PointQuadTree::adjustLodRanges() {
    for(uint32_t level = 0; level <= _depth; level++){
        uint32_t levelStart = level > 0 ? QuadTreeUtils::nodesForLevel(level-1) : 0;
        uint32_t levelEnd = QuadTreeUtils::nodesForLevel(level);
        for(uint32_t i = levelStart; i < levelEnd; i++){
            osg::Node *currentNode = _lodNodes[i].get();
            const osg::BoundingSphere &bs = currentNode->getBound();
            osg::LOD *nodeLOD = dynamic_cast<osg::LOD*>(currentNode);
            if(nodeLOD){
                nodeLOD->setCenterMode(osg::LOD::UNION_OF_BOUNDING_SPHERE_AND_USER_DEFINED);
                nodeLOD->setCenter(bs.center());
                nodeLOD->setRadius(bs.radius());
                nodeLOD->setRange(0, 0, bs.radius()*3.4f);
                for(unsigned int children = 1; children < nodeLOD->getNumChildren(); children++){
                    nodeLOD->setRange(children, 0, bs.radius()*3.4f);
                }
            }
            osg::Geode *insertGeode = nodeLOD ? dynamic_cast<osg::Geode*>(nodeLOD->getChild(0)) : dynamic_cast<osg::Geode*>(currentNode);
            if(insertGeode && insertGeode->getNumDrawables() > 0){
                osg_ibr::PointStreamGeometry *streamGeometry = dynamic_cast<osg_ibr::PointStreamGeometry*>(insertGeode->getDrawable(0));
                if(streamGeometry){
                    QuadTreeUtils::randomizePoints<VertexArray,ColorArray>(streamGeometry);
                    if(nodeLOD){
                        streamGeometry->setLodStart(bs.radius()*1.4f);
                    } else {
                        streamGeometry->setLodStart(bs.radius()*2.4f);
                    }
                    streamGeometry->setLodEnd(bs.radius()*3.4f);
                }
            }
        }
    }
}

void PointQuadTree::buildTree(osg::StateSet *stateset, bool reposition, float colorScale) {
    _lodNodes.front()->setStateSet(stateset);
    for(std::vector<std::string>::iterator fileNamesIt = _fileNames.begin(); fileNamesIt != _fileNames.end(); ++fileNamesIt){
        std::string &filename = *fileNamesIt;
        // read a data file
        std::ifstream ifs;
        ifs.open(filename, std::ios::in | std::ios::binary);

        if(!ifs.is_open()){
            std::cout << "Warning could not open file during build" << std::endl;
            return;
        }

        liblas::ReaderFactory f;
        liblas::Reader reader = f.CreateWithStream(ifs);

        liblas::Header const& header = reader.GetHeader();
        uint32_t i = 0;
        Point point;

        while(reader.ReadNextPoint() || i < header.GetPointRecordsCount())
        {
            liblas::Point const& p = reader.GetPoint();
            osg::Vec3d originalLocation(p.GetX(), p.GetY(), p.GetZ());
            point.location.set(p.GetX(), p.GetY(), p.GetZ());
            point.color.set(p.GetColor().GetRed()*colorScale,
                            p.GetColor().GetGreen()*colorScale,
                            p.GetColor().GetBlue()*colorScale);
            i++;
            // get node index
            int level = std::round((double)_depth-(double)QuadTreeUtils::randomExponential(2.0));
            level = osg::clampBetween(level, 0, (int)_depth);
            int grid = int(powf(2.0f, level)+0.5);
            int xNodeIndex = grid*((originalLocation[0]-_bbox.xMin()) / ((double)(_bbox.xMax()-_bbox.xMin())));
            int yNodeIndex = grid*((originalLocation[1]-_bbox.yMin()) / ((double)(_bbox.yMax()-_bbox.yMin())));
            // translate the point to bb center
            if(reposition){
                point.location = originalLocation - _bbox.center();
            }
            if(xNodeIndex == grid){
                xNodeIndex--;
            }
            if(yNodeIndex == grid){
                yNodeIndex--;
            }
            uint32_t zorgerIndex = QuadTreeUtils::zOrderIndex(xNodeIndex, yNodeIndex);
            if(level == 0){
                insertPoint(point, _lodNodes[0].get());
            } else {
                uint32_t nodeIndex = QuadTreeUtils::nodesForLevel(level-1) + QuadTreeUtils::zOrderIndex(xNodeIndex, yNodeIndex);
                insertPoint(point, _lodNodes[nodeIndex].get());
                _nodeUsed[nodeIndex] = 1;
            }
        }
    }
    adjustLodRanges();
    pruneNodes();
}

void PointQuadTree::writeNodes() {
    osgDB::ReaderWriter::Options* opt = osgDB::Registry::instance()->getOptions();
    if(!opt){
        opt = new osgDB::ReaderWriter::Options();
        osgDB::Registry::instance()->setOptions(opt);
    }
    opt->setOptionString("Compressor=zlib");
    for(uint32_t i = 0; i < _lodNodes.size(); i++){
        if(_nodeUsed[i] > 0){
            osg::Node *nodeToWrite = _lodNodes[i].get();
            osgDB::writeNodeFile(*nodeToWrite, nodeToWrite->getName());
        }
    }
}