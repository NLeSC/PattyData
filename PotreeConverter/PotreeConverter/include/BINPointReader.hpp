

#ifndef BINPOINTREADER_H
#define BINPOINTREADER_H

#include <string>
#include <iostream>
#include <vector>

#include "Point.h"
#include "PointReader.h"
#include "PointAttributes.hpp"

using std::string;

using std::ifstream;
using std::cout;
using std::endl;
using std::vector;

class BINPointReader : public PointReader{
private:
	AABB aabb;
	string path;
	vector<string> files;
	vector<string>::iterator currentFile;
	ifstream *reader;
	PointAttributes attributes;
	Point point;

public:

	BINPointReader(string path);

	~BINPointReader();

	bool readNextPoint();

	Point getPoint();

	AABB getAABB();

	long numPoints();

	void close();

	Vector3<double> getScale();
};

#endif