#pragma once

#include <cstdint>
#include <algorithm>
#include <osg/Geometry>

namespace osgRC {

    class QuadTreeUtils {
    public:
        // returns the number of nodes needing for a quadtree of a certain level    
        // this is including the root node
        static uint32_t nodesForLevel(uint32_t level);

        // returns the number of nodes at a certain level
        // this is excluding the partents
        static uint32_t nodesAtLevel(uint32_t level) {
            return (1 << (level*2));
        }

        // for a given cell gives the z order index
        // from http://www-graphics.stanford.edu/~seander/bithacks.html#InterleaveBMN
        static uint32_t zOrderIndex(uint16_t x, uint16_t y);

        template<typename VertexType, typename ColorType>
        static void randomizePoints(osg::Geometry *streamGeometry) {
            // we need to save the seed for the randomizer so we use the same seed for the vertex and color arrays
            uint32_t x_tmp = x;
            uint32_t y_tmp = y;
            uint32_t z_tmp = z;
            uint32_t w_tmp = w;
            VertexType *vertexArray = dynamic_cast<VertexType*>(streamGeometry->getVertexArray());
            ColorType *colorArray = dynamic_cast<ColorType*>(streamGeometry->getColorArray());
            if(vertexArray){
                std::random_shuffle(vertexArray->asVector().begin(), vertexArray->asVector().end(), randomFunc);
            }
            if(colorArray){
                x = x_tmp;
                y = y_tmp;
                z = z_tmp;
                w = w_tmp;
                std::random_shuffle(colorArray->asVector().begin(), colorArray->asVector().end(), randomFunc);
            }
        }

        static uint32_t randomUniform() {
            return random();
        }

        static double randomExponential(double rate) {
            return -log(1.0 - randomDouble())/rate;
        }

    private:
        static uint32_t x;
        static uint32_t y;
        static uint32_t z;
        static uint32_t w;

        /*
         * Returns double in [0,1) range
         */
        static double randomDouble() {
            return (double)(random()%UINT32_MAX)/(double)UINT32_MAX;
        }

        static uint32_t random() {
            uint32_t t;

            t = x ^ (x << 11);
            x = y; y = z; z = w;
            return w = w ^ (w >> 19) ^ (t ^ (t >> 8));
        }

        static int randomFunc(int i) {
            return random()%i;
        }

    };
}