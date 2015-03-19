#include "QuadTreeUtils.h"
#include "PointQuadTree.h"
#include "PointModelLod.h"
#include "FadingLOD.h"
#include "libsquish/squish.h"

#include <osgDB/FileUtils>
#include <osgDB/FileNameUtils>
#include <osgDB/ReadFile>
#include <osgDB/WriteFile>
#include <osg/Texture2D>
#include <osgUtil/Optimizer>
#include <osg/PagedLOD>

#include <osgViewer/GraphicsWindow>
#include <osgViewer/Version>

#include <stdio.h>

using namespace osgRC;
//special stateset with a shader that draws the points
osg::ref_ptr<osg::StateSet> pointStateset;
void makeStateset() {
    // vertex program
    std::ostringstream vp_oss;
    vp_oss <<
        "varying vec2 texCoord;"
        "void main(void)"
        "{"
        "  gl_Position    = ftransform();"
        "  gl_PointSize = 1.0+30.0/(gl_Position.w);"
        "  gl_FrontColor = gl_Color;"
        "}";
    std::ostringstream fp_oss;
    fp_oss <<
        "void main (void)"
        "{"
        "    gl_FragColor = gl_Color;"
        "}";

    osg::ref_ptr<osg::Program> program = new osg::Program;
    osg::ref_ptr<osg::Shader> vp = new osg::Shader(osg::Shader::VERTEX);
    vp->setShaderSource(vp_oss.str());

    osg::ref_ptr<osg::Shader> fp = new osg::Shader(osg::Shader::FRAGMENT);
    fp->setShaderSource(fp_oss.str());
    program->addShader(vp);
    program->addShader(fp);

    // the stateset itself
    pointStateset = new osg::StateSet();
    pointStateset->setDataVariance(osg::Object::STATIC);
    pointStateset->setMode(GL_LIGHTING, osg::StateAttribute::OFF);
    pointStateset->setMode(GL_NORMALIZE, osg::StateAttribute::OFF);
    pointStateset->setMode(GL_VERTEX_PROGRAM_POINT_SIZE, osg::StateAttribute::ON);
    pointStateset->setMode(GL_POINT_SMOOTH, osg::StateAttribute::ON);
    pointStateset->setAttributeAndModes(program.get(), osg::StateAttribute::ON);
}

enum convertMode {
    QUADTREE,
    LODPOINTS,
    POLYMESH,
    PICTURE_PLANE
};

class CompressTexturesVisitor : public osg::NodeVisitor
{
public:

    CompressTexturesVisitor(osg::Texture::InternalFormatMode internalFormatMode):
        osg::NodeVisitor(osg::NodeVisitor::TRAVERSE_ALL_CHILDREN),
        _internalFormatMode(internalFormatMode) {}

    virtual void apply(osg::Node& node) {
        if(node.getStateSet()) apply(*node.getStateSet());
        traverse(node);
    }

    virtual void apply(osg::Geode& node) {
        if(node.getStateSet()) apply(*node.getStateSet());

        for(unsigned int i = 0; i<node.getNumDrawables(); ++i)
        {
            osg::Drawable* drawable = node.getDrawable(i);
            if(drawable && drawable->getStateSet()) apply(*drawable->getStateSet());
        }

        traverse(node);
    }

    virtual void apply(osg::StateSet& stateset) {
        // search for the existence of any texture object attributes
        for(unsigned int i = 0; i<stateset.getTextureAttributeList().size(); ++i)
        {
            osg::Texture* texture = dynamic_cast<osg::Texture*>(stateset.getTextureAttribute(i, osg::StateAttribute::TEXTURE));
            if(texture)
            {
                _textureSet.insert(texture);
            }
        }
    }

