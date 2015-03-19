#include "QuadTreeUtils.h"

using namespace osgRC;

uint32_t QuadTreeUtils::x = 123456789;
uint32_t QuadTreeUtils::y = 362436069;
uint32_t QuadTreeUtils::z = 521288629;
uint32_t QuadTreeUtils::w = 88675123;

// returns the number of nodes needing for a quadtree of a certain level    
// this is including the root node
uint32_t QuadTreeUtils::nodesForLevel(uint32_t level) {
    uint32_t result = 1;
    uint32_t children = 4;
    for(uint32_t i = 0; i < level; i++){
        result += children;
        children *= 4;
    }
    return result;
}

// for a given cell gives the z order index
// from http://www-graphics.stanford.edu/~seander/bithacks.html#InterleaveBMN
uint32_t QuadTreeUtils::zOrderIndex(uint16_t x, uint16_t y) {
    x = (x | (x << 8)) & 0x00FF;
    x = (x | (x << 4)) & 0x0F0F;
    x = (x | (x << 2)) & 0x3333;
    x = (x | (x << 1)) & 0x5555;

    y = (y | (y << 8)) & 0x00FF;
    y = (y | (y << 4)) & 0x0F0F;
    y = (y | (y << 2)) & 0x3333;
    y = (y | (y << 1)) & 0x5555;

    return  x | (y << 1);
}
