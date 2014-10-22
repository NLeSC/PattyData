
/* Drop Tables */

DROP TABLE IF EXISTS BACKGROUND;
DROP TABLE IF EXISTS PC_CONVERTED;
DROP TABLE IF EXISTS SITES_PC;
DROP TABLE IF EXISTS PC;
DROP TABLE IF EXISTS SITES_PICTURES;
DROP TABLE IF EXISTS SITES_OBJECTS;
DROP TABLE IF EXISTS BOUNDINGS;
DROP TABLE IF EXISTS SITES_MESHES;
DROP TABLE IF EXISTS SITE;




/* Create Tables */

CREATE TABLE BACKGROUND
(
	background_id int NOT NULL,
	name text,
	pc_id int NOT NULL,
	PRIMARY KEY (background_id)
) WITHOUT OIDS;


CREATE TABLE PC
(
	pc_id serial NOT NULL,
	srid int,
	numberPoints int,
	folder text,
	extension varchar(3),
	last_mod int,
	last_check int,
	minx double precision,
	miny double precision,
	minz double precision,
	maxx double precision,
	maxy double precision,
	maxz double precision,
	PRIMARY KEY (pc_id)
) WITHOUT OIDS;


CREATE TABLE PC_CONVERTED
(
	pc_converted_id serial NOT NULL,
	pc_id int NOT NULL,
	data_folder text,
	js_path text,
	PRIMARY KEY (pc_converted_id)
) WITHOUT OIDS;


CREATE TABLE SITES_PICTURES
(
	site_picture_id serial NOT NULL,
	site_id int NOT NULL,
	pic_path text NOT NULL,
	last_mod int,
	last_check int,
	thumbnail boolean,
	PRIMARY KEY (site_picture_id)
) WITHOUT OIDS;


CREATE TABLE BOUNDINGS
(
	bounding_id serial NOT NULL,
	name text NOT NULL UNIQUE,
	PRIMARY KEY (bounding_id)
) WITHOUT OIDS;


CREATE TABLE SITES_MESHES
(
	site_mesh_id serial NOT NULL,
	site_id int NOT NULL,
	obj_path text NOT NULL,
	last_mod int,
	last_check int,
	PRIMARY KEY (site_mesh_id)
) WITHOUT OIDS;


CREATE TABLE SITES_OBJECTS
(
	site_id int NOT NULL,
	object_id int NOT NULL,
	bounding_id int NOT NULL,
	x float DEFAULT 0,
	y float DEFAULT 0,
	z float DEFAULT 0,
	xs float DEFAULT 1,
	ys float DEFAULT 1,
	zs float DEFAULT 1,
	h float DEFAULT 0,
	p float DEFAULT 0,
	r float DEFAULT 0,
	UNIQUE (site_id, object_id)
) WITHOUT OIDS;


CREATE TABLE SITE
(
	site_id int NOT NULL,
	name text,
	geom polygon,
	PRIMARY KEY (site_id)
) WITHOUT OIDS;


CREATE TABLE SITES_PC
(
	sites_pc_id serial NOT NULL,
	site_id int NOT NULL,
	name text,
	pc_id int NOT NULL,
	PRIMARY KEY (sites_pc_id)
) WITHOUT OIDS;



/* Create Foreign Keys */

ALTER TABLE PC_CONVERTED
	ADD FOREIGN KEY (pc_id)
	REFERENCES PC (pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE BACKGROUND
	ADD FOREIGN KEY (pc_id)
	REFERENCES PC (pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITES_PC
	ADD FOREIGN KEY (pc_id)
	REFERENCES PC (pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITES_OBJECTS
	ADD FOREIGN KEY (bounding_id)
	REFERENCES BOUNDINGS (bounding_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITES_PC
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITES_MESHES
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITES_PICTURES
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITES_OBJECTS
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;