    void compress() {
        for(TextureSet::iterator itr = _textureSet.begin();
            itr!=_textureSet.end();
            ++itr)
        {
            osg::Texture* texture = const_cast<osg::Texture*>(itr->get());

            osg::Texture2D* texture2D = dynamic_cast<osg::Texture2D*>(texture);

            osg::ref_ptr<osg::Image> image = texture2D ? texture2D->getImage() : 0;
            if(image.valid() &&
               (image->getPixelFormat()==GL_RGB || image->getPixelFormat()==GL_RGBA) &&
               (image->s()>=32 && image->t()>=32) && image->s()%4 == 0 && image->t()%4 == 0)
            {
                // convert to rgba
                // todo add mipmaps
                unsigned char *data = NULL;
                osg::ref_ptr<osg::Image> image2 = new osg::Image();
                if(image->getPixelFormat()==GL_RGB){
                    data = new unsigned char[image->s()*image->t()*4];
                    image2->setImage(image->s(), image->t(), 1, GL_RGBA, GL_RGBA, GL_UNSIGNED_BYTE, data, osg::Image::USE_NEW_DELETE);
                    unsigned char *dataOld = image->data();
                    for(int i = 0; i < image->s()*image->t(); i++){
                        int indexOld = i*3;
                        int indexNew = i*4;
                        data[indexNew+0] = dataOld[indexOld+0];
                        data[indexNew+1] = dataOld[indexOld+1];
                        data[indexNew+2] = dataOld[indexOld+2];
                        data[indexNew+3] = 255;
                    }
                } else {
                    data = image->data();
                }
                std::cout<<"Compressing image."<<std::endl;
                // compress using libquish
                int memory = squish::GetStorageRequirements(image->s(), image->t(), squish::kDxt1);
                unsigned char *compressedData = new unsigned char[memory];
                squish::CompressImage(data, image->s(), image->t(), compressedData, squish::kDxt1|squish::kColourRangeFit);

                osg::ref_ptr<osg::Image> compressedImage = new osg::Image();
                compressedImage->setImage(image->s(), image->t(), 1, GL_COMPRESSED_RGBA_S3TC_DXT1_EXT, GL_COMPRESSED_RGBA_S3TC_DXT1_EXT, GL_UNSIGNED_BYTE, compressedData, osg::Image::USE_NEW_DELETE);
                texture->setInternalFormatMode(osg::Texture2D::USE_IMAGE_DATA_FORMAT);
                texture->setImage(0,compressedImage);
            } else {
                std::cout<<"Could not compress texture, make sure dimentions are a factor of 4."<<std::endl;
            }
        }
    }

    typedef std::set< osg::ref_ptr<osg::Texture> > TextureSet;
    TextureSet                          _textureSet;
    osg::Texture::InternalFormatMode    _internalFormatMode;

};

// visitor to translate all geodes to the right stop
class TranslateVisitor : public osg::NodeVisitor{
public:

    TranslateVisitor(const osg::Vec3d &translate):
        NodeVisitor(osg::NodeVisitor::TRAVERSE_ALL_CHILDREN),
        _translated(translate) {
    }
    virtual void apply(osg::Geode &geode) {
        for(unsigned int i = 0; i < geode.getNumDrawables(); i++){
            osg::Geometry *geometry = dynamic_cast<osg::Geometry*>(geode.getDrawable(i));
            if(geometry){
                translate(*geometry);
            }
        }
    }

    void translate(osg::Geometry &geometry) {
        osg::Array *array = geometry.getVertexArray();
        if(!array){
            std::cout << "Error: No vertex array found." << std::endl;
            return;
        }
        switch(array->getType()){
            case(osg::Array::Vec3ArrayType) :
            {
                osg::Vec3Array *vec3Array = static_cast<osg::Vec3Array*>(array);
                for(unsigned int i = 0; i < vec3Array->getNumElements(); i++){
                    vec3Array->operator[](i).operator-=(_translated);
                }
                break;
            }
            case(osg::Array::Vec3dArrayType) :
            {
                osg::Vec3dArray *vec3dArray = static_cast<osg::Vec3dArray*>(array);
                for(unsigned int i = 0; i < vec3dArray->getNumElements(); i++){
                    vec3dArray->operator[](i).operator-=(_translated);
                }
                break;
            }
            default:
            {
                std::cout << "Error: compatible." << std::endl;
                break;
            }
        }
    }

private:
    osg::Vec3d _translated;
};

