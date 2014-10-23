
/* Drop Tables */

DROP TABLE IF EXISTS BACKGROUND;
DROP TABLE IF EXISTS PC_CONVERTED_FILE;
DROP TABLE IF EXISTS SITE_PC;
DROP TABLE IF EXISTS PC_CONVERTED_TABLE;
DROP TABLE IF EXISTS PC;
DROP TABLE IF EXISTS SITE_PICTURE;
DROP TABLE IF EXISTS SITE_OBJECT;
DROP TABLE IF EXISTS BOUNDING;
DROP TABLE IF EXISTS SITE_MESH;
DROP TABLE IF EXISTS SITE;




/* Create Tables */

CREATE TABLE BACKGROUND
(
	background_id int NOT NULL,
	name text NOT NULL,
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


CREATE TABLE SITE_PICTURE
(
	site_picture_id serial NOT NULL,
	site_id int NOT NULL,
	pic_path text NOT NULL,
	last_mod int,
	last_check int,
	thumbnail boolean,
	PRIMARY KEY (site_picture_id)
) WITHOUT OIDS;


CREATE TABLE BOUNDING
(
	bounding_id serial NOT NULL,
	name text NOT NULL UNIQUE,
	PRIMARY KEY (bounding_id)
) WITHOUT OIDS;


CREATE TABLE SITE_MESH
(
	site_mesh_id serial NOT NULL,
	site_id int NOT NULL,
	obj_path text NOT NULL,
	last_mod int,
	last_check int,
	PRIMARY KEY (site_mesh_id)
) WITHOUT OIDS;


CREATE TABLE SITE
(
	site_id int NOT NULL,
	name text,
	geom polygon,
	PRIMARY KEY (site_id)
) WITHOUT OIDS;


CREATE TABLE SITE_PC
(
	site_pc_id serial NOT NULL,
	site_id int NOT NULL,
	name text NOT NULL,
	pc_id int NOT NULL,
	PRIMARY KEY (site_pc_id)
) WITHOUT OIDS;


CREATE TABLE SITE_OBJECT
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


CREATE TABLE PC_CONVERTED_FILE
(
	pc_converted_file_id serial NOT NULL,
	pc_id int NOT NULL,
	data_folder text,
	js_path text,
	last_mod int,
	last_check int,
	PRIMARY KEY (pc_converted_file_id)
) WITHOUT OIDS;


CREATE TABLE PC_CONVERTED_TABLE
(
	pc_converted_table_id serial NOT NULL,
	pc_id int NOT NULL,
	tab_name text,
	js_file bytea,
	PRIMARY KEY (pc_converted_table_id)
) WITHOUT OIDS;



/* Create Foreign Keys */

ALTER TABLE PC_CONVERTED_FILE
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


ALTER TABLE SITE_PC
	ADD FOREIGN KEY (pc_id)
	REFERENCES PC (pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE PC_CONVERTED_TABLE
	ADD FOREIGN KEY (pc_id)
	REFERENCES PC (pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_OBJECT
	ADD FOREIGN KEY (bounding_id)
	REFERENCES BOUNDING (bounding_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_MESH
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_OBJECT
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_PC
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_PICTURE
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;



