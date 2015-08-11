PattyData
=========

[![Join the chat at https://gitter.im/NLeSC/PattyData](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/NLeSC/PattyData?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Other related repositories:

 - [PattyVis](https://github.com/NLeSC/PattyVis): WebGL pointcloud visualization of the Via Appia 3D GIS based on potree.
 - [PattyAnalytics](https://github.com/NLeSC/PattyAnalytics): Reusable point cloud analytics software. Includes segmentation, registration, file format conversion.
 - [structure-from-motion](https://github.com/NLeSC/structure-from-motion): Structure from Motion Pipeline

This repository is related to the data management for the Via Appia 3D GIS and it contains:

- Attributes: Explanation about the Attributes management. 
 
- Database: folder with the Entity-Relationship diagram used for the ViaAppiaDB as well as a SQL creation script. It also contains a picture and HTML documentation. 
 
- Documents: folder with several documents:
  - Software User Manual (SUM) for the whole system

  - SUM of the OSG viewer and some basic rules on how to use it

  - Several information for administration purposes 

  - Data storage structure documents

  - Meetings minutes

  - Reports (PID, user requirements, tools analysis, ...)
 
- Footprints: Explanation about the footprints management

- OSG converter code and XSD/XML for the OSG viewer configuration file (from which a python API can be created)

- python: the Data Management tools, i.e. python scripts for the creation and handling of the ViaAppia DB as well as for the management of the Data storage structure.

- test: simple testing framework

In https://github.com/NLeSC/PattyData/blob/master/Documents/SUM/patty.pdf you can find the Software User Manual of the 4D GIS system with an overview of the systems and special focus on the data management (DB and data structure).

In https://github.com/NLeSC/PattyData/blob/master/Documents/SUM_viewer/viewer_sum.pdf you can find the Software User Manual for the OSG desktop-based viewer/editor. In the bottom of this page you can find information about installing and setting up of the OSG viewer/editor. The code is in the private repository https://github.com/NLeSC/Via-Appia.

The web-based Potree viewer is also available. Please contact the administrator if you wish to have access to the web visualization.


Managing data
-------------
In this section we shortly describe how to manage data, i.e. add new data (point clouds, meshes, pictures) or how to remove it. 


**Add data**

- For the addition of new data (mesh, point cloud or image) the data has to be transfered to the Via Appia Linux server. Use WinSCP for this purpose, the Host Name is the IP address of the Via Appia Linux server are the user and password and your user name and password as provided by the administrator. We suggest to move the data (LAS/LAZ file for point cloud, a folder with OBJ/textures/PLY files for meshes and a PNG/JPG for picures) to your default home directory in the Via Appia Linux server.

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

   In this example we add a point cloud of site 41. IMPORTANT: If a point cloud has been aligned with the background you have to make sure that the spatial reference system has been added (Some alignment tools do not set the SRID). Use `UpdateLASSRID.py -s ? -i /home/oscarr/SITE_41.las` to check current value of the SRID in the LAS file and set it if necessary (you will need to create a temporal new file with option `-o` as in the example). Note that in the example we remove the temporal file after adding it in the Data structure (when adding new data in the Data structure a copy is made so you can remove additional copies even though we always recommend to have at least one copy of the data in some other location)
   
   - An example of adding an aligned mesh (assuming the folder `SITE_932_MESH` contains a OBJ file and a PLY file):
   
    `AddRawDataItem.py -f SITE_932_MESH -k SITE -t MESH -p CURR -s 32633 --site 932`
   
   In this example note that since the mesh is aligned we need to use option `-s 32633`. This is different in point cloud case where if a point cloud is aligned we need to use `UpdateLASSRID.py`. Also note that in meshes we need to specify if the mesh is of current period or an archaeological reconstruction. For meshes ideally we need to add a folder with both OBJ/textures and PLY files. OBJ is required by the OSG viewer and PLY is required by the PattyVis webviewer.

   - An example of adding a picture:
   
    `AddRawDataItem.py -k SITE -t PIC -f SITE_1.png -p CURR --site 1`
   
   Like in the mesh example we need to specify if is a current picture of a historical picture.
 
- Still with `pattydat` user, after adding the data we need to update the DB:
  
  `UpdateDB.py`

- Now we need to generate the OSG data of the recently added data required by the Windows desktop viewer/editor. The meshes that do not have a OBJ file won't be included:
  
  `GenerateOSG.py` 

- We also generate the Potree data for the web-based viewer. Only point clouds of sites are converted to Potree data:
  
  `GeneratePOtree.py`
  
- We also generate the Nexus data for the web-based viewer. Only meshes which have a PLY file and are not aligned are converted to Nexus data:
  
  `GenerateNexus.py`

- We update de DB again with the latest changes:
  
  `UpdateDB.py`
 
- We generate the configuration file for the Potree viewer:
  
  `CreatePattyVisConfig.py -o /home/pattydat/DATA/POTREE/CONF.json`

-  We can start the synchronized viewer to download the latest data and configuration file


**List data**

In order to see the data that is currently available in the Via Appia data structure you have to log in the the Via Appia Linux server with Putty (as explained in the previous section) and use:

  `ListRawDataItem.py`

This will list the raw data items (i.e. not the converted OSG or Potree versions), for each data item the ID and the PATH is shown.


**Remove data**

-  If you want to remove some data you need to log in in the Via Appia Linux server with Putty and change user to `pattydat` as described in th eprevious steps.

- Use `ListRawDataItem.py` to find the ID of the raw data item that you wish to delete

- Delete the raw data item (also the related OSG nd Potree data will be deleted). For example:

 `RemoveRawDataItem.py -i 43` 

 This will delete raw data item with ID 43 and all its related OSG and Potree data
 
 - As every time that there is a change in the data structure, we need to update de DB again with the latest changes:
  
  `UpdateDB.py`

- We generate the configuration file for the Potree viewer:
  
  `CreatePattyVisConfig.py -o /home/pattydat/DATA/POTREE/CONF.json`


OSG Via Appia viewer
-------------------

The OSG viewer requires to have a local copy of all the OSG data in your computer as well as the latest XML configuration file.

You can use the viewer/editor with DB/Data synchronization and without it.
To use the synchronized viewer you need to use the `launcher/binary/ViaAppia.bat`, to use the unsynchronized viewer use `viewer/viewer/startViewer.bat`

Synchronized viewer
 - Set you configuration parameters in a file named `config.properties` in the folder `launcher/binary` (you can use the template `config_template.properties`, for more information see below in Setting up section)  
 - After the `config.properties` is in its place run the `launcher/binary/ViaAppia.bat`
 - This will synchronize the data in your local Windows machine with the OSG data in the server and download the latest viewer XML configuration file (this is a different file to the previous `config.properties`)
 - After the synchronization is done the viewer is opened.
 - When you close the viewer please be sure to Save your changes. Then, the tool will ask you if you want to commit your changes to the DB in the server.

Unsynchronized viewer
 - You can start the unsynchronized viewer with `viewer/viewer/startViewer.bat`
 - Be aware that in this case the latest data won't be available in your system and that any changes you do in this mode won't be committed to the DB
 - Obviously the first time that you use the viewer you should use the synchronized viewer, otherwise there won't be any local data to visualize
 
**Installation**

In addition to download the Via Appia OSG repository in your Windows machine you also need to install:
 - The latest drivers of your Graphics card
 - Microsoft Visual Studio C++ Redistributable 2012 and 2013. You can use the installers in `viewer/EXTRA_LIB`
 - Java SE development kit:
    * Browse to http://www.oracle.com/technetwork/java/javase/downloads/index.html
    * Download the Java SDK.
    * Install it (follow the instructions).
 - Putty (http://winscp.net/download/putty.exe)
 - WinSCP (http://winscp.net/download/winscp570.zip)

**Setting up**

In order for the viewer to work you need to:
  - Have a linux OS account in the Via Appia Linux server (ask the administrator to create it for you)
  - Have a PostgreSQL account in DB running in the Via Appia Linux server (ask the DB administrator to create it for you)
  - Create directory in your Windows system where all the ViaAppia data will be stored. We recommend (and use in the examples in this page) `C:/Users/[user name]/ViaAppia` where user name is the name of your user.
  - Download the Via Appia OSG repository:
     * If you are a member click in Download ZIP in https://github.com/NLeSC/Via-Appia
     * If you do not have access please contact some member of the project to get a copy of the repository
     * We recommend saving the ZIP file in C:/Users/[user name]/ViaAppia
     * Uncompress the ZIP file. This should create a folder in `C:/Users/[user name]/ViaAppia/Via-Appia-master`
     * You can now remove the ZIP file
  - Generate a SSH key in the Via Appia Linux server and download the private key to your Windows system:
    * Log in into the Linux Via Appia Server with Putty. For the IP address of the Via Appia Linux server contact the administrator, use the credentials (user name and password) given to you by the administrator
    * Create a key pair in the linux server (Do not enter a passphrase, i.e. press Enter three times): 
    
      `ssh-keygen -t rsa`
    * Add the public key as authoirzed key in the linux server (replace user name accordingly):
    
      `cat  /home/[user name]/.ssh/id_rsa.pub >> /home/[user name]/.ssh/authorized_keys`
    * Change permissions of ssh directory: 
    
      `chmod 700  /home/[user name]/.ssh/`
    * Change permissions of all files in ssh:
    
      `chmod 600  /home/[user name]/.ssh/*`
    * Copy the private key into your Windows machine with WinSCP:
       - Host name is the IP address of the Via Appia Linux server, use the same credentials as in Putty
       - We need to be able to see hidden folders. Go to Options/Preferences/Panels and tick the check box for Show hidden files
       - Go to .ssh folder in the server and select and drag the id_rsa file to your local Windows machine and store it in your Via Appia directory (`C:/Users/[user name]/ViaAppia`)
    * Fill in a `config.properties` file from the `config_template.properties`:
       - Create a `config.properties` with the same content as the file in `C:/Users/[user name]/ViaAppia/Via-Appia-master/launcher/binary/config_template.properties` and store it in `C:/Users/[user name]/ViaAppia/Via-Appia-master/launcher/binary`
       - Change the tags <UserRemote>, <UserLocal>, <localPrivateKey>
          - `<UserRemote>` is your user name in the Linux server
          - `<UserLocal>` is your Windows user name in the local machine
          - `<localPrivateKey>` is the file name of private key that you copied from the Linux server (as explained in the previous step)
          - `<IPRemote>` is the IP address of the Via Appia server
       - This rest of parameters in this configuration file assume that you are setting your Via Appia system to use in `C:\Users\<UserLocal>\ViaAppia`. If that is not the case you may need to explicitly change some other properties
