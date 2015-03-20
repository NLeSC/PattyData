Footprints management
=====================

When a new footprints Shapefile file is available we need to import it into the DB.

The steps for this are:

1- Transfer the Shapefile to the Via Appia Linux server with WinSCP

2- With pattydat user store the new Shapefile file in /home/pattydat/DATA/FOOT

3- Still with pattydat user run the script to update the footprints in the ViaAppia DB

 `UpdateDBFootprints.py -i /home/pattydat/DATA/FOOT/20150306/VIA_APPIA_SITES_06032015.shp`

4- Compute the min Z and max Z for the sites with the new footprints:

 `UpdateDBItemZ.py -c 16 -l /home/pattydat/DATA/RAW/PC/BACK/DRIVE_1_V5`
