user gives a id from raw data item 
from abspath import from related db entry you get what you deal with
define out path
query aligment info and 8bit from db (if necessary)

def getOSGFileFormat(inType):
#    if inType == 'pic':
#        return 'osgt'
    return 'osgb'

def updateXMLDescription(xmlPath, siteId, inType, activeObjectId, fileName = None):
    tempFile = xmlPath + '_TEMP'
    ofile = open(tempFile,'w')
    lines = open(xmlPath,'r').readlines()
    for line in lines:
        if line.count('<description>'):
            ofile.write('    <description>' + utils.getOSGDescrition(siteId, inType, activeObjectId, os.path.basename(os.path.dirname(fileName))) + '</description>\n')
        else:
            ofile.write(line)
    os.system('rm ' + xmlPath)
    os.system('mv ' + tempFile + ' ' + xmlPath)

def createOSG(inFile, outFolder, inType, abOffsetX = None, abOffsetY = None, abOffsetZ = None, color8Bit = False):
    (mainOsgb, xmlPath, offsets) = (None, None, (0,0,0))
    
    if os.path.exists(outFolder):
        os.system('rm -rf ' + outFolder) 
    os.makedirs(outFolder)
    
    #(abOffsetX, abOffsetY, abOffsetZ) from DB
    # color8 also from DB
    
    os.chdir(os.path.dirname(inFile))
    outputPrefix = 'data'
    aligned = (abOffsetX != None)
    
    ofile = getOSGFileFormat(inType)
    if inType == 'pc': #A PC SITE
        tmode = '--mode lodPoints --reposition'
#        outputPrefix = 'data' + os.path.basename(inFile)
    elif inType == 'mesh':
        tmode = '--mode polyMesh --convert --reposition'
    elif inType == 'bg': # A PC BG
        tmode = '--mode quadtree --reposition'
    elif inType == 'pic':
        tmode = '--mode picturePlane'
    
        
    command = CONVERTER_COMMAND + ' ' + tmode + ' --outputPrefix ' + outputPrefix + ' --files ' + os.path.basename(inFile)
    if color8Bit:
        command += ' --8bitColor '
    if aligned:
        command +=  ' --translate ' + str(abOffsetX) + ' ' + str(abOffsetY) + ' ' + str(abOffsetZ)
    
    logFile = os.path.join(outFolder,outputPrefix + '.log')
    command += ' &> ' + logFile

    logging.info(command)
    #os.system(command)
    subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell = True).communicate()
   
#     if inType == 'mesh':
#         rmcommand = 'rm -rf ' + inFile.replace('.obj', '2.obj')
#         logging.info(rmcommand)
#         os.system(rmcommand)
 
    mvcommand = 'mv ' + outputPrefix + '* ' + outFolder
    logging.info(mvcommand)
    os.system(mvcommand)
    #outputPrefix += os.path.basename(inFile)

    ofiles = sorted(glob.glob(os.path.join(outFolder,'*' + ofile)))
    if len(ofiles) == 0:
        logging.error('none OSG file was generated (found in ' + outFolder + '). Check log: ' + logFile)
        mainOsgb = None
    else:
        mainOsgb = ofiles[0]
        if inType != 'bg':
            xmlfiles = glob.glob(os.path.join(outFolder,'*xml'))
            if len(xmlfiles) == 0:
                logging.error('none XML file was generated (found in ' + outFolder + '). Check log: ' + logFile)
                xmlPath = None
            else:
                xmlPath = xmlfiles[0]
                if len(xmlfiles) > 1:
                    logging.error('multiple XMLs file were generated (found in ' + outFolder + '). Using ' + xmlPath)
        txtfiles =  glob.glob(os.path.join(outFolder,'*offset.txt'))
        if len(txtfiles):
            txtFile = txtfiles[0]
            offsets = open(txtFile,'r').read().split('\n')[0].split(':')[1].split()
            for i in range(len(offsets)):
                offsets[i] = float(offsets[i]) 
        elif aligned:
            logging.warn('No offset file was found and it was expected!')
            
            
    updateXMLDescription()
    
    