int main(int argc, char **argv){
    osg::ArgumentParser arguments(&argc, argv);
    arguments.getApplicationUsage()->setDescription("Via Appia converter that converts .las files to osgb.");
    arguments.getApplicationUsage()->setCommandLineUsage(arguments.getApplicationName()+"[options] --files filenames ...");
    arguments.getApplicationUsage()->addCommandLineOption("-h or --help", "Display this information");
    arguments.getApplicationUsage()->addCommandLineOption("--mode <mode>", "This sets different modes for the converter:\n"
                                                          "\tquadtree: This will merge all the .las files and export them as a big quad tree.\n"
                                                          "\tlodPoints: This will merge all the .las files and export them as a big quad tree.\n"
                                                          "\tpolyMesh: This will merge all the .las files and export them as a big quad tree.\n"
                                                          "\tpicturePlane: This will merge all the .las files and export them as a big quad tree.\n"
                                                          "The default mode is lodPoints.");
    arguments.getApplicationUsage()->addCommandLineOption("--lod <size>", "This controls the amount of levels of detail. In case of a quadtree this will control the depth of the tree. Default is 8.");
    arguments.getApplicationUsage()->addCommandLineOption("--reposition",   "This will translate the points to have a new origin which is the center of all the points.\n"
                                                                            "This might be needed because too big coordinates will result in precision errors when rendering.\n"
                                                                            "Turning this option on will also output a txt file with the offset coordinates in it.");
    arguments.getApplicationUsage()->addCommandLineOption("--8bitColor", "This options means to interpret the color data in the .las file in the range [0...255] instead of [0...65535].");
    arguments.getApplicationUsage()->addCommandLineOption("--translate <x> <y> <z>",    "Not for quad trees. This will translate the model coordinates. This is usefull when you have data that is prealigned to another model.\n"
                                                                                        "And the other model is converted with the --reposition option. Then you can use the offset of the other model to translate this model."
                                                                                        "When used together with the reposition option this will not translate the model but it will print out the total translation from both options.");
    arguments.getApplicationUsage()->addCommandLineOption("--outputPrefix <string>", "(Default is to output the model name or 'output' when multiple files are given.) The prefix to prepent to each file name that is outputted.");
    if(arguments.read("-h") || arguments.read("--help"))
    {
        arguments.getApplicationUsage()->write(std::cout);
        return 0;
    }
    // read parameters
    convertMode mode = LODPOINTS;
    std::string modeString;
    if(arguments.read("--mode", modeString)){
        if(modeString.compare("quadtree") == 0){
            mode = QUADTREE;
        } else if(modeString.compare("lodPoints") == 0){
            mode = LODPOINTS;
        } else if(modeString.compare("polyMesh") == 0){
            mode = POLYMESH;
        } else if(modeString.compare("picturePlane") == 0){
            mode = PICTURE_PLANE;
        }
    }
    bool reposition = arguments.read("--reposition");
    float colorScale = arguments.read("--8bitColor") ? 1.0f : 1.0f/(256.0f);
    int lodDepth = 8;
    arguments.read("--lod", lodDepth);
    osg::Vec3d offset = osg::Vec3d();
    arguments.read("--translate", offset[0], offset[1], offset[2]);
    std::string outputPrefix;
    arguments.read("--outputPrefix", outputPrefix);

    int fileNamesPos = arguments.find("--files");

    if(fileNamesPos == -1){
        std::cout << "Error: No file names given." << std::endl << std::endl;
        arguments.getApplicationUsage()->write(std::cout);
        return 0;
    }

    osgDB::DirectoryContents fileList;
    for(int pos = fileNamesPos+1; pos<arguments.argc() && !arguments.isOption(pos); ++pos)
    {
        std::string arg(arguments[pos]);
        if(arg.find('*') != std::string::npos) {
            osgDB::DirectoryContents contents = osgDB::expandWildcardsInFilename(arg);
            fileList.insert(fileList.end(), contents.begin(), contents.end());
        } else {
            fileList.push_back(arg);
        }
    }

    if(fileList.empty()){
        std::cout << "Error: No file names given." << std::endl << std::endl;
        arguments.getApplicationUsage()->write(std::cout);
        return 0;
    }

    makeStateset();

    if(mode == QUADTREE){
        // for the low resolution landscape
        if(outputPrefix.empty()){
            outputPrefix = "output";
        }
        PointQuadTree pointQuadTree(lodDepth, outputPrefix.c_str());
        for(uint32_t i = 0; i < fileList.size(); i++){
            pointQuadTree.addFile(fileList[i].c_str());
        }
        pointQuadTree.buildTree(pointStateset.get(), reposition, colorScale);
        pointQuadTree.writeNodes();
        if(reposition){
            osg::Vec3d bbCenter = pointQuadTree.getBoundingBox().center();
            std::ostringstream offsetFileName;
            offsetFileName << outputPrefix << "_offset.txt";
            std::ofstream file;
            file.precision(15);
            file.open(offsetFileName.str());
            file << "Vector offset:" << bbCenter[0] << " " << bbCenter[1] << " " << bbCenter[2] << std::endl;
            file.close();
        }
    } else if(mode == LODPOINTS){
        for(uint32_t i = 0; i < fileList.size(); i++){
            std::string outputPrefix2 = outputPrefix;
            if(outputPrefix2.empty()){
                outputPrefix2 = fileList[i];
            }
            PointModelLod::convertModel(fileList[i].c_str(), outputPrefix.c_str(), reposition, colorScale, lodDepth, pointStateset, offset);
        }
    } else if(mode == POLYMESH){
        osgDB::ReaderWriter::Options* opt = osgDB::Registry::instance()->getOptions();
        if(!opt) opt = new osgDB::ReaderWriter::Options();
        opt->setOptionString("noRotation");
        osgDB::Registry::instance()->setOptions(opt);
        osg::BoundingBoxd bbCenter;
        for(uint32_t i = 0; i < fileList.size(); i++){
            std::string readFile = fileList[i];
            // recenter file before reading
            std::string extension = osgDB::getFileExtension(fileList[i]);
            osg::Node *node = NULL;
            if(reposition && extension.compare("obj") == 0 && offset != osg::Vec3d()){
                FILE *fp = fopen(fileList[i].c_str(), "r");
                std::string fileName = osgDB::getNameLessExtension(fileList[i]);
                std::ostringstream tmpFileName;
                tmpFileName << fileName << "2.obj";
                readFile = tmpFileName.str();
                FILE *fp2 = fopen(tmpFileName.str().c_str(), "w");
                if(fp && fp2){
                    char buffer[100];
                    while(fgets(buffer,100,fp) != NULL){
                        // if we have a vertex translate it else just pass the line along
                        if(buffer[0] == 'v' && buffer[1] == ' '){
                            double x, y, z;
                            sscanf(buffer, "v %lf %lf %lf", &x, &y, &z);
                            bbCenter.expandBy(osg::Vec3d(x, y, z));
                            x -= offset[0];
                            y -= offset[1];
                            z -= offset[2];
                            fprintf(fp2, "v %lf %lf %lf\n", x, y, z);
                        } else {
                            fprintf(fp2, buffer);
                        }
                    }
                }
                if(fp) fclose(fp);
                if(fp2) fclose(fp2);
                node = osgDB::readNodeFile(readFile);
                // remove the temporary file
                remove(readFile.c_str());
            } else {
                node = osgDB::readNodeFile(readFile);
            }
            if(node){
                std::ostringstream rootFileName;
                if(!outputPrefix.empty()){
                    rootFileName << outputPrefix;
                }
                // get bounding box and translate so the model is in the origin
                if(reposition){
                    osg::BoundingSphere bbCenter2 = node->getBound();
                    TranslateVisitor translateVisitor = TranslateVisitor(bbCenter2.center());
                    node->accept(translateVisitor);
                    std::ostringstream offsetFileName;
                    offsetFileName << outputPrefix << "_offset.txt";
                    std::ofstream file;
                    file.precision(15);
                    file.open(offsetFileName.str());
                    osg::Vec3d newOffset = -offset + bbCenter.center();
                    file << "Vector offset:" << newOffset[0] << " " << newOffset[1] << " " << newOffset[2] << std::endl;
                    file.close();
                }
                rootFileName << fileList[i] << ".osgb";
                // optimize node to make one big array (we do not want small triangle strips, too many of them will load very very slow)
                //osgUtil::Optimizer optimizer = osgUtil::Optimizer();
                //optimizer.optimize(node, osgUtil::Optimizer::INDEX_MESH | osgUtil::Optimizer::VERTEX_POSTTRANSFORM |osgUtil::Optimizer::VERTEX_PRETRANSFORM);
                // compress texture
                CompressTexturesVisitor ctv(osg::Texture::USE_S3TC_DXT1_COMPRESSION);
                node->accept(ctv);
                ctv.compress();
                osgDB::writeNodeFile(*node, rootFileName.str());
                // add a lod file
                osg::ref_ptr<osg::PagedLOD> plod = new osg::PagedLOD();
                std::ostringstream rootFileName2;
                if(!outputPrefix.empty()){
                    rootFileName2 << outputPrefix;
                }
                rootFileName2 << fileList[i] << "_lod.osgb";
                plod->addChild(node, 0, node->getBound().radius()*20.4f, rootFileName.str());
                osgDB::writeNodeFile(*plod, rootFileName2.str());
                // also export an .prototype.xml file to go with it
                std::ostringstream prototypeFilename;
                if(!outputPrefix.empty()){
                    prototypeFilename << outputPrefix;
                }
                prototypeFilename << fileList[i] << ".prototype.xml";
                std::ofstream file;
                file.open(prototypeFilename.str());
                file << "<prototype>" << std::endl;
                file << "   <description>" << outputPrefix << "</description>" << std::endl;
                file << "   <group>Dummy</group>" << std::endl;
                file << "   <file>" << rootFileName2.str() << "</file>" << std::endl;
                file << "   <noCache/>" << std::endl;
                file << "</prototype>" << std::endl;
                file.close();


            }
        }
    } else if(mode == PICTURE_PLANE){
        for(uint32_t i = 0; i < fileList.size(); i++){
            osg::Image *image = osgDB::readImageFile(fileList[i]);
            if(image){
                osg::ref_ptr<osg_ibr::FadingLOD> lod = new osg_ibr::FadingLOD();
                osg::Geode *geode = new osg::Geode();
                osg::Geometry *geometry = new osg::Geometry();
                osg::StateSet *stateset = geometry->getOrCreateStateSet();
                osg::Texture2D *texture = new osg::Texture2D(image);
                texture->setResizeNonPowerOfTwoHint(false);
                texture->setUnRefImageDataAfterApply(true);

                osg::Vec3Array *clipPlaneVertices = new osg::Vec3Array(4);
                clipPlaneVertices->operator[](0).set(-1, -1, 0);
                clipPlaneVertices->operator[](1).set(-1, 1, 0);
                clipPlaneVertices->operator[](2).set(1, 1, 0);
                clipPlaneVertices->operator[](3).set(1, -1, 0);
                geometry->setVertexArray(clipPlaneVertices);
                osg::Vec2Array *texCoords = new osg::Vec2Array(4);
                texCoords->operator[](0).set(0, 0);
                texCoords->operator[](1).set(0, 1);
                texCoords->operator[](2).set(1, 1);
                texCoords->operator[](3).set(1, 0);
                geometry->setVertexArray(clipPlaneVertices);
                geometry->setTexCoordArray(0, texCoords);
                osg::DrawElementsUInt* triangles = new osg::DrawElementsUInt(osg::PrimitiveSet::TRIANGLE_STRIP);
                triangles->push_back(0);
                triangles->push_back(3);
                triangles->push_back(1);
                triangles->push_back(2);
                geometry->addPrimitiveSet(triangles);
                
                stateset->setTextureAttributeAndModes(0, texture, osg::StateAttribute::ON);
                stateset->setMode(GL_LIGHTING, osg::StateAttribute::OFF);
                stateset->setMode(GL_CULL_FACE, osg::StateAttribute::OFF);
                geode->addDrawable(geometry);

                // compress texture
                CompressTexturesVisitor ctv(osg::Texture::USE_S3TC_DXT1_COMPRESSION);
                geode->accept(ctv);
                ctv.compress();

                lod->addChild(geode, 0.0f, 8.0f);
                lod->addChild(new osg::Node(), 8.0f,30.0f);

                std::ostringstream rootFileName;
                if(!outputPrefix.empty()){
                    rootFileName << outputPrefix;
                }
                rootFileName << fileList[i] << ".osgb";
                osgDB::writeNodeFile(*lod, rootFileName.str());
                // add a lod file
                osg::ref_ptr<osg::PagedLOD> plod = new osg::PagedLOD();
                std::ostringstream rootFileName2;
                if(!outputPrefix.empty()){
                    rootFileName2 << outputPrefix;
                }
                rootFileName2 << fileList[i] << "_lod.osgb";
                plod->addChild(lod, 0, 15.0f, rootFileName.str());
                osgDB::writeNodeFile(*plod, rootFileName2.str());
                // also export an .prototype.xml file to go with it
                std::ostringstream prototypeFilename;
                if(!outputPrefix.empty()){
                    prototypeFilename << outputPrefix;
                }
                prototypeFilename << fileList[i] << ".prototype.xml";
                std::ofstream file;
                file.open(prototypeFilename.str());
                file << "<prototype>" << std::endl;
                file << "   <description>" << outputPrefix << "</description>" << std::endl;
                file << "   <group>Dummy</group>" << std::endl;
                file << "   <file>" << rootFileName2.str() << "</file>" << std::endl;
                file << "   <noCache/>" << std::endl;
                file << "</prototype>" << std::endl;
                file.close();
            }
        }
    }
}
