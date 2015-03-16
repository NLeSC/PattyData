#!/usr/bin/env python

import liblas
import osgeo.osr as osr
import argparse
import utils
def main():
    parser = argparse.ArgumentParser(description="Add spatial reference system (SRS) metadata to a LAS file using the EPSG number")
    parser.add_argument("-o", "--outfile", type=str, help="The output filename", required=True )
    parser.add_argument("-i", "--infile",  type=str, help="The input filename", required=True )
    parser.add_argument("-s", "--srs",     type=str, help="Spatial reference system, default " + str(utils.SRID) + " (Use -? to only show current SRID of input file without updating it)", default=str(utils.SRID))
    args = parser.parse_args()

    f1 = liblas.file.File( args.infile )
    header = f1.header
    currentSRID = utils.readSRID(header)

    print 'Current SRID: ' + str(currentSRID)

    if not args.srs == '?':
        print 'Setting SRID ' + str(args.srs)

        osrs = osr.SpatialReference()
        osrs.SetFromUserInput( "EPSG:{0}".format( int(args.srs) ) )

        lsrs = liblas.srs.SRS()
        lsrs.set_wkt( osrs.ExportToWkt() )

        header.set_srs( lsrs )

        f2 = liblas.file.File(args.outfile, header=header, mode="w")
        for p in f1:
            f2.write(p)

        f2.close()
    f1.close()


if __name__ == "__main__":
    main()

