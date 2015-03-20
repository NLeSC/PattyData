PattyData
=========

[![Join the chat at https://gitter.im/NLeSC/PattyData](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/NLeSC/PattyData?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

This repository contains:
 - Attributes: Different versions of Attributes DBs. For each version we need to have the original Microsoft Access DB file but also the converted SQL dump produced from Bullzip's software (See Attributes). 
 - Database: folder with the Entity-Relationship diagram used for the ViaAppiaDB as well as a SQL creation script. It also contains a picture and HTML documentation. 
 - Documents: folder with several documents:
   - Software User Manual (SUM) for the whole system
   - SUM of the OSG viewer and some basic rules on how to use it
   - Several information for administration purposes 
   - Data storage structure documents
   - Meetings minutes
   - Reports (PID, user requirements, tools analysis, ...)
 - Footprints: Different versions of the footprints (current version 06 March 2015)
 - OSG converter code and XSD/XML for the OSG viewer configuration file (from which a python API can be created)
 - python: the Data Management tools, i.e. python scripts for the creation and handling of the ViaAppia DB as well as for the management of the Data storage structure.
 - test: simple testing framework

Managing data
-------------
In this section we shortly describe how to manage data, i.e. add new data (point clouds, meshes, pictures) or how to remove it. 

**Add data**

 - For addition of new data the data has to be transfered to the Via Appia Linux server. Use WinSCP for this purpose, the Host Name is the IP address of the Via Appia Linux server and the user and password and your user name and password as provided by the administrator. We suggest to move the data (LAS/LAZ file for point cloud, a folder with OBJ and textures files for meshes and a PNG/JPG for picures) to your default home directory in the Via Appia Linux server.
 - After the data is in the server you have to log in with Putty. Use same credentials as in WinSCP.
 - Check that the moved data is there:
  
   `ls`
 - The data has to be added to the Via Appia data structure:
   * Change user to `pattydat` since all modifications of data in the Via Appia data structure must be done with `pattydat` user. 
   
    `ssh pattydat@localhost` 
   
    You may need to ask the administration permission for this operation
   * Use the command `AddRawDataItem.py` to add a copy of the data in the Via Appia data structure. You have to specify some options, for example option `-f` is used to point to the data that is to be added (currently in your normal user home directory). Use `AddRawDataItem.py -h` to see all the options of this script. 
     - An example for adding a new point cloud with previous setting of SRID is:
     
      `UpdateLASSRID.py  -i /home/oscarr/SITE_41.las -o /home/pattydat/SITE_41.las -s 32633`
      `AddRawDataItem.py -f /home/pattydat/SITE_41.las -k SITE -t PC --site 41`
      `rm /home/pattydat/SITE_41.las`

     In this example we add a point cloud of site 41. IMPORTANT: If a point cloud has been aligned with the background you have to make sure that the spatial reference system has been added (Some alignement tools do not set the SRID). Use `UpdateLASSRID.py -s ? -i /home/oscarr/SITE_41.las` to check current value of the SRID in the LAS file and set it if necessary (you will need to create a temporal new file with option `-o` as in the example). Note that in the example we remove the temporal file after adding it in the Data structure (when adding new data in the Data structure a copy is made so you can remove additional copies even though we always recommend to have at least one copy of the data in some other location)
     - An example of adding an aligned mesh:
     
     `AddRawDataItem.py -f SITE_932_MESH/SITE_932_O_2_VSFM_TEXTURE_aligned_DRIVE_1_V3.obj -k SITE -t MESH -p CURR -s 32633 --site 932`
     
     In this example note that since the mesh is aligned we need to use option `-s 32633`. This is different in point cloud case where if a point cloud is aligned we need to use `UpdateLASSRID.py`. Also note that in meshes we need to specify if the mesh is of current period or an archeological reconstruction.
     - An example of adding a picture:
     
      `AddRawDataItem.py -k SITE -t PIC -f SITE_1.png -p CURR --site 1`
      
      Like in the mesh example we need to specify if is a current picture of a historical picture.
      
  - Still with `pattydat` user, after adding the data we need to update the DB:
   
   `UpdateDB.py`
   
  - Now we need to generate the OSG data of the recently added data required by the Windows desktop viewer/editor:
   
   `GenerateOSG.py` 

  - We also generate the Potree data for the web-based viewer:
    
   `GeneratePotree.py`

  - We update de DB again with the latest changes:
   
   `UpdateDB.py`
   
  - We generate the configuration file for the Potree viewer:
    
    `CreatePOTreeConfig.py -o /home/pattydat/DATA/POTREE/CONF.json`

  -  We can start the synchronized viewer to doenload the latest data and configuration file
