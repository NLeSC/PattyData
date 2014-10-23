#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#            and Elena Ranguelova                                              #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, argparse, time, glob, json, logging
import utils 

# {"srid": 32633, "max": [0, 0, 0], "numberpoints": 20000000, "extension": "laz", "min": [0, 0, 0]}

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Creates the JSON for a PC (can be a single LAS/LAZ file or a folder with LAZ/LAZ)")
    parser.add_argument('-i','--input',help='Input LAS/LAZ file or folder with LAS/LAZ files',type=str, required=True)
    parser.add_argument('-o','--output',help='Output JSON file',type=str, required=True)
    
    return parser
    
def apply_argument_parser(options=None):
    """ Apply the argument parser. """
    parser = argument_parser()
    if options is not None:
        args = parser.parse_args(options)
    else:
        args = parser.parse_args()    
    return args

def run(args):    
    if os.path.isfile(args.input):
        inputFile = args.input
        extension = os.path.basename(inputFile).split('.')[-1]
    elif os.path.isdir(args.input):
        numLASs = len(glob.glob(os.path.join(args.input, '*las')))
        numLAZs = len(glob.glob(os.path.join(args.input, '*laz')))
        if numLASs != 0 and numLAZs != 0:
            raise Exception('Folder should only contain LAS or LAZ, not both!')
        elif numLASs != 0:
            inputFile = os.path.join(args.input, '*las')
            extension = 'las'
        elif numLAZs != 0:
            inputFile = os.path.join(args.input, '*laz')
            extension = 'laz'
        else:
            raise Exception('None LAS or LAZ file found in folder')
    (count, minX, minY, minZ, maxX, maxY, maxZ, scaleX, scaleY, scaleZ, offsetX, offsetY, offsetZ) = utils.getLASParams(inputFile)
    data = {"srid": None, "max": [float(maxX), float(maxY), float(maxZ)], "numberpoints": count, "extension": extension, "min": [float(minX), float(minY), float(minZ)]}
    oFile = open(args.output, 'w') 
    oFile.write(json.dumps(data))
    oFile.close()
    
    
     
if __name__ == '__main__':
    run( apply_argument_parser() )
