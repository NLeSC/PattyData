Attributes management
=====================

The Attributes data is collected in a single Microsoft Access file. In order to used this data in the 4D GIS system it has to be imported into the ViaAppiaDB PostgreSQL database.

The steps for this are:

1- Convert Attribute Microsoft Access file to PostgreSQL

 We use Bullzip Access to PostgreSQL http://www.bullzip.com/products/a2p/info.php (only available in Windows).

 - Put your Attribute MS file in a new subfolder in Attributes folder. 
 - Execute Bullzip Access to PostgreSQL
    * Select the Attribute Microsoft Access
    * If it complains about a missing driver follow the recommended instructions that appear on screen
    * Select create dump file 
    * Run 
 - Add the produced SQL file to the new subfolder in the Attributes folder.
 - Before being able to use UpdateDBAttribute.py script you need to:
    * Remove the CREATE DATABASE statement in the beginning of the SQL file
    * Remove all the DEFAULT values in TIMESTAMP columns
    * Remove all the double quotes (") of the SQL dump file
 - Upload the SQL file to the repository and synchronize it in the server and you are ready to use UpdateDBAttribute.py
 
2- Transfer the converted SQL (with the proper modifications explained in the previous step) to the Via Appia Linux server with WinSCP

3- With pattydat user store the new Attribute file in /home/pattydat/DATA/ATTR

4- Still with pattydat user run the script to update the Attributes in the ViaAppia DB

  `UpdateDBAttribute.py -i /home/pattydat/DATA/ATTR/2015_03_06/MS.sql`
