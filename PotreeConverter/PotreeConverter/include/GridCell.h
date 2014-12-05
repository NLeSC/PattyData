
#ifndef GRID_CELL_H
#define GRID_CELL_H

#include "Point.h"
#include "GridIndex.h"

#include <math.h>
#include <vector>

using std::vector;

#define MAX_FLOAT std::numeric_limits<float>::max()

class SparseGrid;


class GridCell{
public:
	vector<Vector3<double>> points;
	vector<GridCell*> neighbours;
	SparseGrid *grid;

	GridCell();

	GridCell(SparseGrid *grid, GridIndex &index);

	float minGap(const Vector3<double> &p);

	float squaredMinGap(const Vector3<double> &p);

	void add(Vector3<double> p);

	float minGapAtArea(const Vector3<double> &p);
};

#endif