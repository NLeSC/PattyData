#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez, Elena Ranguelova, Milena Ivanova                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, time, math, subprocess
import scipy
import optparse, utils 

numPointsNode = 10000.

def main(opts):
    t0 = time.time()
    # Check options
    for option in (opts.input, opts.extent, opts.num, opts.output):
        if option == '':
            print 'ERROR - missing options!'
            return
    
    minx,miny,maxx,maxy = opts.extent.split(',')
    l = min([float(maxx)-float(minx),float(maxy)-float(miny)])
    minDist = l /  scipy.cbrt(numPointsNode)
    
    numLevels = math.log((7. * float(opts.num) / numPointsNode) + 1.,8)
    
    command = '/home/elena/temp/PotreeConverter/bin/PotreeConverter --input ' + opts.input + ' --output ' + opts.output + ' -s ' + str(minDist) + ' -l ' + str(numLevels) 
    
    print command
    (out, err)  = subprocess.Popen(command, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    
    
    print 'Finished!. Total time ', time.time() - t0

username = os.popen('whoami').read().replace('\n','')

if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Converts the data in the input folder into the POTree file structure"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--input',default='',help='Input data',type='string')
    op.add_option('-e','--extent',default='',help='The PC extent [default ' + utils.DEFAULT_DB + ']',type='string')
    #op.add_option('-n','--num',default='',help='DB user [default ' + username + ']',type='string')
    #op.add_option('-o','--output',default='',help='DB pass',type='string')
    (opts, args) = op.parse_args()
    main(opts)
