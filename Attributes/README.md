Attributes management
=====================

In thi folder we keep track of different versions of attribute data

Convert Attribute Microsoft Access file to PostgreSQL
-----------------------------------------------------

We use Bullzip Access to PostgreSQL http://www.bullzip.com/products/a2p/info.php.

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
 
Installation
------------
The Bullzip Access to PostgreSQL tool needs to be used in a Windows machine.
